import tempfile
import unittest
from io import StringIO

from rich.console import Console

from soc import SOCConfig, SOCService
from soc.ui.app import SOCApplication


class IncidentsUITests(unittest.TestCase):
    def render(self, app):
        output = StringIO(); Console(file=output, width=120, no_color=True).print(app.collect().payload)
        return output.getvalue()

    def test_empty_is_safe_and_always_advisory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.render(SOCApplication(SOCService(SOCConfig(base_dir=directory)), view="incidents"))
        self.assertIn("No open incidents", output)
        self.assertIn("ADVISORY ONLY", output)

    def test_incident_alert_timeline_guidance_and_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            service.ingest_event({"event_uid": "evt", "host": "H", "event_type": "process_creation", "source": "edr", "severity": "high", "process_name": "psexec.exe"})
            alert = service.create_alerts("H").data["alerts"][0]
            incident = service.create_incident(alert_ids=[alert.alert_id]).data["incident"]
            app = SOCApplication(service, view="incidents", selected_incident=incident.incident_id, max_rows=2)
            output = self.render(app)
            app.transition_selected_incident("investigating")
        for text in (incident.incident_id, "ASSOCIATED ALERTS", "TIMELINE", "VALIDATION", "CONTAINMENT", "RECOVERY", "ESCALATION", "ADVISORY ONLY"):
            self.assertIn(text, output)

    def test_no_selection_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SOCApplication(SOCService(SOCConfig(base_dir=directory)), view="incidents")
            with self.assertRaisesRegex(ValueError, "no incident"):
                app.transition_selected_incident("closed")


if __name__ == "__main__": unittest.main()
