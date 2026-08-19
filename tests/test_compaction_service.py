import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from storage.compaction_service import AlertCompactionService
from storage.event_reader import EventReader


NOW = datetime(2026, 8, 19, tzinfo=timezone.utc)


class AlertCompactionServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.path = self.root / "alerts.jsonl"
        records = [
            {"alert_id": "a-1", "status": "open", "timestamp": "2026-08-18T00:00:00Z"},
            {"alert_id": "legacy", "status": "open", "timestamp": "2020-01-01T00:00:00Z"},
            {"alert_id": "a-1", "status": "acknowledged", "timestamp": "2026-08-18T01:00:00Z",
             "created_at": "2026-08-18T00:00:00Z", "acknowledged_at": "2026-08-18T01:00:00Z"},
            {"alert_id": "a-1", "status": "closed", "timestamp": "2026-08-18T02:00:00Z",
             "created_at": "2026-08-18T00:00:00Z", "acknowledged_at": "2026-08-18T01:00:00Z",
             "closed_at": "2026-08-18T02:00:00Z"},
        ]
        self.path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
        self.service = AlertCompactionService(self.path, self.root / "archive")

    def tearDown(self):
        self.directory.cleanup()

    def test_plan_is_read_only(self):
        original = self.path.read_bytes()
        plan = self.service.plan()
        self.assertEqual(plan["current_alerts"], 2)
        self.assertEqual(plan["records_removed"], 2)
        self.assertEqual(self.path.read_bytes(), original)

    def test_apply_preserves_latest_lifecycle_and_archives_all_history(self):
        original = self.path.read_bytes()
        result = self.service.apply(now=NOW)
        self.assertTrue(result["applied"])
        self.assertEqual(Path(result["archive_path"]).read_bytes(), original)
        self.assertEqual(result["checksums"]["history_sha256"], hashlib.sha256(original).hexdigest())
        current = {item["alert_id"]: item for item in EventReader(self.path).read_events()}
        self.assertEqual(current["a-1"]["status"], "closed")
        self.assertEqual(current["a-1"]["closed_at"], "2026-08-18T02:00:00Z")
        self.assertEqual(current["legacy"]["status"], "open")
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], "1.0")

    def test_second_compaction_is_a_noop(self):
        self.service.apply(now=NOW)
        second = self.service.apply(now=datetime(2026, 8, 20, tzinfo=timezone.utc))
        self.assertFalse(second["applied"])
        self.assertIsNone(second["archive_path"])

    def test_invalid_records_are_preserved_in_complete_archive(self):
        with self.path.open("a", encoding="utf-8") as output:
            output.write("{broken\n")
        result = self.service.apply(now=NOW)
        self.assertEqual(result["invalid_records"], 1)
        self.assertIn(b"{broken", Path(result["archive_path"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
