"""Persist detections as deduplicated, actionable alerts."""

import hashlib
import json
from datetime import datetime, timezone

from soc.errors import AlertTransitionError, QueryError
from soc.models import AlertV1, DetectionV1
from storage.event_reader import EventReader
from storage.event_store import EventStore


VALID_STATUSES = {"open", "acknowledged", "closed"}
VALID_PRIORITIES = {"P1", "P2", "P3", "P4"}
SEVERITY_PRIORITIES = {"critical": "P1", "high": "P2", "medium": "P3", "low": "P4"}
TRANSITIONS = {
    "open": {"acknowledged", "closed"},
    "acknowledged": {"closed"},
    "closed": set(),
}


class AlertService:
    def __init__(self, log_file, lock_timeout=5.0):
        self.reader = EventReader(log_file)
        self.store = EventStore(log_file, lock_timeout=lock_timeout)

    @staticmethod
    def _identity(detection):
        event = detection.get("event") or {}
        identity = {
            "rule_name": detection.get("rule_name"),
            "host": event.get("host") or event.get("hostname"),
            "event_id": event.get("event_id"),
            "timestamp": event.get("timestamp"),
            "process_name": event.get("process_name"),
        }
        payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return "alert-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    def _latest(self):
        return {item["alert_id"]: item for item in self.reader.read_events() if item.get("alert_id")}

    def create_alert(self, detection):
        if isinstance(detection, DetectionV1):
            detection = {
                "rule_name": detection.rule_name, "severity": detection.severity,
                "reason": detection.reason, "event": detection.event,
            }
        alert_id = self._identity(detection)
        existing = self._latest().get(alert_id)
        if existing:
            return AlertV1.from_mapping(existing)
        event = dict(detection.get("event") or {})
        now = datetime.now(timezone.utc).isoformat()
        priority = detection.get("priority") or SEVERITY_PRIORITIES.get(
            str(detection.get("severity") or "").lower(), "P4"
        )
        if priority not in VALID_PRIORITIES:
            raise QueryError(f"invalid alert priority: {priority}")
        alert = AlertV1(
            alert_id=alert_id,
            timestamp=now,
            status="open",
            hostname=event.get("host") or event.get("hostname") or "unknown",
            severity=str(detection.get("severity") or "unknown").lower(),
            rule_name=detection.get("rule_name") or "unknown",
            reason=detection.get("reason") or "",
            event=event,
            priority=priority,
            event_uid=event.get("event_uid"),
            created_at=now,
            updated_at=now,
        )
        self.store.store(alert.__dict__)
        return alert

    def promote(self, detections):
        return [self.create_alert(item) for item in detections]

    def transition(self, alert_id, status):
        if status not in VALID_STATUSES:
            raise AlertTransitionError(f"invalid alert status: {status}")
        current = self._latest().get(alert_id)
        if current is None:
            raise QueryError(f"unknown alert: {alert_id}")
        if status == current["status"]:
            return AlertV1.from_mapping(current)
        if status not in TRANSITIONS[current["status"]]:
            raise AlertTransitionError(
                f"cannot transition alert from {current['status']} to {status}"
            )
        updated = dict(current)
        updated["status"] = status
        now = datetime.now(timezone.utc).isoformat()
        updated["timestamp"] = now
        updated["updated_at"] = now
        updated.setdefault("created_at", current.get("timestamp"))
        if status == "acknowledged":
            updated["acknowledged_at"] = now
        if status == "closed":
            updated["closed_at"] = now
        self.store.store(updated)
        return AlertV1.from_mapping(updated)

    def search(self, *, hostname=None, severity=None, status=None, priority=None):
        if status is not None and status not in VALID_STATUSES:
            raise QueryError(f"invalid alert status filter: {status}")
        if priority is not None and priority not in VALID_PRIORITIES:
            raise QueryError(f"invalid alert priority filter: {priority}")
        current = self._latest().values()
        alerts = [
            AlertV1.from_mapping(item) for item in current
            if (hostname is None or item.get("hostname") == hostname)
            and (severity is None or item.get("severity") == severity)
            and (status is None or item.get("status") == status)
            and (priority is None or AlertV1.from_mapping(item).priority == priority)
        ]
        return sorted(alerts, key=lambda item: (item.priority, item.created_at or item.timestamp))
