import tempfile
import unittest
from io import StringIO
from unittest.mock import Mock

from rich.console import Console

from soc import FOREXWorkflow, SOCConfig, SOCResponseV1, SOCService
from soc.ui.app import SOCApplication
from soc.ui.screens.forex import reference_targets


class ForexUITests(unittest.TestCase):
    def test_empty_and_unknown_terminal_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            state = SOCApplication(service, view="forex", hostname="UNKNOWN").collect()
            output = StringIO(); Console(file=output, no_color=True).print(state.payload)
        self.assertIn("not observed", output.getvalue())
        self.assertIn("No observed terminals", output.getvalue())

    def test_workflow_lists_multiple_terminals(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            for host in ("FX-1", "FX-2"):
                service.ingest_event({"host": host, "event_type": "x", "source": "forex", "severity": "low"})
            self.assertEqual(FOREXWorkflow(service).list_terminals().metadata["count"], 2)

    def test_view_calls_only_forex_workflow(self):
        posture = {"scope": "global", "state": "degraded", "risk": {"score": 9, "level": "high"},
                   "urgent_alerts": 2, "open_incidents": 1, "references": {"alert_ids": ["a"], "incident_ids": ["i"]},
                   "top_reasons": ["reason"], "recommended_next_step": "review", "generated_at": "now"}
        workflow = Mock(spec=["list_terminals", "security_posture"])
        workflow.list_terminals.return_value = SOCResponseV1(data={"terminals": ["FX"]})
        workflow.security_posture.return_value = SOCResponseV1(status="degraded", data={"posture": posture})
        service = Mock()
        state = SOCApplication(service, view="forex", workflow=workflow).collect()
        workflow.list_terminals.assert_called_once_with(); workflow.security_posture.assert_called_once_with(None)
        self.assertEqual(service.mock_calls, [])
        self.assertEqual(reference_targets(posture), {"alerts": ["a"], "hosts": [], "incidents": ["i"]})
        self.assertEqual(state.status, "degraded")


if __name__ == "__main__": unittest.main()
