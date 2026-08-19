"""Generate safe descriptive guidance from current incident or alert evidence."""

from response.playbooks import GENERIC_PLAYBOOK, PLAYBOOKS
from soc.errors import QueryError


SECTIONS = ("validate", "collect_evidence", "contain", "recover", "escalate")


class ResponseGuidance:
    def __init__(self, incident_service, alert_service):
        self.incident_service = incident_service
        self.alert_service = alert_service

    def recommend(self, *, incident_id=None, alert_id=None):
        if (incident_id is None) == (alert_id is None):
            raise QueryError("pass exactly one of incident_id or alert_id")
        alerts = {item.alert_id: item for item in self.alert_service.search()}
        if incident_id is not None:
            incident = self.incident_service.get(incident_id)
            if incident is None:
                raise QueryError(f"unknown incident: {incident_id}")
            selected = [alerts[item] for item in incident.alert_ids if item in alerts]
            subject = {"incident_id": incident_id, "alert_ids": list(incident.alert_ids)}
        else:
            if alert_id not in alerts:
                raise QueryError(f"unknown alert: {alert_id}")
            selected = [alerts[alert_id]]
            subject = {"alert_id": alert_id}

        signals = sorted({
            signal for alert in selected for signal in (
                alert.rule_name, alert.priority, alert.hostname,
                alert.event.get("process_name"), alert.event.get("parent_process"),
            ) if signal
        })
        rules = sorted({alert.rule_name for alert in selected})
        recommendations = {}
        for section in SECTIONS:
            recommendation, risk = GENERIC_PLAYBOOK[section]
            matching = [PLAYBOOKS[rule][section] for rule in rules
                        if rule in PLAYBOOKS and section in PLAYBOOKS[rule]]
            if matching:
                recommendation, risk = matching[0]
            recommendations[section] = [{
                "recommendation": recommendation,
                "reason": f"Based on local signals: {', '.join(rules) or 'unknown rule'}.",
                "precondition_or_risk": risk,
                "signals": signals,
            }]
        return {
            "subject": subject, "advisory_only": True,
            "recommendations": recommendations,
        }
