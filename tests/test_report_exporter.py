import json
import tempfile
import unittest
from pathlib import Path

from reporting.report_exporter import ReportExporter
from soc.errors import QueryError


class ReportExporterTests(unittest.TestCase):
    def test_writes_json_atomically_without_overwriting_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            result = ReportExporter.write(path, {"report_version": "1.0"})
            self.assertGreater(result["bytes"], 0)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["report_version"], "1.0")
            with self.assertRaises(QueryError):
                ReportExporter.write(path, {"changed": True})
            self.assertNotIn("changed", path.read_text(encoding="utf-8"))

    def test_overwrite_must_be_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            ReportExporter.write(path, {"version": 1})
            ReportExporter.write(path, {"version": 2}, overwrite=True)
            self.assertEqual(json.loads(path.read_text())["version"], 2)


if __name__ == "__main__":
    unittest.main()
