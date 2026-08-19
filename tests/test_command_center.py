import tempfile
import unittest
from datetime import datetime, timezone

from reporting.command_center import CommandCenter
from soc import SOCConfig, SOCService


class CommandCenterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))

    def tearDown(self):
        self.directory.cleanup()

    def test_empty_center_is_clear_and_composes_summary(self):
        center = self.service.command_center().data["command_center"]
        self.assertEqual(center["overall_state"], "clear")
        self.assertFalse(center["attention_required"])
        self.assertEqual(center["operational_summary"]["total_events"], 0)
        self.assertIn("integrity", center)

    def test_attention_risk_incidents_and_guidance_are_composed(self):
        self.service.ingest_event({
            "event_uid": "evt-center", "host": "HOST", "event_type": "process_creation",
            "source": "edr", "severity": "high", "process_name": "psexec.exe",
            "timestamp": "2026-08-19T00:00:00Z",
        })
        alert = self.service.create_alerts("HOST").data["alerts"][0]
        incident = self.service.create_incident(alert_ids=[alert.alert_id]).data["incident"]
        component = self.service._components.command_center
        center = CommandCenter(
            component.status_service, component.integrity_service,
            component.attention_queue, component.inventory, component.risk_service,
            component.incident_service, component.guidance,
            component.operational_summary,
            now=lambda: datetime(2026, 8, 21, tzinfo=timezone.utc),
        ).build()
        self.assertIn(center["overall_state"], {"attention", "high_risk"})
        self.assertTrue(center["attention_queue"]["attention_required"])
        self.assertEqual(center["open_incidents"][0].incident_id, incident.incident_id)
        self.assertEqual(center["stale_incidents"][0].incident_id, incident.incident_id)
        self.assertTrue(center["recommendations"][0]["advisory_only"])
        self.assertEqual(center["top_risk_hosts"][0]["hostname"], "HOST")


if __name__ == "__main__":
    unittest.main()
