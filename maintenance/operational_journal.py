"""Append-only, corruption-tolerant operational maintenance journal."""

import json
import os
from pathlib import Path

from storage.errors import StorageReadError, StorageWriteError
from storage.file_lock import exclusive_file_lock


class OperationalJournal:
    def __init__(self, path, lock_timeout=5.0):
        self.path = Path(path)
        self.lock_timeout = lock_timeout

    def append(self, entry):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with exclusive_file_lock(self.path, self.lock_timeout):
                with self.path.open("a", encoding="utf-8", newline="\n") as output:
                    output.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
                    output.flush()
                    os.fsync(output.fileno())
        except OSError as exc:
            raise StorageWriteError(f"cannot write operational journal: {self.path}") from exc

    def read(self, limit=None):
        entries = []
        if not self.path.exists():
            return entries
        try:
            with self.path.open("r", encoding="utf-8") as source:
                for line in source:
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if isinstance(value, dict):
                        entries.append(value)
        except OSError as exc:
            raise StorageReadError(f"cannot read operational journal: {self.path}") from exc
        return entries[-limit:] if limit is not None else entries

    def latest_completed(self):
        return next((item for item in reversed(self.read()) if item.get("finished_at")), None)
