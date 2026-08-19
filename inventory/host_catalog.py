"""Derived host inventory backed by events and current alerts."""

from normalization.time_utils import parse_timestamp


SEVERITY_RANK = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def host_key(value):
    return value.strip().casefold() if isinstance(value, str) else None


class HostCatalog:
    def __init__(self, reader, alert_service):
        self.reader = reader
        self.alert_service = alert_service

    def list(self):
        grouped = {}
        for event in self.reader.read_events():
            observed = event.get("host")
            key = host_key(observed)
            if not key:
                continue
            item = grouped.setdefault(key, {
                "hostname": observed.strip(), "observed_names": [], "total_events": 0,
                "first_seen": None, "last_seen": None, "sources": [],
                "max_severity": "unknown", "open_alerts": 0,
                "_first_time": None, "_last_time": None,
            })
            name = observed.strip()
            if name not in item["observed_names"]:
                item["observed_names"].append(name)
            item["total_events"] += 1
            source = event.get("source")
            if source and source not in item["sources"]:
                item["sources"].append(source)
            severity = str(event.get("severity") or "unknown").lower()
            if SEVERITY_RANK.get(severity, 0) > SEVERITY_RANK.get(item["max_severity"], 0):
                item["max_severity"] = severity
            event_time = parse_timestamp(event.get("timestamp"))
            if event_time is not None:
                if item["_first_time"] is None or event_time < item["_first_time"]:
                    item["_first_time"], item["first_seen"] = event_time, event["timestamp"]
                if item["_last_time"] is None or event_time > item["_last_time"]:
                    item["_last_time"], item["last_seen"] = event_time, event["timestamp"]
        for alert in self.alert_service.search(status="open"):
            key = host_key(alert.hostname)
            if key in grouped:
                grouped[key]["open_alerts"] += 1
        results = []
        for item in grouped.values():
            item.pop("_first_time")
            item.pop("_last_time")
            item["observed_names"].sort(key=str.casefold)
            item["sources"].sort(key=str.casefold)
            results.append(item)
        return sorted(results, key=lambda item: item["hostname"].casefold())

    def get(self, hostname):
        key = host_key(hostname)
        return next((item for item in self.list() if host_key(item["hostname"]) == key), None)
