"""Compact operational summaries for programmatic consumers."""

from collections import Counter

from inventory.host_catalog import host_key
from normalization.time_utils import parse_timestamp
from soc.errors import QueryError


class OperationalSummary:
    def __init__(self, reader, alert_service, detection_engine, status_service):
        self.reader = reader
        self.alert_service = alert_service
        self.detection_engine = detection_engine
        self.status_service = status_service

    def build(self, *, start_timestamp=None, end_timestamp=None, hostname=None, limit=5):
        if not isinstance(limit, int) or limit <= 0:
            raise QueryError("limit must be a positive integer")
        start = parse_timestamp(start_timestamp)
        end = parse_timestamp(end_timestamp)
        if start_timestamp is not None and start is None:
            raise QueryError("start_timestamp must be a valid ISO-8601 value")
        if end_timestamp is not None and end is None:
            raise QueryError("end_timestamp must be a valid ISO-8601 value")
        if start and end and start > end:
            raise QueryError("start_timestamp must not be after end_timestamp")

        events = []
        for event in self.reader.read_events():
            if hostname is not None and host_key(event.get("host")) != host_key(hostname):
                continue
            event_time = parse_timestamp(event.get("timestamp"))
            if start and (event_time is None or event_time < start):
                continue
            if end and (event_time is None or event_time > end):
                continue
            events.append(event)

        alerts = []
        for alert in self.alert_service.search():
            if hostname is not None and host_key(alert.hostname) != host_key(hostname):
                continue
            alert_time = parse_timestamp(alert.created_at or alert.timestamp)
            if start and (alert_time is None or alert_time < start):
                continue
            if end and (alert_time is None or alert_time > end):
                continue
            alerts.append(alert)

        detections = self.detection_engine.analyze_events(events)
        host_counts = Counter(event.get("host") for event in events if event.get("host"))
        rule_counts = Counter(item.get("rule_name") for item in detections)
        timestamped = [
            (parse_timestamp(event.get("timestamp")), event.get("timestamp")) for event in events
        ]
        timestamped = [item for item in timestamped if item[0] is not None]

        return {
            "window": {"start_timestamp": start_timestamp, "end_timestamp": end_timestamp},
            "hostname": hostname,
            "total_events": len(events),
            "events_by_severity": dict(sorted(Counter(
                str(event.get("severity") or "unknown").lower() for event in events
            ).items())),
            "events_by_source": dict(sorted(Counter(
                str(event.get("source") or "unknown") for event in events
            ).items())),
            "events_by_type": dict(sorted(Counter(
                str(event.get("event_type") or "unknown") for event in events
            ).items())),
            "active_hosts": len(host_counts),
            "top_hosts": [
                {"hostname": name, "count": count}
                for name, count in sorted(host_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
            ],
            "alerts_by_priority": dict(sorted(Counter(a.priority for a in alerts).items())),
            "alerts_by_status": dict(sorted(Counter(a.status for a in alerts).items())),
            "top_detections": [
                {"rule_name": name, "count": count}
                for name, count in sorted(rule_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
            ],
            "duplicates_rejected": self.status_service.duplicates_rejected,
            "invalid_records": self.reader.invalid_line_count,
            "last_event": max(timestamped)[1] if timestamped else None,
            "attention_required": any(a.status == "open" for a in alerts)
            or self.reader.invalid_line_count > 0,
        }
