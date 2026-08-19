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

    def test_priority_event_reference_and_lifecycle_are_explicit(self):
        self.detection["event"]["event_uid"] = "evt-42"
        alert = self.service.create_alert(self.detection)
        self.assertEqual(alert.priority, "P2")
        self.assertEqual(alert.event_uid, "evt-42")
        self.assertEqual(alert.created_at, alert.updated_at)
        acknowledged = self.service.transition(alert.alert_id, "acknowledged")
        self.assertEqual(acknowledged.created_at, alert.created_at)
        self.assertIsNotNone(acknowledged.acknowledged_at)
        closed = self.service.transition(alert.alert_id, "closed")
        self.assertIsNotNone(closed.closed_at)
        self.assertEqual(self.service.search(priority="P2")[0].alert_id, alert.alert_id)

    def test_priority_override_validation_and_ordering(self):
        low = dict(self.detection, rule_name="low", severity="low")
        urgent = dict(self.detection, rule_name="urgent", priority="P1")
        self.service.create_alert(low)
        self.service.create_alert(urgent)
        self.assertEqual([item.priority for item in self.service.search()], ["P1", "P4"])
        with self.assertRaises(QueryError):
            self.service.create_alert(dict(self.detection, rule_name="bad", priority="P0"))
        with self.assertRaises(QueryError):
            self.service.search(priority="P0")

    def test_legacy_alert_derives_priority_and_lifecycle(self):
        legacy = {
            "alert_id": "legacy", "timestamp": "2026-01-01T00:00:00Z",
            "status": "open", "hostname": "HOST", "severity": "critical",
            "rule_name": "legacy", "reason": "old", "event": {},
        }
        self.service.store.store(legacy)
        alert = next(item for item in self.service.search() if item.alert_id == "legacy")
        self.assertEqual(alert.priority, "P1")
        self.assertEqual(alert.created_at, legacy["timestamp"])


if __name__ == "__main__":
    unittest.main()
