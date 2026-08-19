import json
import tempfile
import unittest

from soc import SOCConfig, SOCService
from soc.models import EventQueryV1, SOCResponseV1


class SOCServiceFlowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))

    def tearDown(self):
        self.directory.cleanup()

    def test_complete_ingest_search_investigate_analyze_flow(self):
        event = {
            "hostname": "FOREX-01", "event_type": "process_creation",
            "source": "edr", "severity": "high", "process_name": "psexec.exe",
            "parent_process": "services.exe", "timestamp": "2026-08-18T10:00:00Z",
        }
        ingest = self.service.ingest_event(event)
        search = self.service.search_events(EventQueryV1(hostname="FOREX-01"))
        investigation = self.service.investigate_host("FOREX-01")
        analysis = self.service.analyze_host("FOREX-01")

        for response in (ingest, search, investigation, analysis):
            self.assertIsInstance(response, SOCResponseV1)
            self.assertEqual(response.schema_version, "1.0")
            json.dumps(response.to_dict())
        self.assertEqual(search.metadata["count"], 1)
        self.assertEqual(
            ingest.data["event"]["event_uid"], search.data["events"][0]["event_uid"]
        )
        self.assertEqual(search.data["events"][0]["provenance"]["source"], "edr")
        lookup = self.service.get_event(ingest.data["event"]["event_uid"])
        self.assertTrue(lookup.metadata["found"])
        self.assertEqual(lookup.data["event"]["host"], "FOREX-01")
        self.assertEqual(investigation.data.host_profile.hostname, "FOREX-01")
        self.assertGreaterEqual(analysis.metadata["count"], 1)

    def test_services_do_not_share_runtime_state(self):
        other = SOCService(SOCConfig(base_dir=self.directory.name))
        self.assertIsNot(self.service._components.reader, other._components.reader)

    def test_ingestion_retry_is_idempotent_and_reported(self):
        event = {
            "hostname": "FOREX", "event_type": "quote", "source": "forex",
            "severity": "low", "timestamp": "2026-08-18T10:00:00Z",
        }
        first = self.service.ingest_event(event)
        second = self.service.ingest_event(event)
        self.assertEqual(first.data["event"]["event_uid"], second.data["event"]["event_uid"])
        self.assertEqual(first.metadata, {"stored": True, "duplicate": False})
        self.assertEqual(second.metadata, {"stored": False, "duplicate": True})
        self.assertEqual(self.service.search_events(hostname="FOREX").metadata["count"], 1)
        self.assertEqual(self.service.metrics().data["metrics"].duplicates_rejected, 1)

    def test_search_response_exposes_cursor_metadata(self):
        for number in range(3):
            self.service.ingest_event({
                "event_uid": f"evt-page-{number}", "host": "FOREX",
                "event_type": "quote", "source": "forex", "severity": "low",
                "timestamp": f"2026-08-18T0{number}:00:00Z",
            })
        first = self.service.search_events(hostname="FOREX", limit=2)
        second = self.service.search_events(
            hostname="FOREX", limit=2, cursor=first.metadata["next_cursor"]
        )
        self.assertTrue(first.metadata["has_more"])
        self.assertEqual(second.metadata["count"], 1)


if __name__ == "__main__":
    unittest.main()
