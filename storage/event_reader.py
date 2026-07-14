



import json
from pathlib import Path


class EventReader:

    def __init__(self):

        self.log_file = Path("storage/event_logs/events.jsonl")

    def read_events(self):

        events = []

        with self.log_file.open("r") as file:

            for line in file:

                events.append(json.loads(line))

        return events

    def find_by_host(self, hostname):

        events = self.read_events()

        results = []

        for event in events :

            if event["host"]  == hostname:

                results.append(event)

        return results









