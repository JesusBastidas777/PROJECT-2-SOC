











import json
from pathlib import Path


class EventReader:

    def __init__(self):

        self.log_file = Path("storage/event_logs/events.jsonl")

        self.host_index = {}

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

        return self.host_index

    def find_by_host(self, hostname):

        if not self.host_index:

            self.build_host_index()

        return self.host_index.get(hostname, [])



























