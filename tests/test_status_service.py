import json
import tempfile
import unittest

from soc import SOCConfig, SOCService


class StatusServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = SOCConfig(base_dir=self.directory.name)
        self.service = SOCService(self.config)

    def tearDown(self):
        self.directory.cleanup()

    def test_health_and_metrics_are_serializable_and_track_operations(self):
        self.service.ingest_event({
            "hostname": "HOST", "event_type": "process_creation", "source": "edr",
            "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
        })
        self.service.search_events(hostname="HOST")
        self.service.investigate_host("HOST")
        self.service.analyze_host("HOST")
        health = self.service.health().to_dict()
        metrics = self.service.metrics().to_dict()["data"]["metrics"]
        self.assertEqual(health["data"]["health"]["state"], "healthy")
        self.assertEqual(metrics["events_stored"], 1)
        self.assertIsNotNone(metrics["last_ingestion"])
        self.assertEqual(set(metrics["operation_durations_ms"]), {
            "ingest_event", "search_events", "investigate_host", "analyze_host"
        })
        json.dumps(health)
        json.dumps(metrics)

    def test_open_alerts_and_invalid_events_make_metrics_and_health_useful(self):
        self.service.ingest_event({
            "hostname": "HOST", "event_type": "process_creation", "source": "edr",
            "severity": "high", "process_name": "psexec.exe",
            "timestamp": "2026-08-18T00:00:00Z",
        })
        self.service.create_alerts("HOST")
        with self.config.events_path.open("a", encoding="utf-8") as file:
            file.write("{truncated")
        metrics = self.service.metrics().data["metrics"]
        self.assertEqual(metrics.open_alerts, 2)
        self.assertEqual(metrics.invalid_events, 1)
        self.assertEqual(self.service.health().data["health"].state, "degraded")


if __name__ == "__main__":
    unittest.main()
