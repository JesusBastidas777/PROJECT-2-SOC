import json
import tempfile
import unittest
from pathlib import Path

from storage.integrity_service import IntegrityService


class IntegrityServiceTests(unittest.TestCase):
    def test_audit_is_read_only_and_repair_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            original = json.dumps({"host": "A"}) + "\n{broken\n" + json.dumps({"host": "B"}) + "\n"
            path.write_text(original, encoding="utf-8")
            service = IntegrityService(path)
            audit = service.audit()
            self.assertEqual((audit["valid"], audit["invalid"]), (2, 1))
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            repaired = service.repair()
            self.assertTrue(repaired["repaired"])
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)
            self.assertEqual(Path(repaired["backup_path"]).read_text(encoding="utf-8"), original)
            issue = json.loads(Path(repaired["quarantine_path"]).read_text(encoding="utf-8"))
            self.assertEqual(issue["line_number"], 2)

    def test_clean_file_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text('{"host":"A"}\n', encoding="utf-8")
            result = IntegrityService(path).repair()
            self.assertFalse(result["repaired"])
            self.assertIsNone(result["backup_path"])
