import json
import tempfile
import unittest
from pathlib import Path

from investigation.host_timeline import HostTimeline
from storage.event_reader import EventReader


class HostTimelineTests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()
        log_file = Path(self.temp_directory.name) / "events.jsonl"
        events = [
            {"host": "HOST-01", "process_name": "third.exe", "timestamp": "2026-08-18T12:00:00Z"},
            {"host": "HOST-02", "process_name": "other.exe", "timestamp": "2026-08-18T09:00:00Z"},
            {"host": "HOST-01", "process_name": "first.exe", "timestamp": "2026-08-18T10:00:00Z"},
            {"host": "HOST-01", "process_name": "second.exe", "timestamp": "2026-08-18T11:00:00Z"},
        ]
        with log_file.open("w") as file:

            for event in events:

                file.write(json.dumps(event) + "\n")

        self.timeline = HostTimeline(EventReader(log_file))

    def tearDown(self):

        self.temp_directory.cleanup()

    def test_orders_host_events_chronologically(self):

        events = self.timeline.build("HOST-01")

        self.assertEqual(
            [event["process_name"] for event in events],
            ["first.exe", "second.exe", "third.exe"],
        )

    def test_can_return_most_recent_events_first(self):

        events = self.timeline.build("HOST-01", newest_first=True, limit=2)

        self.assertEqual(
            [event["process_name"] for event in events],
            ["third.exe", "second.exe"],
        )

    def test_unknown_host_returns_empty_timeline(self):

        self.assertEqual(self.timeline.build("UNKNOWN"), [])


if __name__ == "__main__":

    unittest.main()
