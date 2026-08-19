import tempfile
import unittest

from soc import SOCConfig, SOCService
from soc.errors import IncidentTransitionError, QueryError


class IncidentServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))
        self.alert = self.service._components.alerts.create_alert({
            "rule_name": "suspicious", "severity": "high", "reason": "test",
            "event": {
                "event_uid": "evt-incident", "host": "HOST",
                "timestamp": "2026-08-19T10:00:00Z",
            },
        })

    def tearDown(self):
        self.directory.cleanup()

    def test_create_is_durable_idempotent_and_does_not_change_alert(self):
        first = self.service.create_incident(alert_ids=[self.alert.alert_id]).data["incident"]
        second = self.service.create_incident(alert_ids=[self.alert.alert_id]).data["incident"]
        self.assertEqual(first.incident_id, second.incident_id)
        self.assertEqual(self.service.get_incident(first.incident_id).data["incident"], first)
        self.assertEqual(self.service.search_alerts().data["alerts"][0].status, "open")
        self.assertEqual(len(self.service.list_incidents().data["incidents"]), 1)

    def test_create_from_group_and_validate_selection(self):
        group_id = self.service.correlate_alerts().data["groups"][0]["group_id"]
        incident = self.service.create_incident(group_id=group_id).data["incident"]
        self.assertEqual(incident.alert_ids, [self.alert.alert_id])
        with self.assertRaises(QueryError):
            self.service.create_incident(alert_ids=["missing"])
        with self.assertRaises(QueryError):
            self.service.create_incident(alert_ids=[self.alert.alert_id, self.alert.alert_id])

    def test_lifecycle_is_forward_only(self):
        incident = self.service.create_incident(alert_ids=[self.alert.alert_id]).data["incident"]
        investigating = self.service.transition_incident(
            incident.incident_id, "investigating"
        ).data["incident"]
        self.assertEqual(investigating.status, "investigating")
        self.service.transition_incident(incident.incident_id, "closed")
        with self.assertRaises(IncidentTransitionError):
            self.service.transition_incident(incident.incident_id, "open")


if __name__ == "__main__":
    unittest.main()
