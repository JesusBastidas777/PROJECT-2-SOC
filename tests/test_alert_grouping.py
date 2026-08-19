import tempfile
import unittest

from correlation.alert_grouping import AlertGrouping
from soc import SOCConfig, SOCService


class AlertGroupingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))
        for uid, process, rule in (
            ("evt-1", "powershell.exe", "sensitive_process_execution"),
            ("evt-2", "powershell.exe", "office_spawned_command_interpreter"),
        ):
            self.service._components.alerts.create_alert({
                "rule_name": rule, "severity": "high", "reason": "test",
                "event": {
                    "event_uid": uid, "host": "HOST", "process_name": process,
                    "timestamp": "2026-08-19T10:00:00Z",
                },
            })

    def tearDown(self):
        self.directory.cleanup()

    def test_related_alerts_form_stable_explainable_group(self):
        first = self.service.correlate_alerts().data["groups"]
        second = self.service.correlate_alerts().data["groups"]
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["group_id"], second[0]["group_id"])
        self.assertEqual(len(first[0]["alert_ids"]), 2)
        self.assertIn("related_process", first[0]["reasons"])
        self.assertIn("score", first[0]["host_risk"])

    def test_singletons_can_be_excluded(self):
        alerts = self.service._components.alerts
        alerts.create_alert({
            "rule_name": "unrelated", "severity": "low", "reason": "test",
            "event": {
                "event_uid": "evt-3", "host": "OTHER", "process_name": "safe.exe",
                "timestamp": "2026-08-19T10:00:00Z",
            },
        })
        groups = self.service.correlate_alerts(include_singletons=False).data["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["hostname"], "HOST")

    def test_correlation_does_not_change_alerts(self):
        before = self.service.search_alerts().to_dict()
        self.service.correlate_alerts()
        self.assertEqual(self.service.search_alerts().to_dict(), before)


if __name__ == "__main__":
    unittest.main()
