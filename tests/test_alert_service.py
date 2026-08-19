import json
import tempfile
import unittest
from pathlib import Path

from alerting import AlertService
from soc.errors import AlertTransitionError, QueryError


class AlertServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "alerts" / "alerts.jsonl"
        self.service = AlertService(self.path)
        self.detection = {
            "rule_name": "suspicious", "severity": "high", "reason": "test",
            "event": {"host": "HOST-01", "event_id": 1, "timestamp": "2026-08-18T00:00:00Z"},
        }

    def tearDown(self):
        self.directory.cleanup()

    def test_alert_has_stable_id_and_deduplicates(self):
        first = self.service.create_alert(self.detection)
        second = self.service.create_alert(self.detection)
        self.assertEqual(first.alert_id, second.alert_id)
        self.assertEqual(first.status, "open")
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 1)
        json.dumps(first.__dict__)

    def test_valid_transitions_are_persisted_and_latest_state_is_queried(self):
        alert = self.service.create_alert(self.detection)
        self.service.transition(alert.alert_id, "acknowledged")
        closed = self.service.transition(alert.alert_id, "closed")
        self.assertEqual(closed.status, "closed")
        self.assertEqual(self.service.search(status="closed")[0].alert_id, alert.alert_id)
        self.assertEqual(self.service.search(status="open"), [])

    def test_invalid_transition_and_filter_are_explicit(self):
        alert = self.service.create_alert(self.detection)
        self.service.transition(alert.alert_id, "closed")
        with self.assertRaises(AlertTransitionError):
            self.service.transition(alert.alert_id, "open")
        with self.assertRaises(QueryError):
            self.service.search(status="invalid")

    def test_queries_filter_host_severity_and_state(self):
        self.service.create_alert(self.detection)
        self.assertEqual(len(self.service.search(
            hostname="HOST-01", severity="high", status="open"
        )), 1)
        self.assertEqual(self.service.search(hostname="OTHER"), [])


if __name__ == "__main__":
    unittest.main()
