


import json

from pathlib import Path


class EventStore:

    def __init__(self, log_file=None):

        self.events = []

        self.log_file = Path(log_file or "storage/event_logs/events.jsonl")

        self.log_file.touch(exist_ok=True)

    def store(self,event):

        self.events.append(event)

        with self.log_file.open("a") as file:

            json.dump(event, file)

            file.write("\n")

        print("Event stored:")

        print(event)

    def count(self):

        return len(self.events)

    def show_summary(self):

        print(f"Total events: {self.count()}")


