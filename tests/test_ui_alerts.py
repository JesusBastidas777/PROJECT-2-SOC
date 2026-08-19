import unittest
from io import StringIO
from types import SimpleNamespace

from rich.console import Console

from soc.models import SOCResponseV1
from soc.ui.app import SOCApplication
from soc.ui.screens.alerts import alert_state, render_alerts


def alert(identifier, priority="P1", **values):
    base = dict(alert_id=identifier, priority=priority, hostname="HOST", status="open",
                rule_name="rule", severity="high", event={}, event_uid=None)
    base.update(values)
    return SimpleNamespace(**base)


class AlertServiceStub:
    def __init__(self, entries): self.entries, self.transitions, self.reads = entries, [], 0
    def ingest_event(self): pass
    def command_center(self): pass
    def get_host_risk(self): pass
    def list_incidents(self): pass
    def attention_queue(self, **filters):
        self.reads += 1
        return SOCResponseV1(data={"queue": {"entries": self.entries, "total": len(self.entries)}})
    def transition_alert(self, alert_id, status):
        self.transitions.append((alert_id, status)); return SOCResponseV1(data={})


class AlertsUITests(unittest.TestCase):
    def test_empty_legacy_and_priority_order_render(self):
        output = StringIO(); Console(file=output, no_color=True).print(render_alerts(alert_state({"entries": []})))
        self.assertIn("No active alerts", output.getvalue())
        entries = [{"alert": alert("4", "P4"), "attention_reason": None}, {"alert": alert("1", "P1"), "age_band": None}]
        state = alert_state({"entries": sorted(entries, key=lambda item: item["alert"].priority)})
        self.assertEqual(state["selected_id"], "1")
        Console(file=StringIO(), no_color=True).print(render_alerts(state))

    def test_selection_clears_safely_and_refresh_is_read_only(self):
        self.assertIsNone(alert_state({"entries": []}, "gone")["selected_id"])
        service = AlertServiceStub([{"alert": alert("a"), "age_band": "unknown", "attention_reason": "review"}])
        app = SOCApplication(service, view="alerts", selected_alert="a")
        app.collect(); app.collect()
        self.assertEqual(service.transitions, [])
        app.transition_selected_alert("acknowledged")
        self.assertEqual(service.transitions, [("a", "acknowledged")])

    def test_invalid_transition_error_remains_public(self):
        service = AlertServiceStub([])
        with self.assertRaisesRegex(ValueError, "no alert"):
            SOCApplication(service, view="alerts").transition_selected_alert("closed")


if __name__ == "__main__": unittest.main()
