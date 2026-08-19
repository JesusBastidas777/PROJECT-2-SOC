import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from storage.errors import StorageWriteError
from storage.event_reader import EventReader
from storage.event_store import EventStore
from storage.retention_service import RetentionService


NOW = datetime(2026, 8, 19, tzinfo=timezone.utc)


class RetentionServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.path = self.root / "events.jsonl"
        self.path.write_text("".join([
            json.dumps({"event_uid": "old", "timestamp": "2026-07-01T00:00:00Z"}) + "\n",
            json.dumps({"event_uid": "new", "timestamp": "2026-08-18T00:00:00Z"}) + "\n",
            json.dumps({"event_uid": "legacy"}) + "\n",
            "{invalid\n",
        ]), encoding="utf-8")
        store = EventStore(self.path)
        self.service = RetentionService(
            self.path, store.uid_index, self.root / "archive"
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_plan_is_read_only_and_preserves_unparseable_records(self):
        original = self.path.read_bytes()
        result = self.service.plan(max_age_days=30, now=NOW)
        self.assertEqual(result["removed_records"], 1)
        self.assertEqual(result["retained_records"], 3)
        self.assertFalse(result["applied"])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse((self.root / "archive").exists())

    def test_apply_archives_before_atomic_replacement_and_rebuilds_index(self):
        result = self.service.apply(max_age_days=30, now=NOW)
        self.assertTrue(result["applied"])
        self.assertTrue(Path(result["archive_path"]).exists())
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["checksums"]["archive_sha256"], result["checksums"]["archive_sha256"])
        events = EventReader(self.path).read_events()
        self.assertEqual([item.get("event_uid") for item in events], ["new", "legacy"])
        self.assertIsNotNone(EventStore(self.path).uid_index.ensure_current().get_event("new"))

    def test_size_policy_removes_oldest_valid_records_only(self):
        legacy_bytes = len((json.dumps({"event_uid": "legacy"}) + "\n{invalid\n").encode())
        result = self.service.apply(max_bytes=legacy_bytes + 5, now=NOW)
        self.assertGreaterEqual(result["removed_by_reason"]["size"], 1)
        self.assertIn("{invalid", self.path.read_text(encoding="utf-8"))

    def test_failure_before_replace_preserves_original(self):
        original = self.path.read_bytes()

        def fail(*args):
            raise OSError("simulated replace failure")

        self.service._write_atomic = fail
        with self.assertRaises(StorageWriteError):
            self.service.apply(max_age_days=30, now=NOW)
        self.assertEqual(self.path.read_bytes(), original)

    def test_policy_is_explicit_and_validated(self):
        with self.assertRaises(ValueError):
            self.service.plan(now=NOW)
        with self.assertRaises(ValueError):
            self.service.plan(max_bytes=0, now=NOW)


if __name__ == "__main__":
    unittest.main()
