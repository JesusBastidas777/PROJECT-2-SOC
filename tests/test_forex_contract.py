import json
import ast
import tempfile
import unittest
from pathlib import Path


class FOREXContractTests(unittest.TestCase):
    def test_forex_uses_only_public_v1_interface(self):
        from soc import FOREXAdapter, FOREXWorkflow, SOCConfig, SOCService
        from soc.models import EventQueryV1

        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            FOREXAdapter().ingest(service, {
                "forex_event_id": "contract-1",
                "hostname": "FOREX", "event_type": "process_creation", "source": "forex",
                "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
            })
            payload = service.search_events(
                EventQueryV1(hostname="FOREX")
            ).to_dict()
            self.assertEqual(
                FOREXWorkflow(service).get_terminal_context("FOREX").schema_version, "1.0"
            )
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["data"]["events"][0]["host"], "FOREX")
        self.assertIn("event_uid", payload["data"]["events"][0])
        self.assertEqual(payload["data"]["events"][0]["event_id"], None)
        json.dumps(payload)

    def test_forex_workflow_does_not_import_internal_soc_layers(self):
        path = Path(__file__).resolve().parent.parent / "soc" / "integrations" / "forex.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        forbidden = ("storage", "alerting", "detection", "investigation", "incident")
        self.assertFalse(any(module and module.startswith(forbidden) for module in imports))


if __name__ == "__main__":
    unittest.main()
