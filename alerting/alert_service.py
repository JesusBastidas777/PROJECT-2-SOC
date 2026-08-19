"""Persist detections as deduplicated, actionable alerts."""

import hashlib
import json
from datetime import datetime, timezone

from soc.errors import AlertTransitionError, QueryError
from soc.models import AlertV1, DetectionV1
from storage.event_reader import EventReader
from storage.event_store import EventStore


VALID_STATUSES = {"open", "acknowledged", "closed"}
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
        alert = AlertV1(
            alert_id=alert_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="open",
            hostname=event.get("host") or event.get("hostname") or "unknown",
            severity=str(detection.get("severity") or "unknown").lower(),
            rule_name=detection.get("rule_name") or "unknown",
            reason=detection.get("reason") or "",
            event=event,
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
        updated["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.store.store(updated)
        return AlertV1.from_mapping(updated)

    def search(self, *, hostname=None, severity=None, status=None):
        if status is not None and status not in VALID_STATUSES:
            raise QueryError(f"invalid alert status filter: {status}")
        alerts = self._latest().values()
        return [
            AlertV1.from_mapping(item) for item in alerts
            if (hostname is None or item.get("hostname") == hostname)
            and (severity is None or item.get("severity") == severity)
            and (status is None or item.get("status") == status)
        ]
