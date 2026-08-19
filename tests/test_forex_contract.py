import json
import tempfile
import unittest


class FOREXContractTests(unittest.TestCase):
    def test_forex_uses_only_public_v1_interface(self):
        from soc import SOCConfig, SOCService
        from soc.models import EventQueryV1

        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            service.ingest_event({
                "hostname": "FOREX", "event_type": "process_creation", "source": "forex",
                "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
            })
            payload = service.search_events(
                EventQueryV1(hostname="FOREX")
            ).to_dict()
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["data"]["events"][0]["host"], "FOREX")
        self.assertIn("event_uid", payload["data"]["events"][0])
        self.assertEqual(payload["data"]["events"][0]["event_id"], None)
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
