











import json
from pathlib import Path

from storage.errors import StorageReadError


class EventReader:

    def __init__(self, log_file=None):

        self.log_file = Path(log_file or "storage/event_logs/events.jsonl")

        self.host_index = {}

        self.process_index = {}

        self.index_mtime = None
        self.invalid_line_count = 0

    def read_events(self):

        events = []
        self.invalid_line_count = 0
        if not self.log_file.exists():
            return events
        try:
            with self.log_file.open("r", encoding="utf-8") as file:
                for line in file:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        self.invalid_line_count += 1
                        continue
                    if isinstance(event, dict):
                        events.append(event)
                    else:
                        self.invalid_line_count += 1
        except OSError as exc:
            raise StorageReadError(f"cannot read event log: {self.log_file}") from exc
        return events

    def _log_signature(self):

        if not self.log_file.exists():
            return None
        try:
            stat = self.log_file.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError as exc:
            raise StorageReadError(f"cannot inspect event log: {self.log_file}") from exc

    def build_host_index(self):

        self.host_index = {}

        self.process_index = {}

        for event in self.read_events():
                hostname = event.get("host")
                if hostname is None:
                    continue

                process_name = event.get("process_name")

                if hostname not in self.host_index:

                    self.host_index[hostname] = []

                self.host_index[hostname].append(event)

                if process_name is not None:

                    if process_name not in self.process_index:

                        self.process_index[process_name] = []

                    self.process_index[process_name].append(event)

        self.index_mtime = self._log_signature()

        return self.host_index

    def find_by_host(self, hostname):

        current_mtime = self._log_signature()

        if not self.host_index or current_mtime != self.index_mtime:

            self.build_host_index()

        return self.host_index.get(hostname, [])

    def find_by_process(self, process_name):

        current_mtime = self._log_signature()

        if not self.host_index or current_mtime != self.index_mtime:

            self.build_host_index()

        return self.process_index.get(process_name, [])
