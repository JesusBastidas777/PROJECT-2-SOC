import tempfile
import unittest
from datetime import datetime, timezone

from risk.host_risk import HostRiskService
from soc import SOCConfig, SOCService


class HostRiskTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))

    def tearDown(self):
        self.directory.cleanup()

    def test_unknown_host_is_explicit(self):
        risk = self.service.get_host_risk("missing").data["risk"]
        self.assertFalse(risk.known_host)
        self.assertEqual((risk.score, risk.level), (0, "unknown"))

    def test_score_is_bounded_explainable_and_deduplicated(self):
        event = {
            "event_uid": "evt-risk", "host": "HOST", "event_type": "process_creation",
            "source": "edr", "severity": "high", "process_name": "psexec.exe",
            "timestamp": "2026-08-19T10:00:00Z",
        }
        self.service.ingest_event(event)
        self.service.create_alerts("HOST")
        service = HostRiskService(
            self.service._components.inventory, self.service._components.alerts,
            self.service._components.investigation.detection_engine,
            self.service._components.reader,
            now=lambda: datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
        )
        first = service.calculate("host")
        second = service.calculate("HOST")
        self.assertEqual(first["score"], second["score"])
        self.assertLessEqual(first["score"], 100)
        self.assertIn(first["level"], {"low", "moderate", "high", "critical"})
        self.assertTrue(first["factors"])
        self.assertIn("not a probability", first["explanation"])
        unique = next(item for item in first["factors"] if item["factor"] == "unique_detections")
        self.assertEqual(unique["value"], 2)


if __name__ == "__main__":
    unittest.main()
