import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class CLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.events = Path(self.directory.name) / "events.jsonl"
        self.alerts = Path(self.directory.name) / "alerts.jsonl"

    def tearDown(self):
        self.directory.cleanup()

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "soc.cli", "--events-path", str(self.events),
             "--alerts-path", str(self.alerts), *arguments],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def test_ingest_search_investigate_alerts_and_status_end_to_end(self):
        event = json.dumps({
            "hostname": "FOREX", "event_type": "process_creation", "source": "edr",
            "severity": "high", "process_name": "psexec.exe",
            "timestamp": "2026-08-18T00:00:00Z",
        })
        commands = [
            ("ingest", event), ("search", "--host", "FOREX"),
            ("investigate", "FOREX"), ("alerts", "--promote-host", "FOREX"),
            ("alerts", "--host", "FOREX", "--status", "open"), ("status",),
            ("hosts", "forex"),
            ("alerts", "--priority", "P2"),
        ]
        payloads = []
        for command in commands:
            result = self.run_cli(*command)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            payloads.append(json.loads(result.stdout))
        self.assertEqual(payloads[1]["metadata"]["count"], 1)
        self.assertGreaterEqual(payloads[4]["metadata"]["count"], 1)
        self.assertEqual(payloads[5]["data"]["health"]["state"], "healthy")
        self.assertEqual(payloads[6]["data"]["host"]["hostname"], "FOREX")
        self.assertGreaterEqual(payloads[7]["metadata"]["count"], 1)

    def test_errors_go_to_stderr_with_consistent_exit_code(self):
        result = self.run_cli("ingest", "not-json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["code"], "invalid_request")

    def test_repeated_ingestion_reports_duplicate(self):
        event = json.dumps({
            "hostname": "FOREX", "event_type": "quote", "source": "forex",
            "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
        })
        first = json.loads(self.run_cli("ingest", event).stdout)
        second = json.loads(self.run_cli("ingest", event).stdout)
        self.assertTrue(first["metadata"]["stored"])
        self.assertTrue(second["metadata"]["duplicate"])

    def test_search_accepts_uid_and_sort_order(self):
        event = json.dumps({
            "event_uid": "forex:cli-1", "host": "FOREX", "event_type": "quote",
            "source": "forex", "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
        })
        self.run_cli("ingest", event)
        result = self.run_cli("search", "--event-uid", "forex:cli-1", "--sort-order", "oldest")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["metadata"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
