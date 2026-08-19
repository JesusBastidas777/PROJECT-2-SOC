"""Unified host detail assembled from one event snapshot and current alerts."""

from collections import Counter

from inventory.host_catalog import host_key
from normalization.time_utils import event_time_key, parse_timestamp


class HostDetail:
    def __init__(self, reader, alert_service, host_catalog):
        self.reader = reader
        self.alert_service = alert_service
        self.host_catalog = host_catalog

    @staticmethod
    def _rank(counter):
        return [
            {"name": name, "count": count}
            for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold()))
        ]

    def build(self, hostname, recent_limit=10):
        if not isinstance(recent_limit, int) or recent_limit <= 0:
            raise ValueError("recent_limit must be a positive integer")
        key = host_key(hostname)
        events = [
            event for event in self.reader.read_events()
            if host_key(event.get("host")) == key
        ]
        if not events:
            return None

        record = self.host_catalog.get(hostname)
        timestamps = [
            (parse_timestamp(event.get("timestamp")), event.get("timestamp")) for event in events
        ]
        timestamps = [item for item in timestamps if item[0] is not None]
        processes = Counter(
            str(event["process_name"]) for event in events if event.get("process_name")
        )
        users = Counter(str(event["user"]) for event in events if event.get("user"))
        events.sort(key=event_time_key, reverse=True)
        alerts = [
            alert for alert in self.alert_service.search(status="open")
            if host_key(alert.hostname) == key
        ]
        return {
            "hostname": record["hostname"],
            "observed_names": list(record["observed_names"]),
            "first_seen": min(timestamps)[1] if timestamps else None,
            "last_seen": max(timestamps)[1] if timestamps else None,
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
            "frequent_processes": self._rank(processes),
            "frequent_users": self._rank(users),
            "open_alerts_by_priority": dict(sorted(Counter(
                alert.priority for alert in alerts
            ).items())),
            "recent_activity": events[:recent_limit],
        }
