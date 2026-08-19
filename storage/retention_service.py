"""Explicit, archival-first retention for the active event JSONL."""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from normalization.time_utils import parse_timestamp
from soc.errors import QueryError
from storage.errors import StorageReadError, StorageWriteError
from storage.file_lock import exclusive_file_lock


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


class RetentionService:
    def __init__(self, log_file, uid_index, archive_dir=None, lock_timeout=5.0):
        self.log_file = Path(log_file)
        self.uid_index = uid_index
        self.archive_dir = Path(archive_dir) if archive_dir else self.log_file.parent / "archive"
        self.lock_timeout = lock_timeout

    @staticmethod
    def _validate(max_age_days, max_bytes):
        if max_age_days is None and max_bytes is None:
            raise QueryError("retention requires max_age_days or max_bytes")
        if max_age_days is not None and (
            not isinstance(max_age_days, (int, float)) or max_age_days <= 0
        ):
            raise QueryError("max_age_days must be positive")
        if max_bytes is not None and (not isinstance(max_bytes, int) or max_bytes <= 0):
            raise QueryError("max_bytes must be a positive integer")

    def _read(self):
        try:
            return self.log_file.read_bytes().splitlines(keepends=True) if self.log_file.exists() else []
        except OSError as exc:
            raise StorageReadError(f"cannot read event log: {self.log_file}") from exc

    def _calculate(self, lines, max_age_days, max_bytes, now):
        self._validate(max_age_days, max_bytes)
        records = []
        for position, raw in enumerate(lines):
            parsed = None
            try:
                value = json.loads(raw.decode("utf-8"))
                if isinstance(value, dict):
                    parsed = parse_timestamp(value.get("timestamp"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            records.append({"position": position, "raw": raw, "time": parsed, "reason": None})

        cutoff = now - timedelta(days=max_age_days) if max_age_days is not None else None
        for record in records:
            if cutoff is not None and record["time"] is not None and record["time"] < cutoff:
                record["reason"] = "age"

        if max_bytes is not None:
            current_size = sum(len(item["raw"]) for item in records if item["reason"] is None)
            candidates = sorted(
                (item for item in records if item["reason"] is None and item["time"] is not None),
                key=lambda item: (item["time"], item["position"]),
            )
            for record in candidates:
                if current_size <= max_bytes:
                    break
                record["reason"] = "size"
                current_size -= len(record["raw"])

        removed = [item for item in records if item["reason"]]
        retained = [item for item in records if not item["reason"]]
        removed_times = [item["time"] for item in removed if item["time"] is not None]
        retained_bytes = b"".join(item["raw"] for item in retained)
        archive_bytes = b"".join(item["raw"] for item in removed)
        report = {
            "path": str(self.log_file),
            "policy": {"max_age_days": max_age_days, "max_bytes": max_bytes},
            "evaluated_at": now.isoformat(),
            "cutoff": cutoff.isoformat() if cutoff else None,
            "total_records": len(records),
            "retained_records": len(retained),
            "removed_records": len(removed),
            "removed_by_reason": {
                reason: sum(item["reason"] == reason for item in removed)
                for reason in ("age", "size")
            },
            "original_bytes": sum(len(item["raw"]) for item in records),
            "retained_bytes": len(retained_bytes),
            "target_met": max_bytes is None or len(retained_bytes) <= max_bytes,
            "removed_window": {
                "first_timestamp": min(removed_times).isoformat() if removed_times else None,
                "last_timestamp": max(removed_times).isoformat() if removed_times else None,
            },
            "checksums": {
                "original_sha256": _sha256(b"".join(lines)),
                "archive_sha256": _sha256(archive_bytes),
                "retained_sha256": _sha256(retained_bytes),
            },
        }
        return report, archive_bytes, retained_bytes

    def plan(self, *, max_age_days=None, max_bytes=None, now=None):
        now = now or datetime.now(timezone.utc)
        report, _, _ = self._calculate(self._read(), max_age_days, max_bytes, now)
        return {**report, "applied": False, "archive_path": None, "manifest_path": None}

    @staticmethod
    def _write_atomic(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, prefix=path.name + ".") as output:
                temporary = Path(output.name)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def apply(self, *, max_age_days=None, max_bytes=None, now=None):
        now = now or datetime.now(timezone.utc)
        stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
        archive = self.archive_dir / f"events.{stamp}.archive.jsonl"
        manifest = self.archive_dir / f"events.{stamp}.manifest.json"
        try:
            with exclusive_file_lock(self.log_file, self.lock_timeout):
                report, archive_bytes, retained_bytes = self._calculate(
                    self._read(), max_age_days, max_bytes, now
                )
                if not report["removed_records"]:
                    return {**report, "applied": False, "archive_path": None, "manifest_path": None}
                self.archive_dir.mkdir(parents=True, exist_ok=True)
                with archive.open("xb") as output:
                    output.write(archive_bytes)
                    output.flush()
                    os.fsync(output.fileno())
                manifest_payload = {
                    "manifest_version": "1.0", "operation": "event_retention",
                    **report, "archive_path": archive.name,
                }
                with manifest.open("x", encoding="utf-8", newline="\n") as output:
                    json.dump(manifest_payload, output, ensure_ascii=False, indent=2, sort_keys=True)
                    output.write("\n")
                    output.flush()
                    os.fsync(output.fileno())
                self._write_atomic(self.log_file, retained_bytes)
                self.uid_index.invalidate()
                self.uid_index.rebuild()
                return {
                    **report, "applied": True, "archive_path": str(archive),
                    "manifest_path": str(manifest),
                }
        except OSError as exc:
            raise StorageWriteError(f"cannot apply retention to: {self.log_file}") from exc
