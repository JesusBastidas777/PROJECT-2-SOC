import unittest
from datetime import datetime

from normalization.event_normalizer import EventNormalizer


class EventNormalizerTests(unittest.TestCase):

    def setUp(self):

        self.normalizer = EventNormalizer()

    def test_preserves_valid_iso_timestamp(self):

        timestamp = "2026-08-18T12:30:00+00:00"

        normalized = self.normalizer.normalize({"timestamp": timestamp})

        self.assertEqual(normalized["timestamp"], timestamp)

    def test_adds_utc_timestamp_when_missing(self):

        normalized = self.normalizer.normalize({})
        timestamp = datetime.fromisoformat(normalized["timestamp"])

        self.assertIsNotNone(timestamp.tzinfo)
        self.assertEqual(timestamp.utcoffset().total_seconds(), 0)

    def test_replaces_invalid_timestamp(self):

        normalized = self.normalizer.normalize({"timestamp": "not-a-date"})

        self.assertNotEqual(normalized["timestamp"], "not-a-date")
        self.assertIsNotNone(datetime.fromisoformat(normalized["timestamp"]).tzinfo)


if __name__ == "__main__":

    unittest.main()
