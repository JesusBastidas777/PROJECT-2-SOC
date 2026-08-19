import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from soc import SOCConfig, SOCService
from storage.backup_service import BackupService
from storage.errors import StorageReadError, StorageWriteError
from storage.event_store import EventStore


NOW = datetime(2026, 8, 19, tzinfo=timezone.utc)


class BackupServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.events = self.root / "events.jsonl"
        self.alerts = self.root / "alerts.jsonl"
        store = EventStore(self.events)
        store.store_once({"event_uid": "evt-original", "host": "FOREX"})
        EventStore(self.alerts).store({"alert_id": "alert-original", "status": "open"})
        self.service = BackupService(
            self.events, self.alerts, store.uid_index, self.root / "safety"
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_create_and_verify_include_both_stores(self):
        destination = self.root / "backup"
        result = self.service.create(destination, now=NOW)
        self.assertTrue(result["created"])
        verification = self.service.verify(destination)
        self.assertTrue(verification["valid"])
        self.assertEqual(verification["manifest"]["logical_signature"], "soc-jsonl-v1")
        self.assertEqual(set(verification["manifest"]["files"]), {"events", "alerts"})

    def test_tampering_is_detected_and_cannot_be_restored(self):
        destination = self.root / "backup"
        self.service.create(destination, now=NOW)
        (destination / "events.jsonl").write_text("tampered", encoding="utf-8")
        self.assertFalse(self.service.verify(destination)["valid"])
        with self.assertRaises(StorageReadError):
            self.service.restore(destination)

    def test_dry_run_does_not_change_active_state(self):
        destination = self.root / "backup"
        self.service.create(destination, now=NOW)
        original = self.events.read_bytes()
        result = self.service.restore(destination, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(self.events.read_bytes(), original)

    def test_restore_creates_safety_backup_and_rebuilds_uid_index(self):
        destination = self.root / "backup"
        self.service.create(destination, now=NOW)
        self.events.write_text('{"event_uid":"evt-mutated"}\n', encoding="utf-8")
        self.alerts.write_text('{"alert_id":"alert-mutated"}\n', encoding="utf-8")
        result = self.service.restore(
            destination, now=datetime(2026, 8, 20, tzinfo=timezone.utc)
        )
        self.assertTrue(result["restored"])
        self.assertTrue(Path(result["safety_backup_path"]).exists())
        self.assertIn("evt-original", self.events.read_text(encoding="utf-8"))
        self.assertIn("alert-original", self.alerts.read_text(encoding="utf-8"))
        self.assertIsNotNone(self.service.uid_index.ensure_current().get_event("evt-original"))

    def test_failed_second_replace_rolls_back_both_active_files(self):
        destination = self.root / "backup"
        self.service.create(destination, now=NOW)
        self.events.write_text('{"event_uid":"evt-current"}\n', encoding="utf-8")
        self.alerts.write_text('{"alert_id":"alert-current"}\n', encoding="utf-8")
        before = self.events.read_bytes(), self.alerts.read_bytes()
        original = self.service._atomic_file
        calls = 0

        def fail_once(path, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated alert replace failure")
            return original(path, data)

        self.service._atomic_file = fail_once
        with self.assertRaises(StorageWriteError):
            self.service.restore(destination, now=datetime(2026, 8, 21, tzinfo=timezone.utc))
        self.assertEqual((self.events.read_bytes(), self.alerts.read_bytes()), before)


if __name__ == "__main__":
    unittest.main()
