import json
import tempfile
import unittest
from pathlib import Path

from investigation.event_search import EventSearch
from soc.errors import QueryError
from storage.event_reader import EventReader


class PaginationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "events.jsonl"
        with self.path.open("w", encoding="utf-8") as output:
            for number in range(5):
                output.write(json.dumps({
                    "event_uid": f"evt-{number}", "host": "FOREX",
                    "timestamp": f"2026-08-18T0{number}:00:00Z",
                }) + "\n")
        self.search = EventSearch(EventReader(self.path))

    def tearDown(self):
        self.directory.cleanup()

    def test_walks_all_pages_without_duplicates(self):
        first = self.search.search_page(hostname="FOREX", limit=2)
        second = self.search.search_page(hostname="FOREX", limit=2, cursor=first["next_cursor"])
        third = self.search.search_page(hostname="FOREX", limit=2, cursor=second["next_cursor"])
        values = first["events"] + second["events"] + third["events"]
        self.assertEqual([item["event_uid"] for item in values], [
            "evt-4", "evt-3", "evt-2", "evt-1", "evt-0",
        ])
        self.assertTrue(first["has_more"])
        self.assertFalse(third["has_more"])
        self.assertIsNone(third["next_cursor"])

    def test_cursor_is_bound_to_filters_and_order(self):
        cursor = self.search.search_page(limit=1)["next_cursor"]
        with self.assertRaises(QueryError):
            self.search.search_page(limit=1, cursor=cursor, hostname="FOREX")
        with self.assertRaises(QueryError):
            self.search.search_page(limit=1, cursor=cursor, sort_order="oldest")
        with self.assertRaises(QueryError):
            self.search.search_page(limit=1, cursor="not-a-cursor")

    def test_new_events_before_anchor_do_not_repeat_previous_page(self):
        first = self.search.search_page(limit=2)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps({
                "event_uid": "evt-new", "host": "FOREX",
                "timestamp": "2026-08-19T00:00:00Z",
            }) + "\n")
        second = self.search.search_page(limit=2, cursor=first["next_cursor"])
        returned = {item["event_uid"] for item in first["events"] + second["events"]}
        self.assertNotIn("evt-new", returned)
        self.assertEqual(len(returned), 4)

    def test_limit_is_bounded(self):
        with self.assertRaises(QueryError):
            self.search.search_page(limit=3, max_limit=2)


if __name__ == "__main__":
    unittest.main()
