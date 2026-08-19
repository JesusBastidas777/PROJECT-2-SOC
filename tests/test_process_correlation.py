import json
import tempfile
import unittest
from pathlib import Path

from investigation.process_correlation import ProcessCorrelation
from storage.event_reader import EventReader


class ProcessCorrelationTests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()
        log_file = Path(self.temp_directory.name) / "events.jsonl"
        events = [
            {
                "host": "HOST-01", "parent_process": "winword.exe",
                "process_name": "powershell.exe", "timestamp": "2026-08-18T12:00:00Z",
            },
            {
                "host": "HOST-01", "parent_process": "explorer.exe",
                "process_name": "cmd.exe", "timestamp": "2026-08-18T11:00:00Z",
            },
            {
                "host": "HOST-01", "parent_process": "winword.exe",
                "process_name": "powershell.exe", "timestamp": "2026-08-18T10:00:00Z",
            },
            {"host": "HOST-01", "process_name": "legacy.exe"},
            {
                "host": "HOST-02", "parent_process": "winword.exe",
                "process_name": "powershell.exe", "timestamp": "2026-08-18T09:00:00Z",
            },
        ]
        with log_file.open("w") as file:

            for event in events:

                file.write(json.dumps(event) + "\n")

        self.correlation = ProcessCorrelation(EventReader(log_file))

    def tearDown(self):

        self.temp_directory.cleanup()

    def test_groups_repeated_parent_child_relationships(self):

        results = self.correlation.correlate("HOST-01")
        powershell = next(
            item for item in results if item["process_name"] == "powershell.exe"
        )

        self.assertEqual(powershell["count"], 2)
        self.assertEqual(powershell["first_seen"], "2026-08-18T10:00:00Z")
        self.assertEqual(powershell["last_seen"], "2026-08-18T12:00:00Z")

    def test_keeps_hosts_separate(self):

        results = self.correlation.correlate()

        self.assertEqual(len(results), 3)

    def test_ignores_old_events_without_parent_process(self):

        results = self.correlation.correlate("HOST-01")

        self.assertNotIn("legacy.exe", [item["process_name"] for item in results])

    def test_results_are_json_serializable(self):

        json.dumps(self.correlation.correlate())


if __name__ == "__main__":

    unittest.main()
