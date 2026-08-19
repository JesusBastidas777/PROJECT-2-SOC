import json
import tempfile
import unittest
from pathlib import Path

from storage.event_reader import EventReader


class EventReaderTests(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.TemporaryDirectory()
        self.log_file = Path(self.temp_directory.name) / "events.jsonl"
        self.write_events([
            {"host": "HOST-01", "process_name": "powershell.exe"},
            {"host": "HOST-02", "process_name": "cmd.exe"},
        ])
        self.reader = EventReader(self.log_file)

    def tearDown(self):

        self.temp_directory.cleanup()

    def write_events(self, events):

        with self.log_file.open("w") as file:

            for event in events:

                file.write(json.dumps(event) + "\n")

    def append_event(self, event):

        with self.log_file.open("a") as file:

            file.write(json.dumps(event) + "\n")

    def test_finds_events_by_process(self):

        matches = self.reader.find_by_process("powershell.exe")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["host"], "HOST-01")

    def test_unknown_process_returns_empty_list(self):

        self.assertEqual(self.reader.find_by_process("unknown.exe"), [])

    def test_process_index_refreshes_when_log_changes(self):

        self.reader.find_by_process("powershell.exe")
        self.append_event({"host": "HOST-03", "process_name": "powershell.exe"})

        matches = self.reader.find_by_process("powershell.exe")

        self.assertEqual(len(matches), 2)

    def test_host_search_still_works(self):

        matches = self.reader.find_by_host("HOST-02")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["process_name"], "cmd.exe")

    def test_snapshot_is_reused_and_uid_index_is_available(self):
        self.write_events([{"host": "HOST", "event_uid": "evt-1"}])
        first = self.reader.read_events()
        second = self.reader.read_events()
        self.assertIsNot(first, second)
        self.assertIs(first[0], second[0])
        self.assertEqual(self.reader.find_by_uid("evt-1")["host"], "HOST")

    def test_returned_snapshot_list_cannot_mutate_reader_cache(self):
        events = self.reader.read_events()
        events.clear()
        self.assertEqual(len(self.reader.read_events()), 2)


if __name__ == "__main__":

    unittest.main()
