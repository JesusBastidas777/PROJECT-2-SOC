import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from storage.event_reader import EventReader


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
            ("queue", "--host", "FOREX"),
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
        self.assertTrue(payloads[8]["data"]["queue"]["attention_required"])

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

    def test_search_cursor_can_be_passed_to_cli(self):
        for number in range(2):
            self.run_cli("ingest", json.dumps({
                "event_uid": f"forex:page-{number}", "host": "FOREX",
                "event_type": "quote", "source": "forex", "severity": "low",
                "timestamp": f"2026-08-18T0{number}:00:00Z",
            }))
        first = json.loads(self.run_cli("search", "--limit", "1").stdout)
        second = self.run_cli(
            "search", "--limit", "1", "--cursor", first["metadata"]["next_cursor"]
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(second.stdout)["metadata"]["has_more"])

    def test_hosts_detail_is_available_without_changing_basic_lookup(self):
        self.run_cli("ingest", json.dumps({
            "event_uid": "forex:detail", "host": "FOREX", "event_type": "quote",
            "source": "forex", "severity": "low", "timestamp": "2026-08-18T00:00:00Z",
        }))
        basic = json.loads(self.run_cli("hosts", "FOREX").stdout)
        detailed = self.run_cli("hosts", "forex", "--detail", "--recent-limit", "1")
        self.assertEqual(detailed.returncode, 0, detailed.stderr)
        self.assertEqual(basic["data"]["host"]["total_events"], 1)
        self.assertEqual(json.loads(detailed.stdout)["data"]["host"]["total_events"], 1)

    def test_retention_defaults_to_a_read_only_plan(self):
        self.run_cli("ingest", json.dumps({
            "event_uid": "forex:retain", "host": "FOREX", "event_type": "quote",
            "source": "forex", "severity": "low", "timestamp": "2020-01-01T00:00:00Z",
        }))
        plan = self.run_cli("retention", "--max-age-days", "1")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertFalse(json.loads(plan.stdout)["data"]["retention"]["applied"])
        self.assertEqual(len(EventReader(self.events).read_events()), 1)

    def test_alert_compaction_defaults_to_plan(self):
        result = self.run_cli("compact-alerts")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)["data"]["compaction"]
        self.assertFalse(payload["applied"])

    def test_backup_create_verify_and_restore_dry_run(self):
        backup = Path(self.directory.name) / "backup"
        created = self.run_cli("backup", "create", str(backup))
        verified = self.run_cli("backup", "verify", str(backup))
        restored = self.run_cli("backup", "restore", str(backup), "--dry-run")
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertTrue(json.loads(verified.stdout)["data"]["backup"]["valid"])
        self.assertTrue(json.loads(restored.stdout)["data"]["restore"]["dry_run"])

    def test_maintenance_plan_run_and_history(self):
        plan = self.run_cli(
            "maintenance", "plan", "--skip-backup", "--skip-alert-compaction"
        )
        run = self.run_cli(
            "maintenance", "run", "--skip-backup", "--skip-alert-compaction"
        )
        history = self.run_cli("maintenance", "history", "--limit", "5")
        self.assertTrue(json.loads(plan.stdout)["data"]["maintenance"]["plan_only"])
        self.assertTrue(json.loads(run.stdout)["data"]["maintenance"]["success"])
        self.assertGreaterEqual(json.loads(history.stdout)["metadata"]["count"], 2)

    def test_forex_assess_context_and_report(self):
        event = json.dumps({
            "forex_event_id": "cli-workflow", "terminal_id": "FOREX", "type": "quote",
            "severity": "low", "timestamp": "2026-08-19T00:00:00Z",
        })
        assessed = self.run_cli("forex", "assess", event)
        context = self.run_cli("forex", "context", "forex", "--recent-limit", "1")
        destination = Path(self.directory.name) / "forex-report.json"
        report = self.run_cli("forex", "report", "FOREX", str(destination))
        duplicate = self.run_cli("forex", "report", "FOREX", str(destination))
        self.assertEqual(assessed.returncode, 0, assessed.stderr)
        self.assertTrue(json.loads(context.stdout)["metadata"]["found"])
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(duplicate.returncode, 1)
        self.assertEqual(json.loads(destination.read_text())["report_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
