import tempfile
import unittest

from soc import SOCConfig, SOCService


class HostCatalogTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))

    def tearDown(self):
        self.directory.cleanup()

    def ingest(self, host, timestamp, severity="low", source="edr", suffix=""):
        return self.service.ingest_event({
            "hostname": host, "event_type": "process_creation", "source": source,
            "severity": severity, "timestamp": timestamp, "vendor_value": suffix,
        })

    def test_inventory_consolidates_safe_name_variants(self):
        self.ingest(" HOST-01 ", "2026-08-18T11:00:00Z", suffix="a")
        self.ingest("host-01", "2026-08-18T10:00:00Z", "high", "sysmon", "b")
        response = self.service.list_hosts()
        host = response.data["hosts"][0]
        self.assertEqual(response.metadata["count"], 1)
        self.assertEqual(host.total_events, 2)
        self.assertEqual(host.first_seen, "2026-08-18T10:00:00+00:00")
        self.assertEqual(host.max_severity, "high")
        self.assertEqual(host.sources, ["edr", "sysmon"])
        self.assertEqual(set(host.observed_names), {"HOST-01", "host-01"})

    def test_get_is_case_insensitive_and_unknown_is_explicit(self):
        self.ingest("FOREX", "2026-08-18T10:00:00Z")
        self.assertEqual(self.service.get_host(" forex ").data["host"].hostname, "FOREX")
        missing = self.service.get_host("unknown")
        self.assertIsNone(missing.data["host"])
        self.assertFalse(missing.metadata["found"])

    def test_open_alerts_are_included(self):
        self.service.ingest_event({
            "hostname": "HOST", "event_type": "process_creation", "source": "edr",
            "severity": "high", "process_name": "psexec.exe",
            "timestamp": "2026-08-18T10:00:00Z",
        })
        self.service.create_alerts("HOST")
        self.assertEqual(self.service.get_host("HOST").data["host"].open_alerts, 2)
