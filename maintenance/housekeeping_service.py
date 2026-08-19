"""Coordinated local housekeeping with explicit stages and journaling."""

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import uuid

from storage.file_lock import exclusive_file_lock


class HousekeepingService:
    def __init__(self, integrity, backup, retention, compaction, journal, backup_dir):
        self.integrity = integrity
        self.backup = backup
        self.retention = retention
        self.compaction = compaction
        self.journal = journal
        self.backup_dir = Path(backup_dir)
        self.lock_target = journal.path.with_name("housekeeping")

    @staticmethod
    def _policy(options):
        return {
            "audit": options["audit"], "backup": options["backup"],
            "retention": options["max_age_days"] is not None or options["max_bytes"] is not None,
            "max_age_days": options["max_age_days"], "max_bytes": options["max_bytes"],
            "alert_compaction": options["alert_compaction"],
            "final_verification": options["final_verification"],
        }

    def _execute(self, name, function, steps):
        started = perf_counter()
        result = function()
        steps.append({
            "name": name, "duration_ms": round((perf_counter() - started) * 1000, 3),
            "result": result,
        })
        return result

    def run(self, *, plan_only=True, audit=True, backup=True, max_age_days=None,
            max_bytes=None, alert_compaction=True, final_verification=True, now=None):
        now = now or datetime.now(timezone.utc)
        options = {
            "audit": audit, "backup": backup, "max_age_days": max_age_days,
            "max_bytes": max_bytes, "alert_compaction": alert_compaction,
            "final_verification": final_verification,
        }
        policy = self._policy(options)
        if plan_only:
            steps = []
            if audit:
                self._execute("audit", self.integrity.audit, steps)
            if backup:
                steps.append({"name": "backup", "planned": True})
            if policy["retention"]:
                self._execute("retention", lambda: self.retention.plan(
                    max_age_days=max_age_days, max_bytes=max_bytes, now=now
                ), steps)
            if alert_compaction:
                self._execute("alert_compaction", self.compaction.plan, steps)
            if final_verification:
                self._execute("final_verification", self.integrity.audit, steps)
            return {"plan_only": True, "policy": policy, "steps": steps, "success": True}

        run_id = "maintenance-" + uuid.uuid4().hex[:16]
        started_at = now.isoformat()
        with exclusive_file_lock(self.lock_target, timeout=0):
            self.journal.append({
                "run_id": run_id, "started_at": started_at, "policy": policy,
                "state": "running",
            })
            steps = []
            artifacts = []
            success = False
            error = None
            try:
                if audit:
                    self._execute("audit", self.integrity.audit, steps)
                backup_result = None
                if backup:
                    destination = self.backup_dir / (
                        "housekeeping-" + now.strftime("%Y%m%dT%H%M%S%fZ")
                    )
                    backup_result = self._execute(
                        "backup", lambda: self.backup.create(destination, now=now), steps
                    )
                    artifacts.append(backup_result["path"])
                if policy["retention"]:
                    retention_result = self._execute("retention", lambda: self.retention.apply(
                        max_age_days=max_age_days, max_bytes=max_bytes, now=now
                    ), steps)
                    artifacts.extend(filter(None, (
                        retention_result.get("archive_path"), retention_result.get("manifest_path")
                    )))
                if alert_compaction:
                    compact_result = self._execute(
                        "alert_compaction", lambda: self.compaction.apply(now=now), steps
                    )
                    artifacts.extend(filter(None, (
                        compact_result.get("archive_path"), compact_result.get("manifest_path")
                    )))
                if final_verification:
                    def verify():
                        result = {"integrity": self.integrity.audit()}
                        if backup_result:
                            result["backup"] = self.backup.verify(backup_result["path"])
                        return result
                    self._execute("final_verification", verify, steps)
                success = True
            except Exception as exc:
                success = False
                error = {"type": type(exc).__name__, "message": str(exc)}
                raise
            finally:
                finished_at = datetime.now(timezone.utc).isoformat()
                entry = {
                    "run_id": run_id, "started_at": started_at, "finished_at": finished_at,
                    "policy": policy, "steps": steps, "artifacts": artifacts,
                    "success": success,
                }
                if error:
                    entry["error"] = error
                self.journal.append(entry)
            return {"plan_only": False, **entry}
