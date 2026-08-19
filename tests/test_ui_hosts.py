import tempfile
import unittest
from io import StringIO

from rich.console import Console

from soc import SOCConfig, SOCService
from soc.ui.app import SOCApplication


class HostsUITests(unittest.TestCase):
    def render(self, service, hostname=None):
        state = SOCApplication(service, view="hosts", hostname=hostname, max_rows=2).collect()
        output = StringIO(); Console(file=output, width=120, no_color=True).print(state.payload)
        return output.getvalue()

    def test_empty_and_unknown_host_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            self.assertIn("No observed hosts", self.render(service))
            self.assertIn("Host not observed", self.render(service, "UNKNOWN"))

    def test_known_forex_host_and_case_insensitive_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            service.ingest_event({"host": "FOREX-01", "event_type": "legacy", "source": "forex", "severity": "low"})
            output = self.render(service, "forex-01")
        self.assertIn("FOREX-01", output)
        for label in ("RISK", "RECENT ACTIVITY", "DETECTIONS", "CORRELATIONS"):
            self.assertIn(label, output)

    def test_render_limits_recent_activity(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            for index in range(4):
                service.ingest_event({"event_uid": f"e{index}", "host": "H", "event_type": "x", "source": "edr", "severity": "low"})
            output = self.render(service, "H")
        self.assertIn("EVENTS", output)


if __name__ == "__main__": unittest.main()
