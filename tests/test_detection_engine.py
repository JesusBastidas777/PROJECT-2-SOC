import json
import tempfile
import unittest
from pathlib import Path

from detection.detection_engine import DetectionEngine
from storage.event_reader import EventReader


class DetectionEngineTests(unittest.TestCase):

    def test_benign_event_does_not_trigger_detection(self):

        event = {
            "host": "HOST-01",
            "parent_process": "explorer.exe",
            "process_name": "notepad.exe",
            "severity": "low",
        }

        self.assertEqual(DetectionEngine().analyze_events([event]), [])

    def test_sensitive_process_triggers_explainable_detection(self):

        event = {"host": "HOST-01", "process_name": "Mimikatz.exe"}

        detections = DetectionEngine().analyze_events([event])

        self.assertEqual(detections[0]["rule_name"], "sensitive_process_execution")
        self.assertEqual(detections[0]["severity"], "high")
        self.assertIn("mimikatz.exe", detections[0]["reason"])
        self.assertIs(detections[0]["event"], event)

    def test_office_parent_starting_shell_triggers_detection(self):

        event = {
            "host": "HOST-01",
            "parent_process": "WINWORD.EXE",
            "process_name": "PowerShell.exe",
        }

        detections = DetectionEngine().analyze_events([event])

        self.assertEqual(
            detections[0]["rule_name"], "office_spawned_command_interpreter"
        )

    def test_high_source_severity_triggers_detection(self):

        detections = DetectionEngine().analyze_events([{
            "host": "HOST-01", "process_name": "app.exe", "severity": "HIGH"
        }])

        self.assertEqual(detections[0]["rule_name"], "source_reported_high_severity")

    def test_enrichment_is_stable_local_and_does_not_mutate_event(self):
        event = {
            "event_uid": "evt-1", "host": "HOST-01", "process_name": "psexec.exe",
            "parent_process": "services.exe", "user": "analyst", "source": "edr",
        }
        original = dict(event)
        first = DetectionEngine().analyze_events([event])[0]
        second = DetectionEngine().analyze_events([event])[0]
        self.assertEqual(first["detection_id"], second["detection_id"])
        self.assertEqual(first["category"], "credential_or_admin_tool")
        self.assertEqual(first["confidence"], "high")
        self.assertEqual(first["event_uid"], "evt-1")
        self.assertEqual(first["evidence"]["parent_process"], "services.exe")
        self.assertEqual(first["context"]["hostname"], "HOST-01")
        self.assertEqual(event, original)

    def test_can_analyze_events_for_one_host(self):

        with tempfile.TemporaryDirectory() as directory:

            log_file = Path(directory) / "events.jsonl"
            events = [
                {"host": "HOST-01", "process_name": "psexec.exe"},
                {"host": "HOST-02", "process_name": "mimikatz.exe"},
            ]
            with log_file.open("w") as file:

                for event in events:

                    file.write(json.dumps(event) + "\n")

            detections = DetectionEngine(EventReader(log_file)).analyze_host("HOST-01")

        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0]["event"]["host"], "HOST-01")


if __name__ == "__main__":

    unittest.main()
