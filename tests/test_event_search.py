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
                "event_uid": "evt-a",
                "user": "alice", "event_id": 4688, "source": "edr",
                "severity": "high", "timestamp": "2026-08-18T10:00:00+00:00",
            },
            {
                "host": "HOST-01", "process_name": "cmd.exe",
                "event_uid": "evt-b",
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

    def test_naive_query_timestamp_is_consistently_treated_as_utc(self):
        matches = self.search.search(
            start_timestamp="2026-08-18T11:00:00",
            end_timestamp="2026-08-18T11:00:00Z",
        )
        self.assertEqual([event.get("process_name") for event in matches], ["cmd.exe"])

    def test_uid_lookup_uses_the_index(self):
        self.assertEqual(self.search.search(event_uid="evt-b")[0]["process_name"], "cmd.exe")
        self.assertEqual(self.search.search(event_uid="missing"), [])

    def test_order_is_deterministic_for_new_and_legacy_events(self):
        newest = self.search.search(hostname="HOST-01")
        oldest = self.search.search(hostname="HOST-01", sort_order="oldest")
        self.assertEqual([item.get("event_uid") for item in newest], ["evt-b", "evt-a", None])
        self.assertEqual([item.get("event_uid") for item in oldest], [None, "evt-a", "evt-b"])

    def test_rejects_unknown_sort_order(self):
        with self.assertRaises(ValueError):
            self.search.search(sort_order="sideways")


if __name__ == "__main__":

    unittest.main()
