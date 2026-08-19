import tempfile
import unittest

from soc import SOCConfig, SOCService
from soc.models import HostDetailV1


class HostDetailTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))

    def tearDown(self):
        self.directory.cleanup()

    def ingest(self, **values):
        event = {
            "host": "FOREX-01", "event_type": "process_creation", "source": "forex",
            "severity": "low", "timestamp": "2026-08-18T10:00:00Z",
        }
        event.update(values)
        return self.service.ingest_event(event)

    def test_combines_statistics_alerts_and_recent_activity(self):
        self.ingest(event_uid="evt-1", process_name="psexec.exe", user="alice", severity="high")
        self.ingest(event_uid="evt-2", host=" forex-01 ", process_name="cmd.exe", user="alice",
                    event_type="quote", timestamp="2026-08-18T11:00:00Z")
        self.service.create_alerts("FOREX-01")
        detail = self.service.get_host_detail("  FoReX-01  ", recent_limit=1).data["host"]
        self.assertIsInstance(detail, HostDetailV1)
        self.assertEqual(detail.total_events, 2)
        self.assertEqual(detail.events_by_source, {"forex": 2})
        self.assertEqual(detail.events_by_type, {"process_creation": 1, "quote": 1})
        self.assertEqual(detail.frequent_users[0], {"name": "alice", "count": 2})
        self.assertEqual(len(detail.recent_activity), 1)
        self.assertGreaterEqual(detail.open_alerts_by_priority.get("P2", 0), 1)

    def test_unknown_host_is_explicit(self):
        response = self.service.get_host_detail("missing")
        self.assertIsNone(response.data["host"])
        self.assertFalse(response.metadata["found"])

    def test_legacy_host_without_process_or_alert_is_supported(self):
        self.service.config.events_path.write_text(
            '{"host":"LEGACY","timestamp":"bad"}\n', encoding="utf-8"
        )
        detail = self.service.get_host_detail("legacy").data["host"]
        self.assertEqual(detail.total_events, 1)
        self.assertEqual(detail.frequent_processes, [])
        self.assertEqual(detail.open_alerts_by_priority, {})
        self.assertIsNone(detail.first_seen)

    def test_recent_limit_is_validated(self):
        self.ingest(event_uid="evt-1")
        with self.assertRaises(ValueError):
            self.service.get_host_detail("FOREX-01", recent_limit=0)


if __name__ == "__main__":
    unittest.main()
