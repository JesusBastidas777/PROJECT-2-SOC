import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from storage.errors import StorageWriteError
from storage.event_reader import EventReader
from storage.event_store import EventStore
from storage.file_lock import exclusive_file_lock


class EventPersistenceTests(unittest.TestCase):
    def test_store_creates_directories_and_preserves_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "events.jsonl"
            EventStore(path).store({"host": "MÉXICO"})
            self.assertEqual(EventReader(path).read_events(), [{"host": "MÉXICO"}])
            self.assertIn("MÉXICO", path.read_text(encoding="utf-8"))

    def test_missing_file_is_an_empty_store_and_index(self):
        reader = EventReader(Path(tempfile.gettempdir()) / "soc-definitely-missing.jsonl")
        self.assertEqual(reader.read_events(), [])
        self.assertEqual(reader.find_by_host("HOST"), [])

    def test_reader_recovers_around_corrupt_and_truncated_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(
                json.dumps({"host": "A"}) + "\n{bad json\n" +
                json.dumps({"host": "B"}) + "\n{\"host\":",
                encoding="utf-8",
            )
            reader = EventReader(path)
            self.assertEqual([e["host"] for e in reader.read_events()], ["A", "B"])
            self.assertEqual(reader.invalid_line_count, 2)
            self.assertEqual(reader.find_by_host("B")[0]["host"], "B")

    def test_non_serializable_event_raises_storage_error_without_counting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            with self.assertRaises(StorageWriteError):
                store.store({"bad": object()})
            self.assertEqual(store.count(), 0)

    def test_multiple_processes_append_complete_json_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            processes = [
                subprocess.Popen([
                    sys.executable, "-c",
                    (
                        "from storage.event_store import EventStore; "
                        f"s=EventStore({str(path)!r}); "
                        f"[s.store({{'host': {str(index)!r}, 'number': n}}) for n in range(5)]"
                    ),
                ])
                for index in range(3)
            ]
            for process in processes:
                self.assertEqual(process.wait(timeout=10), 0)
            self.assertEqual(len(EventReader(path).read_events()), 15)

    def test_lock_timeout_is_structured_and_lock_is_reusable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            with exclusive_file_lock(path):
                with self.assertRaisesRegex(StorageWriteError, "timed out"):
                    EventStore(path, lock_timeout=0).store({"host": "blocked"})
            EventStore(path, lock_timeout=0).store({"host": "stored"})
            self.assertEqual(EventReader(path).read_events()[0]["host"], "stored")


if __name__ == "__main__":
    unittest.main()
