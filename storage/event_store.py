


import json
import logging
import os
from pathlib import Path

from storage.errors import StorageWriteError
from storage.file_lock import exclusive_file_lock

logger = logging.getLogger(__name__)


def _default_log_file():
    return Path(__file__).resolve().parent / "event_logs" / "events.jsonl"

class EventStore:

    def __init__(self, log_file=None, lock_timeout=5.0):

        self.events = []

        self.log_file = Path(log_file) if log_file is not None else _default_log_file()
        self.lock_timeout = lock_timeout
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.log_file.touch(exist_ok=True)
        except OSError as exc:
            raise StorageWriteError(f"cannot initialize event log: {self.log_file}") from exc

    def store(self,event):

        try:
            payload = json.dumps(event, ensure_ascii=False)
            with exclusive_file_lock(self.log_file, self.lock_timeout):
                with self.log_file.open("a", encoding="utf-8", newline="\n") as file:
                    file.write(payload + "\n")
                    file.flush()
                    os.fsync(file.fileno())
        except (OSError, TypeError, ValueError) as exc:
            raise StorageWriteError(f"cannot store event in: {self.log_file}") from exc
        self.events.append(event)
        logger.info("event stored", extra={"event_host": event.get("host")})
        return event

    def count(self):

        return len(self.events)

    def show_summary(self):
        logger.info("total events: %s", self.count())
