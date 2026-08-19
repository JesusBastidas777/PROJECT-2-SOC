import tempfile
import unittest
from datetime import datetime, timezone

from alerting.attention_queue import AttentionQueue
from soc import SOCConfig, SOCService


class AttentionQueueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))
        alerts = self.service._components.alerts
        self.p4 = alerts.create_alert({
            "rule_name": "low", "severity": "low", "reason": "low",
            "event": {"host": "B", "timestamp": "2026-08-18T10:00:00Z"},
        })
        self.p2 = alerts.create_alert({
            "rule_name": "high", "severity": "high", "reason": "high",
            "event": {"host": "A", "timestamp": "2026-08-18T11:00:00Z"},
        })
        self.queue = AttentionQueue(
            alerts, now=lambda: datetime(2026, 8, 20, tzinfo=timezone.utc)
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_queue_is_ranked_and_explains_attention(self):
        result = self.queue.build()
        self.assertEqual([item["alert"].priority for item in result["entries"]], ["P2", "P4"])
        self.assertEqual(result["totals_by_priority"], {"P2": 1, "P4": 1})
        self.assertTrue(result["attention_required"])
        self.assertIn(result["entries"][0]["age_band"], {"new", "aging", "stale"})
        self.assertIn("P2 open", result["entries"][0]["attention_reason"])

    def test_acknowledged_is_opt_in_and_filters_apply(self):
        self.service.transition_alert(self.p2.alert_id, "acknowledged")
        self.assertEqual([item["alert"].alert_id for item in self.queue.build()["entries"]], [self.p4.alert_id])
        included = self.queue.build(include_acknowledged=True, hostname="A", priority="P2")
        self.assertEqual(included["entries"][0]["alert"].status, "acknowledged")

    def test_limit_does_not_hide_totals(self):
        result = self.queue.build(limit=1)
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["total"], 2)
        self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()
