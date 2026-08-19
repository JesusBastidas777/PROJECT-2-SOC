import json
import tempfile
import unittest
from pathlib import Path

from investigation.event_search import EventSearch
from storage.event_reader import EventReader


class EventSearchTests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()
        log_file = Path(self.temp_directory.name) / "events.jsonl"
        events = [
            {
                "host": "HOST-01", "process_name": "powershell.exe",
                "user": "alice", "event_id": 4688, "source": "edr",
                "severity": "high", "timestamp": "2026-08-18T10:00:00+00:00",
            },
            {
                "host": "HOST-01", "process_name": "cmd.exe",
                "user": "bob", "event_id": 1, "source": "sysmon",
                "severity": "low", "timestamp": "2026-08-18T11:00:00+00:00",
            },
            {
                "host": "HOST-02", "process_name": "powershell.exe",
                "user": "alice", "event_id": 1, "source": "sysmon",
                "severity": "medium", "timestamp": "2026-08-18T12:00:00+00:00",
            },
            {"host": "HOST-01", "process_name": "legacy.exe"},
        ]
        with log_file.open("w") as file:

            for event in events:

                file.write(json.dumps(event) + "\n")

        self.search = EventSearch(EventReader(log_file))

    def tearDown(self):

        self.temp_directory.cleanup()

    def test_combines_all_provided_filters(self):

        matches = self.search.search(
            hostname="HOST-01",
            process_name="powershell.exe",
            user="alice",
            event_id=4688,
            source="edr",
            severity="high",
        )

        self.assertEqual(len(matches), 1)

    def test_filters_by_inclusive_time_range(self):

        matches = self.search.search(
            hostname="HOST-01",
            start_timestamp="2026-08-18T10:30:00+00:00",
            end_timestamp="2026-08-18T11:00:00+00:00",
        )

        self.assertEqual([event["process_name"] for event in matches], ["cmd.exe"])

    def test_applies_limit(self):

        self.assertEqual(len(self.search.search(hostname="HOST-01", limit=1)), 1)

    def test_returns_empty_list_without_matches(self):

        self.assertEqual(self.search.search(hostname="UNKNOWN"), [])


if __name__ == "__main__":

    unittest.main()
