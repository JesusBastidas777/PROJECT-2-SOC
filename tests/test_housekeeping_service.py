import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from maintenance.operational_journal import OperationalJournal
from soc import SOCConfig, SOCService
from storage.errors import StorageWriteError
from storage.file_lock import exclusive_file_lock


NOW = datetime(2026, 8, 19, tzinfo=timezone.utc)


class HousekeepingServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = SOCService(SOCConfig(base_dir=self.directory.name))
        self.service.ingest_event({
            "event_uid": "evt-old", "host": "FOREX", "event_type": "quote",
            "source": "forex", "severity": "low", "timestamp": "2020-01-01T00:00:00Z",
        })

    def tearDown(self):
        self.directory.cleanup()

    def test_plan_is_read_only_and_in_dependency_order(self):
        journal = self.service.config.maintenance_journal_path
        result = self.service._components.housekeeping.run(
            plan_only=True, max_age_days=30, now=NOW
        )
        self.assertEqual([step["name"] for step in result["steps"]], [
            "audit", "backup", "retention", "alert_compaction", "final_verification",
        ])
        self.assertFalse(journal.exists())
        self.assertEqual(self.service.search_events().metadata["count"], 1)

    def test_run_records_results_artifacts_and_status(self):
        result = self.service._components.housekeeping.run(
            plan_only=False, max_age_days=30, now=NOW
        )
        self.assertTrue(result["success"])
        self.assertEqual([step["name"] for step in result["steps"]], [
            "audit", "backup", "retention", "alert_compaction", "final_verification",
        ])
        self.assertTrue(result["artifacts"])
        completed = self.service._components.journal.latest_completed()
        self.assertEqual(completed["run_id"], result["run_id"])
        self.assertEqual(self.service.status().data["maintenance_last"]["run_id"], result["run_id"])

    def test_stages_can_be_disabled(self):
        result = self.service._components.housekeeping.run(
            plan_only=False, audit=False, backup=False, alert_compaction=False,
            final_verification=False, now=NOW,
        )
        self.assertEqual(result["steps"], [])
        self.assertTrue(result["success"])

    def test_two_runs_cannot_overlap(self):
        housekeeping = self.service._components.housekeeping
        with exclusive_file_lock(housekeeping.lock_target):
            with self.assertRaises(StorageWriteError):
                housekeeping.run(
                    plan_only=False, audit=False, backup=False,
                    alert_compaction=False, final_verification=False, now=NOW,
                )

    def test_failure_is_written_to_the_journal(self):
        housekeeping = self.service._components.housekeeping

        def fail():
            raise RuntimeError("simulated audit failure")

        housekeeping.integrity.audit = fail
        with self.assertRaises(RuntimeError):
            housekeeping.run(
                plan_only=False, backup=False, alert_compaction=False,
                final_verification=False, now=NOW,
            )
        self.assertFalse(housekeeping.journal.latest_completed()["success"])


class OperationalJournalTests(unittest.TestCase):
    def test_truncated_last_line_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operations.jsonl"
            journal = OperationalJournal(path)
            journal.append({"run_id": "one", "finished_at": "now", "success": True})
            with path.open("a", encoding="utf-8") as output:
                output.write('{"run_id":')
            self.assertEqual(journal.latest_completed()["run_id"], "one")


if __name__ == "__main__":
    unittest.main()
