import ast
import json
import tempfile
import unittest
from pathlib import Path

import soc


ROOT = Path(__file__).resolve().parent.parent


class PublicAPIContractTests(unittest.TestCase):
    def test_supported_imports_are_frozen_at_package_boundary(self):
        for name in ("SOCConfig", "SOCService", "SOCResponseV1", "EventQueryV1",
                     "FOREXAdapter", "FOREXWorkflow"):
            self.assertTrue(hasattr(soc, name), name)
            self.assertIn(name, soc.__all__)

    def test_get_alert_is_a_serializable_optional_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            response = soc.SOCService(soc.SOCConfig(base_dir=directory)).get_alert("missing")
            self.assertFalse(response.metadata["found"])
            self.assertIsNone(response.data["alert"])
            self.assertEqual(response.schema_version, "1.0")
            json.dumps(response.to_dict())

    def test_ui_and_integrations_cannot_import_private_layers(self):
        forbidden = ("storage", "alerting", "incident", "investigation", "risk", "reporting", "detection")
        directories = [ROOT / "soc" / "integrations"]
        if (ROOT / "soc" / "ui").exists():
            directories.append(ROOT / "soc" / "ui")
        for directory in directories:
            for path in directory.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
                self.assertFalse(any(module and module.startswith(forbidden) for module in modules), path)


if __name__ == "__main__":
    unittest.main()
