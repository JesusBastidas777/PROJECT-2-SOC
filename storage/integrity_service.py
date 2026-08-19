"""Audit and explicit repair for append-only JSONL storage."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile

from storage.errors import StorageReadError, StorageWriteError
from storage.file_lock import exclusive_file_lock


class IntegrityService:
    def __init__(self, log_file, lock_timeout=5.0):
        self.log_file = Path(log_file)
        self.lock_timeout = lock_timeout

    def audit(self):
        valid = 0
        issues = []
        if not self.log_file.exists():
            return {"path": str(self.log_file), "valid": 0, "invalid": 0, "issues": []}
        try:
            with self.log_file.open("r", encoding="utf-8") as file:
                for number, line in enumerate(file, 1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                        if not isinstance(value, dict):
                            raise ValueError("record is not a JSON object")
                        valid += 1
                    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                        issues.append({"line_number": number, "error": str(exc), "raw": line.rstrip("\n")})
        except OSError as exc:
            raise StorageReadError(f"cannot audit event log: {self.log_file}") from exc
        return {"path": str(self.log_file), "valid": valid, "invalid": len(issues), "issues": issues}

    def repair(self, quarantine_path=None):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = self.log_file.with_name(self.log_file.name + f".{stamp}.backup")
        quarantine = Path(quarantine_path) if quarantine_path else self.log_file.with_name(
            self.log_file.name + f".{stamp}.quarantine.jsonl"
        )
        temporary = None
        try:
            with exclusive_file_lock(self.log_file, self.lock_timeout):
                report = self.audit()
                if not report["issues"]:
                    return {**report, "repaired": False, "backup_path": None, "quarantine_path": None}
                quarantine.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.log_file, backup)
                with quarantine.open("x", encoding="utf-8", newline="\n") as output:
                    for issue in report["issues"]:
                        output.write(json.dumps(issue, ensure_ascii=False) + "\n")
                with tempfile.NamedTemporaryFile(
                    "w", encoding="utf-8", newline="\n", delete=False,
                    dir=self.log_file.parent, prefix=self.log_file.name + ".repair."
                ) as output:
                    temporary = Path(output.name)
                    with self.log_file.open("r", encoding="utf-8") as source:
                        for line in source:
                            try:
                                value = json.loads(line)
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                continue
                            if isinstance(value, dict):
                                output.write(json.dumps(value, ensure_ascii=False) + "\n")
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, self.log_file)
                temporary = None
                return {
                    **report, "repaired": True, "backup_path": str(backup),
                    "quarantine_path": str(quarantine),
                }
        except OSError as exc:
            raise StorageWriteError(f"cannot repair event log: {self.log_file}") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
