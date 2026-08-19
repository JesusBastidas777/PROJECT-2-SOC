import ast
import json
import tempfile
import unittest
from pathlib import Path

from examples.forex_workflow import get_security_posture, run_workflow
from soc import FOREXAdapter, FOREXWorkflow, SOCConfig, SOCService
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
            self.assertEqual(first["data"]["host"]["hostname"], "FOREX")
            self.assertGreaterEqual(len(first["data"]["alerts"]), 1)
            self.assertTrue(first["data"]["summary"]["attention_required"])
            json.dumps(first)

    def test_workflow_context_and_portable_report_use_public_responses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = SOCService(SOCConfig(base_dir=root / "soc"))
            workflow = FOREXWorkflow(service)
            assessed = workflow.ingest_and_assess({
                "forex_event_id": "workflow-1", "terminal_id": "FOREX",
                "type": "process_creation", "severity": "high",
                "process_name": "psexec.exe", "timestamp": "2026-08-19T00:00:00Z",
            })
            context = workflow.get_terminal_context("forex", recent_limit=1)
            destination = root / "reports" / "terminal.json"
            exported = workflow.export_terminal_report(
                "FOREX", destination, recent_limit=1,
                generated_at="2026-08-19T12:00:00+00:00",
            )
            self.assertEqual(assessed.schema_version, "1.0")
            self.assertTrue(context.metadata["found"])
            report = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(report["report_version"], "1.0")
            self.assertEqual(report["identity"]["hostname"], "FOREX")
            self.assertEqual(report["generated_at"], "2026-08-19T12:00:00+00:00")
            for field in ("statistics", "recent_events", "detections", "alerts", "summary"):
                self.assertIn(field, report)
            self.assertEqual(exported.data["export"]["path"], str(destination))

    def test_invalid_forex_event_uses_normal_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            with self.assertRaises(EventValidationError):
                FOREXAdapter().ingest(service, {"forex_event_id": "missing-host"})

    def test_security_posture_is_compact_for_global_and_terminal_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            FOREXWorkflow(service).ingest_and_assess({
                "forex_event_id": "posture-1", "terminal_id": "FOREX-01",
                "type": "process_creation", "severity": "high",
                "process_name": "psexec.exe", "timestamp": "2026-08-19T00:00:00Z",
            })
            terminal = FOREXWorkflow(service).security_posture("FOREX-01")
            global_posture = get_security_posture(service)
        posture = terminal.data["posture"]
        self.assertEqual(terminal.schema_version, "1.0")
        self.assertIn(posture["state"], {"clear", "attention", "high_risk", "degraded"})
        self.assertTrue(posture["attention_required"])
        self.assertGreaterEqual(posture["urgent_alerts"], 1)
        self.assertNotIn("events", posture)
        self.assertEqual(posture["scope"], "terminal")
        self.assertTrue(posture["observed"])
        self.assertEqual(global_posture["schema_version"], "1.0")

    def test_unknown_terminal_returns_safe_unobserved_posture(self):
        with tempfile.TemporaryDirectory() as directory:
            response = FOREXWorkflow(SOCService(SOCConfig(base_dir=directory))).security_posture("UNKNOWN")
        posture = response.data["posture"]
        self.assertFalse(posture["observed"])
        self.assertEqual(posture["risk"]["score"], 0)
        self.assertEqual(posture["scope"], "terminal")
        json.dumps(response.to_dict())

    def test_examples_import_only_the_public_soc_package(self):
        for relative in ("examples/forex_adapter.py", "examples/forex_workflow.py"):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any(module and module.startswith((
                "storage", "alerting", "investigation", "detection", "normalization"
            )) for module in imports))
