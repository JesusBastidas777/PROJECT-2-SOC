











import json
from pathlib import Path


class EventReader:

    def __init__(self):

        self.log_file = Path("storage/event_logs/events.jsonl")

        self.host_index = {}

        self.index_mtime = None

    def read_events(self):

        events = []

        with self.log_file.open("r") as file:

            for line in file:

                events.append(json.loads(line))

        return events

    def build_host_index(self):

        self.host_index = {}

        with self.log_file.open("r") as file:

            for line in file:

                event = json.loads(line)

                hostname = event["host"]

                if hostname not in self.host_index:

                    self.host_index[hostname] = []

                self.host_index[hostname].append(event)

        self.index_mtime = self.log_file.stat().st_mtime

        return self.host_index

    def find_by_host(self, hostname):

        current_mtime = self.log_file.stat().st_mtime

        if not self.host_index or current_mtime != self.index_mtime:

            self.build_host_index()

        return self.host_index.get(hostname, [])
