"""Deterministic, read-only triage view over current alerts."""

from collections import Counter
from datetime import datetime, timezone

from normalization.time_utils import parse_timestamp
from soc.errors import QueryError


PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
STATUS_ORDER = {"open": 0, "acknowledged": 1}


class AttentionQueue:
    def __init__(self, alert_service, now=None):
        self.alert_service = alert_service
        self._now = now or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _age_band(seconds):
        if seconds < 3600:
            return "new"
        if seconds < 86400:
            return "aging"
        return "stale"

    def build(self, *, hostname=None, priority=None, limit=20,
              include_acknowledged=False):
        if not isinstance(limit, int) or limit <= 0:
            raise QueryError("limit must be a positive integer")
        if priority is not None and priority not in PRIORITY_ORDER:
            raise QueryError(f"invalid alert priority filter: {priority}")

        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        statuses = ("open", "acknowledged") if include_acknowledged else ("open",)
        alerts = []
        for status in statuses:
            alerts.extend(self.alert_service.search(
                hostname=hostname, priority=priority, status=status
            ))

        entries = []
        for alert in alerts:
            created = parse_timestamp(alert.created_at or alert.timestamp)
            age_seconds = max(0, int((now - created).total_seconds())) if created else None
            band = self._age_band(age_seconds) if age_seconds is not None else "unknown"
            reason = f"{alert.priority} {alert.status} alert"
            if band == "stale":
                reason += " awaiting attention for at least one day"
            elif band == "aging":
                reason += " awaiting attention for at least one hour"
            entries.append({
                "alert": alert,
                "attention_reason": reason,
                "age_seconds": age_seconds,
                "age_band": band,
            })

        entries.sort(key=lambda item: (
            PRIORITY_ORDER.get(item["alert"].priority, 99),
            STATUS_ORDER.get(item["alert"].status, 99),
            parse_timestamp(item["alert"].created_at or item["alert"].timestamp)
            or datetime.max.replace(tzinfo=timezone.utc),
            item["alert"].alert_id,
        ))
        priority_totals = Counter(item["alert"].priority for item in entries)
        status_totals = Counter(item["alert"].status for item in entries)
        oldest = min(
            (item["alert"].created_at or item["alert"].timestamp for item in entries),
            key=lambda value: parse_timestamp(value) or datetime.max.replace(tzinfo=timezone.utc),
            default=None,
        )
        total = len(entries)
        return {
            "entries": entries[:limit],
            "totals_by_priority": dict(sorted(priority_totals.items())),
            "totals_by_status": dict(sorted(status_totals.items())),
            "oldest_unhandled_at": oldest,
            "attention_required": total > 0,
            "total": total,
            "truncated": total > limit,
        }
