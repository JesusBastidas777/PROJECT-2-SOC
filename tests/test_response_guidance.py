import tempfile
import unittest

from soc import SOCConfig, SOCService


class ResponseGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))
        self.alert = self.service._components.alerts.create_alert({
            "rule_name": "sensitive_process_execution", "severity": "high",
            "reason": "test", "event": {
                "host": "HOST", "process_name": "psexec.exe",
                "timestamp": "2026-08-19T00:00:00Z",
            },
        })

    def tearDown(self):
        self.directory.cleanup()

    def test_incident_guidance_is_advisory_structured_and_descriptive(self):
        incident = self.service.create_incident(
            alert_ids=[self.alert.alert_id]
        ).data["incident"]
        guidance = self.service.recommend_response(
            incident_id=incident.incident_id
        ).data["guidance"]
        self.assertTrue(guidance["advisory_only"])
        self.assertEqual(set(guidance["recommendations"]), {
            "validate", "collect_evidence", "contain", "recover", "escalate"
        })
        for items in guidance["recommendations"].values():
            self.assertTrue(items[0]["recommendation"])
            self.assertTrue(items[0]["reason"])
            self.assertTrue(items[0]["precondition_or_risk"])
            self.assertTrue(items[0]["signals"])
        self.assertIn("Consider isolating", guidance["recommendations"]["contain"][0]["recommendation"])

    def test_unknown_rule_uses_safe_generic_alert_playbook(self):
        unknown = self.service._components.alerts.create_alert({
            "rule_name": "custom_unknown", "severity": "low", "reason": "test",
            "event": {"host": "OTHER"},
        })
        guidance = self.service.recommend_response(alert_id=unknown.alert_id).data["guidance"]
        self.assertTrue(guidance["advisory_only"])
        self.assertIn("Review the alert evidence", guidance["recommendations"]["validate"][0]["recommendation"])


if __name__ == "__main__":
    unittest.main()
