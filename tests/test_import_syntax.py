import ast
import unittest
from pathlib import Path


class ImportSyntaxTests(unittest.TestCase):
    def test_ui_has_no_private_domain_imports(self):
        root = Path(__file__).resolve().parent.parent / "soc" / "ui"
        forbidden = ("storage", "alerting", "incident", "investigation", "risk", "reporting", "detection")
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any(name and name.startswith(forbidden) for name in names), path)


if __name__ == "__main__": unittest.main()
