import json
import tempfile
import unittest

from soc import SOCConfig, SOCService
from soc.errors import QueryError


class OperationalSummaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))
        for host, timestamp, severity, process in (
            ("A", "2026-08-18T10:00:00Z", "high", "psexec.exe"),
            ("A", "2026-08-18T11:00:00Z", "low", "safe.exe"),
            ("B", "2026-08-18T12:00:00Z", "medium", "safe.exe"),
        ):
            self.service.ingest_event({
                "hostname": host, "event_type": "process_creation", "source": "edr",
                "severity": severity, "process_name": process, "timestamp": timestamp,
            })
        self.service.create_alerts("A")

    def tearDown(self):
        self.directory.cleanup()

    def test_global_summary_is_deterministic_and_serializable(self):
        response = self.service.operational_summary()
        summary = response.data["summary"]
        self.assertEqual(summary.total_events, 3)
        self.assertEqual(summary.active_hosts, 2)
        self.assertEqual(summary.top_hosts[0], {"hostname": "A", "count": 2})
        self.assertEqual(summary.events_by_severity, {"high": 1, "low": 1, "medium": 1})
        self.assertTrue(summary.attention_required)
        json.dumps(response.to_dict())

    def test_window_and_host_filters_are_combined(self):
        summary = self.service.operational_summary(
            hostname="a", start_timestamp="2026-08-18T11:00:00Z",
            end_timestamp="2026-08-18T11:00:00Z",
        ).data["summary"]
        self.assertEqual(summary.total_events, 1)
        self.assertEqual(summary.last_event, "2026-08-18T11:00:00+00:00")

    def test_empty_and_invalid_windows_are_explicit(self):
        self.assertEqual(self.service.operational_summary(
            start_timestamp="2027-01-01T00:00:00Z"
        ).data["summary"].total_events, 0)
        with self.assertRaises(QueryError):
            self.service.operational_summary(start_timestamp="bad")
