import tempfile
import unittest

from soc import SOCConfig, SOCService


class IncidentTimelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))
        stored = self.service.ingest_event({
            "event_uid": "evt-timeline", "host": "HOST", "event_type": "process_creation",
            "source": "edr", "severity": "high", "process_name": "psexec.exe",
            "timestamp": "2026-08-19T09:00:00Z",
        })
        self.assertTrue(stored.metadata["stored"])
        self.alert = self.service.create_alerts("HOST").data["alerts"][0]
        self.incident = self.service.create_incident(
            alert_ids=[self.alert.alert_id]
        ).data["incident"]

    def tearDown(self):
        self.directory.cleanup()

    def test_timeline_combines_evidence_and_state_history(self):
        self.service.transition_alert(self.alert.alert_id, "acknowledged")
        self.service.transition_incident(self.incident.incident_id, "investigating")
        timeline = self.service.get_incident_timeline(self.incident.incident_id).data["timeline"]
        kinds = [item["kind"] for item in timeline["entries"]]
        for kind in ("event", "alert_created", "alert_transition", "incident_created", "incident_transition"):
            self.assertIn(kind, kinds)
        self.assertTrue(all(item["incident_id"] == self.incident.incident_id for item in timeline["entries"]))

    def test_order_and_limit_are_stable(self):
        oldest = self.service.get_incident_timeline(
            self.incident.incident_id, sort_order="oldest", limit=2
        ).data["timeline"]
        newest = self.service.get_incident_timeline(
            self.incident.incident_id, sort_order="newest", limit=2
        ).data["timeline"]
        self.assertEqual(len(oldest["entries"]), 2)
        self.assertTrue(oldest["truncated"])
        self.assertNotEqual(oldest["entries"], newest["entries"])

    def test_missing_event_is_marked_without_failure(self):
        missing = self.service._components.alerts.create_alert({
            "rule_name": "missing", "severity": "low", "reason": "test",
            "event": {"event_uid": "absent", "host": "OTHER"},
        })
        incident = self.service.create_incident(alert_ids=[missing.alert_id]).data["incident"]
        entries = self.service.get_incident_timeline(incident.incident_id).data["timeline"]["entries"]
        self.assertIn("missing_evidence", [item["kind"] for item in entries])


if __name__ == "__main__":
    unittest.main()
