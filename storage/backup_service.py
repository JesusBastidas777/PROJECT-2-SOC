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
    def __init__(self, events_path, alerts_path, uid_index, backup_dir, lock_timeout=5.0):
        self.events_path = Path(events_path)
        self.alerts_path = Path(alerts_path)
        self.uid_index = uid_index
        self.backup_dir = Path(backup_dir)
        self.lock_timeout = lock_timeout

    def _locks(self):
        stack = ExitStack()
        for path in sorted((self.events_path, self.alerts_path), key=lambda item: str(item.resolve())):
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
            (temporary / "events.jsonl").write_bytes(events)
            (temporary / "alerts.jsonl").write_bytes(alerts)
            manifest = {
                "manifest_version": MANIFEST_VERSION,
                "logical_signature": LOGICAL_SIGNATURE,
                "created_at": created_at.isoformat(),
                "files": {
                    "events": self._file_entry("events.jsonl", events),
                    "alerts": self._file_entry("alerts.jsonl", alerts),
                },
            }
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
        safety = self.backup_dir / ("pre-restore-" + now.strftime("%Y%m%dT%H%M%S%fZ"))
        try:
            with self._locks():
                safety_result = self._snapshot_locked(safety, now)
                events_old = self.events_path.read_bytes() if self.events_path.exists() else b""
                alerts_old = self.alerts_path.read_bytes() if self.alerts_path.exists() else b""
                try:
                    self._atomic_file(self.events_path, events_new)
                    self._atomic_file(self.alerts_path, alerts_new)
                except OSError:
                    self._atomic_file(self.events_path, events_old)
                    self._atomic_file(self.alerts_path, alerts_old)
                    raise
                self.uid_index.invalidate()
                self.uid_index.rebuild()
        except OSError as exc:
            raise StorageWriteError("restore failed; original state was recovered") from exc
        return {
            "restored": True, "dry_run": False, "verification": verification,
            "safety_backup_path": safety_result["path"],
        }
