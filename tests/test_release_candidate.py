import json
import tempfile
import unittest
from pathlib import Path
from io import StringIO

from rich.console import Console

from soc import FOREXWorkflow, SOCConfig, SOCService
from soc.ui.app import SOCApplication


class ReleaseCandidateTests(unittest.TestCase):
    def test_package_metadata_declares_entrypoint_and_rich(self):
        metadata = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('soc = "soc.cli:main"', metadata)
        self.assertIn('"rich==15.0.0"', metadata)
        self.assertIn('"storage*"', metadata)

    def test_end_to_end_event_incident_posture_and_all_views(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            service.ingest_event({"event_uid": "rc-event", "host": "FOREX-01", "event_type": "process_creation", "source": "forex", "severity": "high", "process_name": "psexec.exe"})
            alert = service.create_alerts("FOREX-01").data["alerts"][0]
            service.create_incident(alert_ids=[alert.alert_id])
            json.dumps(FOREXWorkflow(service).security_posture("FOREX-01").to_dict())
            for view in ("overview", "alerts", "hosts", "incidents", "forex"):
                state = SOCApplication(service, view=view, hostname="FOREX-01", max_rows=3).refresh()
                output = StringIO(); Console(file=output, width=70, no_color=True).print(state.payload)
                self.assertTrue(output.getvalue(), view)

    def test_empty_repository_all_views(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            for view in ("overview", "alerts", "hosts", "incidents", "forex"):
                self.assertIsNotNone(SOCApplication(service, view=view).refresh())


if __name__ == "__main__": unittest.main()
