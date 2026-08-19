











import json
import logging
from pathlib import Path

from storage.errors import StorageReadError

logger = logging.getLogger(__name__)


def _default_log_file():
    return Path(__file__).resolve().parent / "event_logs" / "events.jsonl"


class EventReader:

    def __init__(self, log_file=None):

        self.log_file = Path(log_file) if log_file is not None else _default_log_file()

        self.host_index = {}

        self.process_index = {}

        self.uid_index = {}

        self.index_mtime = None
        self.invalid_line_count = 0
        self._snapshot = []

    def _read_file(self):
        events = []
        self.invalid_line_count = 0
        if not self.log_file.exists():
            return events
        try:
            with self.log_file.open("r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, 1):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        self.invalid_line_count += 1
                        logger.warning("skipping invalid event log line %s", line_number)
                        continue
                    if isinstance(event, dict):
                        events.append(event)
                    else:
                        self.invalid_line_count += 1
                        logger.warning("skipping non-object event log line %s", line_number)
        except OSError as exc:
            raise StorageReadError(f"cannot read event log: {self.log_file}") from exc
        return events

    def _ensure_snapshot(self):
        signature = self.signature()
        if self.index_mtime != signature:
            self._snapshot = self._read_file()
            self.host_index = {}
            self.process_index = {}
            self.uid_index = {}
            for event in self._snapshot:
                hostname = event.get("host")
                process_name = event.get("process_name")
                event_uid = event.get("event_uid")
                if hostname is not None:
                    self.host_index.setdefault(hostname, []).append(event)
                if process_name is not None:
                    self.process_index.setdefault(process_name, []).append(event)
                if event_uid is not None:
                    self.uid_index[event_uid] = event
            self.index_mtime = signature

    def read_events(self):
        self._ensure_snapshot()
        return list(self._snapshot)

    def signature(self):

        if not self.log_file.exists():
            return None
        try:
            stat = self.log_file.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError as exc:
            raise StorageReadError(f"cannot inspect event log: {self.log_file}") from exc

    def build_host_index(self):
        self._ensure_snapshot()
        return self.host_index

    def find_by_host(self, hostname):

        self._ensure_snapshot()
        return list(self.host_index.get(hostname, []))

    def find_by_process(self, process_name):

        self._ensure_snapshot()
        return list(self.process_index.get(process_name, []))

    def find_by_uid(self, event_uid):
        self._ensure_snapshot()
        return self.uid_index.get(event_uid)

    # Kept for internal callers from older releases.
    def _log_signature(self):
        return self.signature()
