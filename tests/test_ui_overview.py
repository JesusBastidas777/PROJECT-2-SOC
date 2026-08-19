import copy
import unittest
from io import StringIO

from rich.console import Console

from soc.models import SOCResponseV1
from soc.ui.app import SOCApplication
from soc.ui.screens.overview import render_overview


class OverviewService:
    def __init__(self, center): self.center, self.calls = center, []
    def command_center(self, **options):
        self.calls.append(("command_center", options))
        return SOCResponseV1(data={"command_center": self.center})
    def ingest_event(self): pass
    def get_host_risk(self): pass
    def list_incidents(self): pass


def rendered(center, limit=5):
    output = StringIO()
    Console(file=output, width=100, no_color=True).print(render_overview(center, limit))
    return output.getvalue()


class OverviewUITests(unittest.TestCase):
    def test_empty_and_unknown_values_render_safely(self):
        output = rendered({"overall_state": None, "health": None, "integrity": None})
        for text in ("UNKNOWN", "No observed hosts", "No open incidents", "No stale incidents"):
            self.assertIn(text, output)

    def test_operational_sections_and_row_limit(self):
        center = {"overall_state": "high_risk", "health": {"state": "healthy"}, "integrity": {"invalid": 1},
                  "attention_queue": {"totals_by_priority": {"P1": 2, "P2": 1}},
                  "top_risk_hosts": [{"hostname": f"H{i}", "score": 90, "level": "high"} for i in range(4)],
                  "open_incidents": [], "stale_incidents": [], "reasons": ["urgent"],
                  "recommendations": [{"recommended_next_step": "Investigate now"}]}
        output = rendered(center, 2)
        self.assertIn("HIGH_RISK", output)
        self.assertIn("3", output)
        self.assertIn("Investigate now", output)
        self.assertNotIn("H3", output)

    def test_collect_calls_only_command_center_and_does_not_mutate_response(self):
        center = {"overall_state": "clear", "health": {"state": "healthy"}, "integrity": {}, "generated_at": "now"}
        before = copy.deepcopy(center)
        service = OverviewService(center)
        state = SOCApplication(service, view="overview").collect()
        self.assertEqual(service.calls, [("command_center", {"limit": 20})])
        self.assertEqual(center, before)
        self.assertEqual(state.updated_at, "now")


if __name__ == "__main__": unittest.main()
