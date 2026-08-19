"""Explainable, deterministic host risk heuristic."""

from collections import Counter
from datetime import datetime, timezone

from inventory.host_catalog import host_key
from normalization.time_utils import parse_timestamp


PRIORITY_POINTS = {"P1": 40, "P2": 25, "P3": 12, "P4": 4}
SEVERITY_POINTS = {"critical": 15, "high": 10, "medium": 5, "low": 1}


class HostRiskService:
    def __init__(self, inventory, alert_service, detection_engine, reader, now=None):
        self.inventory = inventory
        self.alert_service = alert_service
        self.detection_engine = detection_engine
        self.reader = reader
        self._now = now or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _level(score):
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 20:
            return "moderate"
        return "low"

    def calculate(self, hostname):
        record = self.inventory.get(hostname)
        calculated_at = self._now()
        if calculated_at.tzinfo is None:
            calculated_at = calculated_at.replace(tzinfo=timezone.utc)
        if record is None:
            return {
                "hostname": hostname, "known_host": False, "score": 0,
                "level": "unknown", "factors": [],
                "calculated_at": calculated_at.isoformat(),
                "explanation": "No stored evidence exists for this host.",
                "heuristic": True,
            }

        key = host_key(hostname)
        alerts = [
            alert for alert in self.alert_service.search(status="open")
            if host_key(alert.hostname) == key
        ]
        priority_counts = Counter(alert.priority for alert in alerts)
        factors = []
        points = 0
        for priority in ("P1", "P2", "P3", "P4"):
            count = priority_counts.get(priority, 0)
            if count:
                contribution = min(PRIORITY_POINTS[priority] * count, PRIORITY_POINTS[priority] * 2)
                points += contribution
                factors.append({
                    "factor": "open_alerts", "value": {"priority": priority, "count": count},
                    "points": contribution,
                })

        detections = self.detection_engine.analyze_host(record["hostname"])
        unique = {}
        for detection in detections:
            identity = detection.get("detection_id") or (
                detection.get("rule_name"),
                detection.get("event_uid") or (detection.get("event") or {}).get("event_uid"),
            )
            unique[identity] = detection
        if unique:
            contribution = min(len(unique) * 4, 20)
            points += contribution
            factors.append({
                "factor": "unique_detections", "value": len(unique), "points": contribution,
            })

        severities = [
            str((item.get("event") or {}).get("severity") or item.get("severity") or "").lower()
            for item in unique.values()
        ]
        max_severity = max(severities, key=lambda item: SEVERITY_POINTS.get(item, 0), default="unknown")
        severity_points = SEVERITY_POINTS.get(max_severity, 0)
        if severity_points:
            points += severity_points
            factors.append({
                "factor": "maximum_severity", "value": max_severity,
                "points": severity_points,
            })

        relevant_recent = set()
        for item in unique.values():
            event = item.get("event") or {}
            timestamp = parse_timestamp(event.get("timestamp"))
            if timestamp and 0 <= (calculated_at - timestamp).total_seconds() <= 86400:
                relevant_recent.add(event.get("event_uid") or item.get("detection_id"))
        if relevant_recent:
            contribution = min(len(relevant_recent) * 3, 10)
            points += contribution
            factors.append({
                "factor": "recent_relevant_activity_24h",
                "value": len(relevant_recent), "points": contribution,
            })

        score = min(points, 100)
        return {
            "hostname": record["hostname"], "known_host": True, "score": score,
            "level": self._level(score), "factors": factors,
            "calculated_at": calculated_at.isoformat(),
            "explanation": (
                "Operational heuristic derived from current alerts and local detections; "
                "it is not a probability of compromise."
            ),
            "heuristic": True,
        }
