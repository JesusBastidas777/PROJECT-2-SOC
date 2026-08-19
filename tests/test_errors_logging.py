import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from investigation.event_search import EventSearch
from normalization.event_contract import EventValidationError
from soc.errors import QueryError, SOCError, ValidationError
from storage.event_reader import EventReader


class ErrorsAndLoggingTests(unittest.TestCase):
    def test_domain_errors_are_structured(self):
        error = QueryError("bad filter", details={"filter": "limit"})
        self.assertIsInstance(error, SOCError)
        self.assertEqual(error.to_dict(), {
            "code": "query_error", "message": "bad filter",
            "details": {"filter": "limit"},
        })
        self.assertTrue(issubclass(EventValidationError, ValidationError))

    def test_invalid_filters_raise_query_errors(self):
        search = EventSearch(EventReader(Path(tempfile.gettempdir()) / "missing-soc.jsonl"))
        for arguments in (
            {"limit": 0}, {"start_timestamp": "bad"},
            {"start_timestamp": "2026-02-02T00:00:00Z", "end_timestamp": "2026-01-01T00:00:00Z"},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(QueryError):
                search.search(**arguments)

    def test_corruption_logs_warning_without_writing_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("{broken\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertLogs(
                "storage.event_reader", level="WARNING"
            ) as logs:
                EventReader(path).read_events()
            self.assertEqual(output.getvalue(), "")
            self.assertIn("invalid event log line", logs.output[0])


if __name__ == "__main__":
    unittest.main()
