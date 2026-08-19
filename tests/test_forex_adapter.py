import ast
import json
import tempfile
import unittest
from pathlib import Path

from examples.forex_workflow import run_workflow
from soc import FOREXAdapter, SOCConfig, SOCService
from normalization.event_contract import EventValidationError


ROOT = Path(__file__).resolve().parent.parent


class FOREXAdapterTests(unittest.TestCase):
    def test_maps_identity_and_preserves_forex_fields(self):
        adapter = FOREXAdapter()
        event = adapter.adapt({
            "forex_event_id": "trade-42", "terminal_id": "FX-01",
            "type": "trade_execution", "symbol": "EURUSD",
        })
        self.assertEqual(event["event_uid"], "forex:trade-42")
        self.assertEqual(event["host"], "FX-01")
        self.assertEqual(event["event_type"], "trade_execution")
        self.assertEqual(event["symbol"], "EURUSD")
        self.assertEqual(event["provenance"]["producer"], "FOREX")

    def test_retry_and_complete_workflow_use_public_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            event = {
                "forex_event_id": "event-1", "terminal_id": "FOREX",
                "type": "process_creation", "severity": "high",
                "process_name": "psexec.exe", "timestamp": "2026-08-19T00:00:00Z",
            }
            first = run_workflow(service, event)
            retry = FOREXAdapter().ingest(service, event)
            self.assertTrue(retry.metadata["duplicate"])
            self.assertEqual(first["host"]["data"]["host"]["hostname"], "FOREX")
            self.assertGreaterEqual(first["alerts"]["metadata"]["count"], 1)
            self.assertTrue(first["summary"]["data"]["summary"]["attention_required"])
            json.dumps(first)

    def test_invalid_forex_event_uses_normal_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            with self.assertRaises(EventValidationError):
                FOREXAdapter().ingest(service, {"forex_event_id": "missing-host"})

    def test_examples_import_only_the_public_soc_package(self):
        for relative in ("examples/forex_adapter.py", "examples/forex_workflow.py"):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any(module and module.startswith((
                "storage", "alerting", "investigation", "detection", "normalization"
            )) for module in imports))
