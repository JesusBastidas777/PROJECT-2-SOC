


import json
import logging
import os
from pathlib import Path

from storage.errors import StorageWriteError
from storage.file_lock import exclusive_file_lock
from storage.uid_index import UIDIndex

logger = logging.getLogger(__name__)


def _default_log_file():
    return Path(__file__).resolve().parent / "event_logs" / "events.jsonl"

class EventStore:

    def __init__(self, log_file=None, lock_timeout=5.0):

        self.events = []

        self.log_file = Path(log_file) if log_file is not None else _default_log_file()
        self.lock_timeout = lock_timeout
        self.uid_index = UIDIndex(self.log_file)
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.log_file.touch(exist_ok=True)
        except OSError as exc:
            raise StorageWriteError(f"cannot initialize event log: {self.log_file}") from exc

    def _append_unlocked(self, payload):
        with self.log_file.open("a", encoding="utf-8", newline="\n") as file:
            file.seek(0, os.SEEK_END)
            offset = file.buffer.tell()
            file.write(payload + "\n")
            file.flush()
            os.fsync(file.fileno())
            return offset

    def store(self,event):
        try:
            payload = json.dumps(event, ensure_ascii=False)
            with exclusive_file_lock(self.log_file, self.lock_timeout):
                self._append_unlocked(payload)
        except (OSError, TypeError, ValueError) as exc:
            raise StorageWriteError(f"cannot store event in: {self.log_file}") from exc
        self.events.append(event)
        logger.info("event stored", extra={"event_host": event.get("host")})
        return event

    def store_once(self, event):
        """Atomically append an identified event unless its UID already exists."""
        event_uid = event.get("event_uid")
        if not event_uid:
            self.store(event)
            return event, True
        try:
            payload = json.dumps(event, ensure_ascii=False)
            with exclusive_file_lock(self.log_file, self.lock_timeout):
                index = self.uid_index.ensure_current()
                existing = index.get_event(event_uid)
                if existing is not None:
                    return existing, False
                # A bad offset can only cause a conservative rebuild, never an append.
                if event_uid in index.offsets:
                    index.rebuild()
                    existing = index.get_event(event_uid)
                    if existing is not None:
                        return existing, False
                offset = self._append_unlocked(payload)
                index.record(event_uid, offset)
        except (OSError, TypeError, ValueError) as exc:
            raise StorageWriteError(f"cannot store event in: {self.log_file}") from exc
        self.events.append(event)
        logger.info("event stored", extra={"event_host": event.get("host")})
        return event, True

    def count(self):

        return len(self.events)

    def show_summary(self):
        logger.info("total events: %s", self.count())
