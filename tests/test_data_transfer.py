import json
import tempfile
import unittest
from pathlib import Path

from soc import SOCConfig, SOCService


class DataTransferTests(unittest.TestCase):
    def test_filtered_export_and_idempotent_import_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = SOCService(SOCConfig(base_dir=root / "source"))
            for host in ("A", "B"):
                source.ingest_event({
                    "hostname": host, "event_type": "test", "source": "edr",
                    "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
                })
            exported = root / "transfer" / "events.jsonl"
            self.assertEqual(source.export_events(exported, hostname="A").data["export"]["exported"], 1)
            target = SOCService(SOCConfig(base_dir=root / "target"))
            first = target.import_events(exported).data["import"]
            second = target.import_events(exported).data["import"]
            self.assertEqual((first["stored"], second["duplicates"]), (1, 1))
            self.assertEqual(target.search_events().metadata["count"], 1)

    def test_dry_run_and_invalid_lines_do_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "input.jsonl"
            path.write_text(json.dumps({
                "host": "A", "event_type": "test", "source": "edr", "severity": "low",
                "timestamp": "2026-08-18T00:00:00Z",
            }) + "\n{bad\n", encoding="utf-8")
            service = SOCService(SOCConfig(base_dir=root / "soc"))
            result = service.import_events(path, dry_run=True).data["import"]
            self.assertEqual((result["stored"], result["invalid"]), (1, 1))
            self.assertEqual(service.search_events().metadata["count"], 0)

    def test_bulk_import_reuses_the_uid_index_without_rebuilding_per_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.jsonl"
            source.write_text("".join(
                json.dumps({
                    "event_uid": f"evt-{number}", "host": "A", "event_type": "test",
                    "source": "edr", "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
                }) + "\n" for number in range(20)
            ), encoding="utf-8")
            service = SOCService(SOCConfig(base_dir=root / "soc"))
            index = service._components.store.uid_index
            calls = 0
            original = index.rebuild

            def counted_rebuild():
                nonlocal calls
                calls += 1
                return original()

            index.rebuild = counted_rebuild
            result = service.import_events(source).data["import"]
            self.assertEqual(result["stored"], 20)
            self.assertEqual(calls, 1)
