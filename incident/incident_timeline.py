"""Evidence-linked timeline assembled from append-only SOC records."""

from normalization.time_utils import parse_timestamp
from soc.errors import QueryError


class IncidentTimeline:
    def __init__(self, incident_service, alert_service, event_reader):
        self.incident_service = incident_service
        self.alert_service = alert_service
        self.event_reader = event_reader

    @staticmethod
    def _entry(kind, timestamp, summary, source, incident_id, **references):
        return {
            "kind": kind, "timestamp": timestamp, "summary": summary,
            "source": source, "incident_id": incident_id, **references,
        }

    def build(self, incident_id, *, sort_order="oldest", limit=100):
        if sort_order not in {"oldest", "newest"}:
            raise QueryError("sort_order must be oldest or newest")
        if not isinstance(limit, int) or limit <= 0:
            raise QueryError("limit must be a positive integer")
        incident = self.incident_service.get(incident_id)
        if incident is None:
            raise QueryError(f"unknown incident: {incident_id}")

        entries = []
        incident_records = [
            item for item in self.incident_service.reader.read_events()
            if item.get("incident_id") == incident_id
        ]
        for index, record in enumerate(incident_records):
            kind = "incident_created" if index == 0 else "incident_transition"
            summary = (
                f"Incident created with status {record.get('status', 'unknown')}"
                if index == 0 else f"Incident status changed to {record.get('status', 'unknown')}"
            )
            entries.append(self._entry(
                kind, record.get("created_at") if index == 0 else record.get("updated_at"),
                summary, "incidents", incident_id,
            ))

        alert_records = [
            item for item in self.alert_service.reader.read_events()
            if item.get("alert_id") in incident.alert_ids
        ]
        seen_alerts = set()
        referenced_events = {}
        for record in alert_records:
            alert_id = record["alert_id"]
            created = alert_id not in seen_alerts
            seen_alerts.add(alert_id)
            event_uid = record.get("event_uid") or (record.get("event") or {}).get("event_uid")
            entries.append(self._entry(
                "alert_created" if created else "alert_transition",
                record.get("created_at") if created else record.get("updated_at") or record.get("timestamp"),
                (
                    f"Alert created with status {record.get('status', 'unknown')}"
                    if created else f"Alert status changed to {record.get('status', 'unknown')}"
                ),
                "alerts", incident_id, alert_id=alert_id, event_uid=event_uid,
            ))
            if event_uid:
                referenced_events.setdefault(event_uid, alert_id)

        for event_uid, alert_id in referenced_events.items():
            event = self.event_reader.find_by_uid(event_uid)
            if event is None:
                entries.append(self._entry(
                    "missing_evidence", incident.created_at,
                    f"Referenced event {event_uid} is unavailable", "events",
                    incident_id, event_uid=event_uid, alert_id=alert_id,
                ))
            else:
                entries.append(self._entry(
                    "event", event.get("timestamp"),
                    f"Referenced {event.get('event_type') or 'event'} observed on "
                    f"{event.get('host') or 'unknown host'}",
                    "events", incident_id, event_uid=event_uid, alert_id=alert_id,
                ))

        for alert_id in sorted(set(incident.alert_ids) - seen_alerts):
            entries.append(self._entry(
                "missing_evidence", incident.created_at,
                f"Referenced alert {alert_id} is unavailable", "alerts",
                incident_id, alert_id=alert_id,
            ))

        entries.sort(key=lambda item: (
            parse_timestamp(item.get("timestamp")) is None,
            parse_timestamp(item.get("timestamp")) or parse_timestamp("9999-12-31T00:00:00Z"),
            item["kind"], item.get("alert_id") or "", item.get("event_uid") or "",
        ), reverse=sort_order == "newest")
        total = len(entries)
        return {
            "incident_id": incident_id, "entries": entries[:limit],
            "sort_order": sort_order, "total": total, "truncated": total > limit,
        }
