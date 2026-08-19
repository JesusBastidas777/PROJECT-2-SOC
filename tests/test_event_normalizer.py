import unittest
from datetime import datetime

from normalization.event_contract import EventValidationError
from normalization.event_normalizer import EventNormalizer


class EventNormalizerTests(unittest.TestCase):

    def setUp(self):

        self.normalizer = EventNormalizer()

    def test_preserves_valid_iso_timestamp(self):

        timestamp = "2026-08-18T12:30:00+00:00"

        normalized = self.normalizer.normalize(self.complete_event(timestamp=timestamp))

        self.assertEqual(normalized["timestamp"], timestamp)

    def test_adds_utc_timestamp_when_missing(self):

        normalized = self.normalizer.normalize(self.complete_event(timestamp=None))
        timestamp = datetime.fromisoformat(normalized["timestamp"])

        self.assertIsNotNone(timestamp.tzinfo)
        self.assertEqual(timestamp.utcoffset().total_seconds(), 0)

    def test_rejects_invalid_timestamp(self):

        with self.assertRaises(EventValidationError):
            self.normalizer.normalize(self.complete_event(timestamp="not-a-date"))

    def test_preserves_process_investigation_context(self):

        event = {
            "pid": 1234,
            "parent_process": "winword.exe",
            "user": "analyst",
            "event_type": "process_creation",
            "source": "edr",
            "severity": "high",
            "hostname": "HOST-01",
        }

        normalized = self.normalizer.normalize(event)

        for field, value in event.items():

            if field == "hostname":
                continue

            self.assertEqual(normalized[field], value)

        self.assertEqual(normalized["host"], event["hostname"])

    def test_old_process_event_receives_optional_fields(self):

        normalized = self.normalizer.normalize({
            "hostname": "DESKTOP-01",
            "event_id": 4688,
            "process_name": "powershell.exe",
            "event_type": "process_creation", "source": "legacy", "severity": "low",
        })

        self.assertEqual(normalized["host"], "DESKTOP-01")
        self.assertEqual(normalized["process_name"], "powershell.exe")
        for field in (
            "pid", "parent_process", "user"
        ):

            self.assertIsNone(normalized[field])

    def complete_event(self, **overrides):
        event = {
            "hostname": "HOST-01", "event_type": "process_creation",
            "source": "edr", "severity": "low",
            "timestamp": "2026-08-18T12:30:00+00:00",
        }
        event.update(overrides)
        return event

    def test_requires_canonical_fields(self):
        with self.assertRaisesRegex(EventValidationError, "event_type"):
            self.normalizer.normalize({"hostname": "HOST-01", "source": "edr", "severity": "low"})

    def test_normalizes_offset_to_utc_and_preserves_extended_fields(self):
        normalized = self.normalizer.normalize(self.complete_event(
            timestamp="2026-08-18T06:30:00-06:00", dst_ip="10.0.0.2",
            file_hash="abc", vendor_field="retained",
        ))
        self.assertEqual(normalized["timestamp"], "2026-08-18T12:30:00+00:00")
        self.assertEqual(normalized["dst_ip"], "10.0.0.2")
        self.assertEqual(normalized["file_hash"], "abc")
        self.assertEqual(normalized["vendor_field"], "retained")

    def test_adds_stable_identity_and_provenance_without_reusing_event_id(self):
        event = self.complete_event(event_id=4688)
        first = self.normalizer.normalize(event)
        second = self.normalizer.normalize(event)
        self.assertEqual(first["event_uid"], second["event_uid"])
        self.assertTrue(first["event_uid"].startswith("evt-"))
        self.assertEqual(first["event_id"], 4688)
        self.assertEqual(first["provenance"], {"source": "edr"})
        self.assertEqual(first["event_schema_version"], "1.0")
        self.assertIsNotNone(datetime.fromisoformat(first["ingested_at"]).tzinfo)

    def test_preserves_valid_producer_uid_and_rejects_invalid_uid(self):
        normalized = self.normalizer.normalize(self.complete_event(event_uid="forex:42"))
        self.assertEqual(normalized["event_uid"], "forex:42")
        with self.assertRaisesRegex(EventValidationError, "event_uid"):
            self.normalizer.normalize(self.complete_event(event_uid="bad uid"))

    def test_identity_changes_when_event_content_changes(self):
        first = self.normalizer.normalize(self.complete_event(process_name="one.exe"))
        second = self.normalizer.normalize(self.complete_event(process_name="two.exe"))
        self.assertNotEqual(first["event_uid"], second["event_uid"])


if __name__ == "__main__":

    unittest.main()
