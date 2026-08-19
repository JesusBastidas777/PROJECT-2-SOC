"""Verified, consistent backups and rollback-safe restore for SOC JSONL state."""

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from storage.errors import StorageReadError, StorageWriteError
from storage.file_lock import exclusive_file_lock


MANIFEST_VERSION = "1.0"
LOGICAL_SIGNATURE = "soc-jsonl-v1"


class BackupService:
    def __init__(self, events_path, alerts_path, uid_index, backup_dir, lock_timeout=5.0,
                 incidents_path=None):
        self.events_path = Path(events_path)
        self.alerts_path = Path(alerts_path)
        self.uid_index = uid_index
        self.backup_dir = Path(backup_dir)
        self.lock_timeout = lock_timeout
        self.incidents_path = Path(incidents_path) if incidents_path is not None else None

    def _locks(self):
        stack = ExitStack()
        paths = [self.events_path, self.alerts_path]
        if self.incidents_path is not None:
            paths.append(self.incidents_path)
        for path in sorted(paths, key=lambda item: str(item.resolve())):
            stack.enter_context(exclusive_file_lock(path, self.lock_timeout))
        return stack

    @staticmethod
    def _file_entry(name, data):
        return {
            "path": name,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def _snapshot_locked(self, destination, created_at):
        destination = Path(destination)
        if destination.exists():
            raise StorageWriteError(f"backup destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=destination.name + ".", dir=destination.parent))
        try:
            events = self.events_path.read_bytes() if self.events_path.exists() else b""
            alerts = self.alerts_path.read_bytes() if self.alerts_path.exists() else b""
            incidents = (
                self.incidents_path.read_bytes()
                if self.incidents_path is not None and self.incidents_path.exists() else b""
            )
            (temporary / "events.jsonl").write_bytes(events)
            (temporary / "alerts.jsonl").write_bytes(alerts)
            if self.incidents_path is not None:
                (temporary / "incidents.jsonl").write_bytes(incidents)
            manifest = {
                "manifest_version": MANIFEST_VERSION,
                "logical_signature": LOGICAL_SIGNATURE,
                "created_at": created_at.isoformat(),
                "files": {
                    "events": self._file_entry("events.jsonl", events),
                    "alerts": self._file_entry("alerts.jsonl", alerts),
                },
            }
            if self.incidents_path is not None:
                manifest["files"]["incidents"] = self._file_entry(
                    "incidents.jsonl", incidents
                )
            with (temporary / "manifest.json").open("x", encoding="utf-8", newline="\n") as output:
                json.dump(manifest, output, ensure_ascii=False, indent=2, sort_keys=True)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, destination)
            temporary = None
            return {"path": str(destination), "manifest": manifest, "created": True}
        except OSError as exc:
            raise StorageWriteError(f"cannot create backup: {destination}") from exc
        finally:
            if temporary is not None:
                shutil.rmtree(temporary, ignore_errors=True)

    def create(self, destination, now=None):
        now = now or datetime.now(timezone.utc)
        with self._locks():
            return self._snapshot_locked(destination, now)

    @staticmethod
    def verify(source):
        source = Path(source)
        issues = []
        manifest = None
        try:
            manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {"path": str(source), "valid": False, "issues": [f"invalid manifest: {exc}"]}
        if manifest.get("manifest_version") != MANIFEST_VERSION:
            issues.append("unsupported manifest version")
        if manifest.get("logical_signature") != LOGICAL_SIGNATURE:
            issues.append("unsupported logical signature")
        files = manifest.get("files")
        if not isinstance(files, dict):
            issues.append("manifest files are missing")
            files = {}
        for key, expected_name in (("events", "events.jsonl"), ("alerts", "alerts.jsonl")):
            entry = files.get(key)
            if not isinstance(entry, dict) or entry.get("path") != expected_name:
                issues.append(f"invalid {key} entry")
                continue
            try:
                data = (source / expected_name).read_bytes()
            except OSError:
                issues.append(f"missing {expected_name}")
                continue
            if len(data) != entry.get("size"):
                issues.append(f"size mismatch for {expected_name}")
            if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
                issues.append(f"checksum mismatch for {expected_name}")
        if "incidents" in files:
            entry = files["incidents"]
            if not isinstance(entry, dict) or entry.get("path") != "incidents.jsonl":
                issues.append("invalid incidents entry")
            else:
                try:
                    data = (source / "incidents.jsonl").read_bytes()
                    if len(data) != entry.get("size"):
                        issues.append("size mismatch for incidents.jsonl")
                    if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
                        issues.append("checksum mismatch for incidents.jsonl")
                except OSError:
                    issues.append("missing incidents.jsonl")
        return {"path": str(source), "valid": not issues, "issues": issues, "manifest": manifest}

    @staticmethod
    def _atomic_file(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, prefix=path.name + ".restore.") as output:
                temporary = Path(output.name)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def restore(self, source, *, dry_run=False, now=None):
        source = Path(source)
        verification = self.verify(source)
        if not verification["valid"]:
            raise StorageReadError("backup verification failed", details={"issues": verification["issues"]})
        if dry_run:
            return {"restored": False, "dry_run": True, "verification": verification,
                    "safety_backup_path": None}
        now = now or datetime.now(timezone.utc)
        events_new = (source / "events.jsonl").read_bytes()
        alerts_new = (source / "alerts.jsonl").read_bytes()
        has_incidents = "incidents" in verification["manifest"]["files"]
        incidents_new = (
            (source / "incidents.jsonl").read_bytes() if has_incidents else None
        )
        safety = self.backup_dir / ("pre-restore-" + now.strftime("%Y%m%dT%H%M%S%fZ"))
        try:
            with self._locks():
                safety_result = self._snapshot_locked(safety, now)
                events_old = self.events_path.read_bytes() if self.events_path.exists() else b""
                alerts_old = self.alerts_path.read_bytes() if self.alerts_path.exists() else b""
                incidents_old = (
                    self.incidents_path.read_bytes()
                    if self.incidents_path is not None and self.incidents_path.exists() else b""
                )
                try:
                    self._atomic_file(self.events_path, events_new)
                    self._atomic_file(self.alerts_path, alerts_new)
                    if self.incidents_path is not None and incidents_new is not None:
                        self._atomic_file(self.incidents_path, incidents_new)
                except OSError:
                    self._atomic_file(self.events_path, events_old)
                    self._atomic_file(self.alerts_path, alerts_old)
                    if self.incidents_path is not None:
                        self._atomic_file(self.incidents_path, incidents_old)
                    raise
                self.uid_index.invalidate()
                self.uid_index.rebuild()
        except OSError as exc:
            raise StorageWriteError("restore failed; original state was recovered") from exc
        return {
            "restored": True, "dry_run": False, "verification": verification,
            "safety_backup_path": safety_result["path"],
        }
