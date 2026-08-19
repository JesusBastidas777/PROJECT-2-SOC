import ast
import os
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from soc.ui.app import SOCApplication
from soc.ui.navigation import next_view, normalize_view
from soc.ui.state import UIState
from soc.ui.theme import CRITICAL, HEALTHY, INFO, MUTED, TITLE


class UIService:
    def ingest_event(self): pass
    def command_center(self): pass
    def get_host_risk(self): pass
    def list_incidents(self): pass


class UIFoundationTests(unittest.TestCase):
    def test_theme_and_navigation_are_stable(self):
        self.assertEqual((TITLE, INFO, HEALTHY, CRITICAL, MUTED), ("#808000", "yellow", "green", "red", "grey62"))
        self.assertEqual(next_view("overview"), "alerts")
        with self.assertRaises(ValueError): normalize_view("nope")

    def test_once_and_no_color_are_supported(self):
        output = StringIO()
        console = Console(file=output, width=80, no_color=True, highlight=False, markup=False)
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertEqual(SOCApplication(UIService()).run(once=True, console=console), 0)
        self.assertIn("FOREX SOC", output.getvalue())
        self.assertNotIn("\x1b[", output.getvalue())

    def test_collection_error_is_isolated(self):
        app = SOCApplication(UIService())
        app.collect = lambda: (_ for _ in ()).throw(RuntimeError("offline"))
        output = StringIO()
        app.run(once=True, console=Console(file=output, no_color=True))
        self.assertIn("DEGRADED", output.getvalue())

    def test_state_and_render_are_not_mutated(self):
        app = SOCApplication(UIService(), max_rows=5)
        state = UIState("hosts", payload={"hosts": []})
        before = repr(state)
        app.render(state)
        self.assertEqual(repr(state), before)

    def test_ui_imports_only_public_soc_surface(self):
        root = Path(__file__).resolve().parent.parent / "soc" / "ui"
        forbidden = ("storage", "alerting", "incident", "investigation", "risk", "reporting", "detection")
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any(name and name.startswith(forbidden) for name in imports), path)


if __name__ == "__main__": unittest.main()
