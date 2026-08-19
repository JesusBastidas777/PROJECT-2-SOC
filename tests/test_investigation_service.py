import json
import tempfile
import unittest
from pathlib import Path

from investigation.investigation_service import InvestigationService
from storage.event_reader import EventReader


class InvestigationServiceTests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()
        log_file = Path(self.temp_directory.name) / "events.jsonl"
        events = [
            {
                "host": "HOST-01", "event_id": 4688,
                "process_name": "powershell.exe", "parent_process": "winword.exe",
                "user": "alice", "severity": "high",
                "timestamp": "2026-08-18T10:00:00Z",
            },
            {
                "host": "HOST-01", "event_id": 1,
                "process_name": "whoami.exe", "parent_process": "powershell.exe",
                "user": "alice", "severity": "low",
                "timestamp": "2026-08-18T10:01:00Z",
            },
        ]
        with log_file.open("w") as file:

            for event in events:

                file.write(json.dumps(event) + "\n")

        self.service = InvestigationService(EventReader(log_file))

    def tearDown(self):

        self.temp_directory.cleanup()

    def test_returns_complete_serializable_host_investigation(self):

        result = self.service.investigate_host("HOST-01", timeline_limit=1)

        self.assertEqual(result["host_profile"]["hostname"], "HOST-01")
        self.assertEqual(len(result["timeline"]), 1)
        self.assertEqual(len(result["process_correlations"]), 2)
        self.assertGreaterEqual(len(result["detections"]), 1)
        self.assertEqual(result["query"]["timeline_limit"], 1)
        json.dumps(result)

    def test_unknown_host_returns_valid_empty_structures(self):

        result = self.service.investigate_host("UNKNOWN")

        self.assertEqual(result["host_profile"]["total_events"], 0)
        self.assertEqual(result["host_profile"]["processes"], {})
        self.assertEqual(result["timeline"], [])
        self.assertEqual(result["process_correlations"], [])
        self.assertEqual(result["detections"], [])
        json.dumps(result)


if __name__ == "__main__":

    unittest.main()
