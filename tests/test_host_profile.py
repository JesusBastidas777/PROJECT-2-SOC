import json
import tempfile
import unittest
from pathlib import Path

from investigation.host_profile import HostProfile
from storage.event_reader import EventReader


class HostProfileTests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()
        self.log_file = Path(self.temp_directory.name) / "events.jsonl"
        self.events = [
            {
                "host": "HOST-01", "process_name": "cmd.exe", "user": "bob",
                "event_id": 1, "timestamp": "2026-08-18T12:00:00Z",
            },
            {
                "host": "HOST-01", "process_name": "powershell.exe", "user": "alice",
                "event_id": 4688, "timestamp": "2026-08-18T10:00:00Z",
            },
            {
                "host": "HOST-01", "process_name": "powershell.exe", "user": "alice",
                "event_id": 1, "timestamp": "2026-08-18T11:00:00Z",
            },
        ]
        self.write_events(self.events)
        self.profile_builder = HostProfile(EventReader(self.log_file))

    def tearDown(self):

        self.temp_directory.cleanup()

    def write_events(self, events):

        with self.log_file.open("w") as file:

            for event in events:

                file.write(json.dumps(event) + "\n")

    def test_builds_enriched_profile_without_losing_existing_fields(self):

        profile = self.profile_builder.build("HOST-01")

        self.assertEqual(profile["total_events"], 3)
        self.assertEqual(profile["unique_processes"], 2)
        self.assertEqual(profile["most_frequent_process"], "powershell.exe")
        self.assertEqual(profile["most_frequent_count"], 2)
        self.assertEqual(profile["first_seen"], "2026-08-18T10:00:00Z")
        self.assertEqual(profile["last_seen"], "2026-08-18T12:00:00Z")
        self.assertEqual(profile["users"], ["bob", "alice"])
        self.assertEqual(profile["unique_users"], 2)
        self.assertEqual(profile["event_ids"], [1, 4688])
        self.assertEqual(
            profile["recent_processes"],
            ["cmd.exe", "powershell.exe", "powershell.exe"],
        )

    def test_profile_cache_invalidates_after_fast_append(self):

        first_profile = self.profile_builder.build("HOST-01")
        with self.log_file.open("a") as file:

            file.write(json.dumps({
                "host": "HOST-01", "process_name": "whoami.exe", "user": "alice",
                "event_id": 1, "timestamp": "2026-08-18T13:00:00Z",
            }) + "\n")

        refreshed_profile = self.profile_builder.build("HOST-01")

        self.assertEqual(first_profile["total_events"], 3)
        self.assertEqual(refreshed_profile["total_events"], 4)
        self.assertEqual(refreshed_profile["last_seen"], "2026-08-18T13:00:00Z")

    def test_old_events_without_enrichment_fields_still_work(self):

        self.write_events([{"host": "LEGACY", "process_name": "old.exe"}])
        profile = self.profile_builder.build("LEGACY")

        self.assertEqual(profile["first_seen"], None)
        self.assertEqual(profile["users"], [])
        self.assertEqual(profile["event_ids"], [])

    def test_event_without_process_name_does_not_break_profile(self):
        self.write_events([{"host": "LEGACY", "event_id": 3}])
        profile = self.profile_builder.build("LEGACY")
        self.assertEqual(profile["total_events"], 1)
        self.assertEqual(profile["processes"], {})


if __name__ == "__main__":

    unittest.main()
