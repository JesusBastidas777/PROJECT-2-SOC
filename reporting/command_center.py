"""Read-only operational command center composed from existing capabilities."""

from datetime import datetime, timezone

from normalization.time_utils import parse_timestamp
from soc.errors import QueryError


class CommandCenter:
    def __init__(self, status_service, integrity_service, attention_queue,
                 inventory, risk_service, incident_service, guidance,
                 operational_summary, now=None):
        self.status_service = status_service
        self.integrity_service = integrity_service
        self.attention_queue = attention_queue
        self.inventory = inventory
        self.risk_service = risk_service
        self.incident_service = incident_service
        self.guidance = guidance
        self.operational_summary = operational_summary
        self._now = now or (lambda: datetime.now(timezone.utc))

    def build(self, *, hostname=None, limit=5, stale_hours=24):
        if not isinstance(limit, int) or limit <= 0:
            raise QueryError("limit must be a positive integer")
        if not isinstance(stale_hours, (int, float)) or stale_hours <= 0:
            raise QueryError("stale_hours must be positive")
        health = self.status_service.health()
        integrity = self.integrity_service.audit()
        queue = self.attention_queue.build(hostname=hostname, limit=limit)
        hosts = [self.inventory.get(hostname)] if hostname else self.inventory.list()
        risks = [self.risk_service.calculate(item["hostname"]) for item in hosts if item]
        risks.sort(key=lambda item: (-item["score"], item["hostname"].casefold()))
        incidents = [
            item for item in self.incident_service.list(hostname=hostname)
            if item.status != "closed"
        ]
        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        stale = [
            item for item in incidents
            if parse_timestamp(item.updated_at)
            and (now - parse_timestamp(item.updated_at)).total_seconds() >= stale_hours * 3600
        ]
        recommendations = []
        for incident in incidents[:limit]:
            advisory = self.guidance.recommend(incident_id=incident.incident_id)
            validate = advisory["recommendations"]["validate"][0]
            recommendations.append({
                "incident_id": incident.incident_id,
                "recommended_next_step": validate["recommendation"],
                "reason": validate["reason"], "advisory_only": True,
            })
        summary = self.operational_summary.build(hostname=hostname, limit=limit)

        reasons = []
        if health.state != "healthy":
            reasons.append("SOC health is degraded")
        if integrity["invalid"]:
            reasons.append("Event storage contains invalid records")
        if queue["attention_required"]:
            reasons.append(f"{queue['total']} alert(s) require attention")
        if incidents:
            reasons.append(f"{len(incidents)} incident(s) remain open")
        if stale:
            reasons.append(f"{len(stale)} incident(s) have not been updated recently")
        if risks and risks[0]["level"] in {"high", "critical"}:
            reasons.append(f"Host {risks[0]['hostname']} has {risks[0]['level']} operational risk")
        if health.state != "healthy" or integrity["invalid"]:
            overall_state = "degraded"
        elif risks and risks[0]["level"] == "critical":
            overall_state = "high_risk"
        elif queue["attention_required"] or incidents:
            overall_state = "attention"
        else:
            overall_state = "clear"
        return {
            "overall_state": overall_state,
            "attention_required": overall_state != "clear",
            "reasons": reasons,
            "health": health,
            "integrity": integrity,
            "attention_queue": queue,
            "top_risk_hosts": risks[:limit],
            "open_incidents": incidents[:limit],
            "stale_incidents": stale[:limit],
            "recommendations": recommendations,
            "operational_summary": summary,
            "generated_at": now.isoformat(),
        }
