











import json
from pathlib import Path


class EventReader:

    def __init__(self, log_file=None):

        self.log_file = Path(log_file or "storage/event_logs/events.jsonl")

        self.host_index = {}

        self.process_index = {}

        self.index_mtime = None

    def read_events(self):

        events = []

        with self.log_file.open("r") as file:

            for line in file:

                events.append(json.loads(line))

        return events

    def _log_signature(self):

        stat = self.log_file.stat()

        return stat.st_mtime_ns, stat.st_size

    def build_host_index(self):

        self.host_index = {}

        self.process_index = {}

        with self.log_file.open("r") as file:

            for line in file:

                event = json.loads(line)

                hostname = event["host"]

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
