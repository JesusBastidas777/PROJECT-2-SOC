"""Append-only incident state built from explicitly selected alerts."""

import hashlib
from datetime import datetime, timezone

from soc.errors import IncidentTransitionError, QueryError
from soc.models import IncidentV1
from storage.event_reader import EventReader
from storage.event_store import EventStore


VALID_STATUSES = {"open", "investigating", "contained", "closed"}
TRANSITIONS = {
    "open": {"investigating", "contained", "closed"},
    "investigating": {"contained", "closed"},
    "contained": {"closed"},
    "closed": set(),
}
PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}


class IncidentService:
    """Keep one active incident per alert; closed alerts may be reused explicitly."""

    def __init__(self, log_file, alert_service, alert_grouping, lock_timeout=5.0,
                 now=None):
        self.reader = EventReader(log_file)
        self.store = EventStore(log_file, lock_timeout=lock_timeout)
        self.alert_service = alert_service
        self.alert_grouping = alert_grouping
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _latest(self):
        return {
            item["incident_id"]: item for item in self.reader.read_events()
            if item.get("incident_id")
        }

    @staticmethod
    def _identity(alert_ids):
        payload = "\n".join(sorted(alert_ids))
        return "inc-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    def create(self, *, alert_ids=None, group_id=None, title=None, summary=None):
        if (alert_ids is None) == (group_id is None):
            raise QueryError("pass exactly one of alert_ids or group_id")
        if group_id is not None:
            group = self.alert_grouping.get(group_id)
            if group is None:
                raise QueryError(f"unknown correlation group: {group_id}")
            alert_ids = group["alert_ids"]
        alert_ids = list(alert_ids)
        if not alert_ids:
            raise QueryError("at least one alert_id is required")
        if len(alert_ids) != len(set(alert_ids)):
            raise QueryError("duplicate alert_id values are not allowed")

        current_alerts = {item.alert_id: item for item in self.alert_service.search()}
        missing = sorted(set(alert_ids) - set(current_alerts))
        if missing:
            raise QueryError("unknown alerts", details={"alert_ids": missing})
        alert_ids = sorted(alert_ids)
        incident_id = self._identity(alert_ids)
        existing = self._latest()
        if incident_id in existing:
            return IncidentV1.from_mapping(existing[incident_id])
        conflicts = sorted({
            alert_id for item in existing.values() if item.get("status") != "closed"
            for alert_id in item.get("alert_ids", []) if alert_id in alert_ids
        })
        if conflicts:
            raise QueryError(
                "alerts already belong to an active incident",
                details={"alert_ids": conflicts},
            )

        alerts = [current_alerts[alert_id] for alert_id in alert_ids]
        priority = min(
            (item.priority for item in alerts),
            key=lambda value: PRIORITY_ORDER.get(value, 99),
        )
        hosts = sorted({item.hostname for item in alerts}, key=str.casefold)
        now = self._now().isoformat()
        incident = IncidentV1(
            incident_id=incident_id,
            title=title or f"{priority} incident on {', '.join(hosts)}",
            status="open", priority=priority,
            severity={"P1": "critical", "P2": "high", "P3": "medium", "P4": "low"}[priority],
            hosts=hosts, alert_ids=alert_ids, created_at=now, updated_at=now,
            summary=summary or f"Created from {len(alert_ids)} selected alert(s).",
        )
        self.store.store(incident.__dict__)
        return incident

    def get(self, incident_id):
        item = self._latest().get(incident_id)
        return IncidentV1.from_mapping(item) if item else None

    def list(self, *, status=None, hostname=None):
        if status is not None and status not in VALID_STATUSES:
            raise QueryError(f"invalid incident status filter: {status}")
        items = [IncidentV1.from_mapping(item) for item in self._latest().values()]
        items = [
            item for item in items
            if (status is None or item.status == status)
            and (hostname is None or hostname.casefold() in {host.casefold() for host in item.hosts})
        ]
        return sorted(items, key=lambda item: (
            PRIORITY_ORDER.get(item.priority, 99), item.created_at, item.incident_id
        ))

    def transition(self, incident_id, status):
        if status not in VALID_STATUSES:
            raise IncidentTransitionError(f"invalid incident status: {status}")
        current = self._latest().get(incident_id)
        if current is None:
            raise QueryError(f"unknown incident: {incident_id}")
        if status == current["status"]:
            return IncidentV1.from_mapping(current)
        if status not in TRANSITIONS[current["status"]]:
            raise IncidentTransitionError(
                f"cannot transition incident from {current['status']} to {status}"
            )
        updated = dict(current)
        updated["status"] = status
        updated["updated_at"] = self._now().isoformat()
        self.store.store(updated)
        return IncidentV1.from_mapping(updated)
