"""Safe compaction of active alert state with complete history archival."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile

from storage.errors import StorageReadError, StorageWriteError
from storage.file_lock import exclusive_file_lock


class AlertCompactionService:
    def __init__(self, alerts_path, archive_dir=None, lock_timeout=5.0):
        self.alerts_path = Path(alerts_path)
        self.archive_dir = Path(archive_dir) if archive_dir else self.alerts_path.parent / "archive"
        self.lock_timeout = lock_timeout

    def _read(self):
        try:
            return self.alerts_path.read_bytes() if self.alerts_path.exists() else b""
        except OSError as exc:
            raise StorageReadError(f"cannot read alert log: {self.alerts_path}") from exc

    @staticmethod
    def _calculate(raw):
        latest = {}
        valid = 0
        invalid = 0
        for position, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                invalid += 1
                continue
            alert_id = value.get("alert_id") if isinstance(value, dict) else None
            if not alert_id:
                invalid += 1
                continue
            valid += 1
            latest[alert_id] = (position, value)
        current = [value for _, value in sorted(latest.values(), key=lambda item: item[0])]
        compact = b"".join(
            (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8") for value in current
        )
        return {
            "total_records": valid + invalid,
            "valid_records": valid,
            "invalid_records": invalid,
            "current_alerts": len(current),
            "records_removed": valid + invalid - len(current),
            "original_bytes": len(raw),
            "compacted_bytes": len(compact),
            "checksums": {
                "history_sha256": hashlib.sha256(raw).hexdigest(),
                "compacted_sha256": hashlib.sha256(compact).hexdigest(),
            },
        }, compact

    def plan(self):
        report, _ = self._calculate(self._read())
        return {**report, "applied": False, "archive_path": None, "manifest_path": None}

    @staticmethod
    def _atomic_replace(path, data):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                "wb", delete=False, dir=path.parent, prefix=path.name + ".compact."
            ) as output:
                temporary = Path(output.name)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def apply(self, now=None):
        now = now or datetime.now(timezone.utc)
        stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
        archive = self.archive_dir / f"alerts.{stamp}.history.jsonl"
        manifest = self.archive_dir / f"alerts.{stamp}.manifest.json"
        try:
            with exclusive_file_lock(self.alerts_path, self.lock_timeout):
                raw = self._read()
                report, compact = self._calculate(raw)
                if report["records_removed"] == 0:
                    return {**report, "applied": False, "archive_path": None, "manifest_path": None}
                self.archive_dir.mkdir(parents=True, exist_ok=True)
                with archive.open("xb") as output:
                    output.write(raw)
                    output.flush()
                    os.fsync(output.fileno())
                payload = {
                    "manifest_version": "1.0", "operation": "alert_compaction",
                    "created_at": now.isoformat(), "archive_path": archive.name, **report,
                }
                with manifest.open("x", encoding="utf-8", newline="\n") as output:
                    json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
                    output.write("\n")
                    output.flush()
                    os.fsync(output.fileno())
                self._atomic_replace(self.alerts_path, compact)
                return {
                    **report, "applied": True, "archive_path": str(archive),
                    "manifest_path": str(manifest),
                }
        except OSError as exc:
            raise StorageWriteError(f"cannot compact alert log: {self.alerts_path}") from exc
