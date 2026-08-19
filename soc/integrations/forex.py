"""Minimal translation boundary for FOREX-produced events."""

import hashlib
import re
from datetime import datetime, timezone

from reporting.report_exporter import ReportExporter
from soc.models import SOCResponseV1


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,121}$")


class FOREXAdapter:
    """Translate a FOREX mapping without hiding the public SOCService API."""

    def adapt(self, forex_event):
        if not isinstance(forex_event, dict):
            raise TypeError("FOREX event must be a mapping")
        event = dict(forex_event)
        event.setdefault("host", event.get("hostname") or event.get("terminal_id"))
        event.setdefault("event_type", event.get("type") or "forex_activity")
        event.setdefault("source", "forex")
        event.setdefault("severity", "low")
        forex_id = event.get("forex_event_id")
        if not event.get("event_uid") and forex_id is not None:
            candidate = str(forex_id)
            if SAFE_ID.fullmatch(candidate):
                event["event_uid"] = "forex:" + candidate
            else:
                digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:24]
                event["event_uid"] = "forex:" + digest
        provenance = dict(event.get("provenance") or {})
        provenance.setdefault("producer", "FOREX")
        event["provenance"] = provenance
        return event

    def ingest(self, service, forex_event):
        return service.ingest_event(self.adapt(forex_event))


class FOREXWorkflow:
    """Convenient FOREX workflows composed exclusively from public SOC calls."""

    REPORT_VERSION = "1.0"

    def __init__(self, service, adapter=None, exporter=None):
        self.service = service
        self.adapter = adapter or FOREXAdapter()
        self.exporter = exporter or ReportExporter()

    def ingest_and_assess(self, forex_event):
        ingestion = self.adapter.ingest(self.service, forex_event)
        hostname = ingestion.data["event"]["host"]
        host = self.service.get_host_detail(hostname)
        detections = self.service.analyze_host(hostname)
        alerts = self.service.create_alerts(hostname)
        summary = self.service.operational_summary(hostname=hostname)
        return SOCResponseV1(data={
            "ingestion": ingestion.data,
            "host": host.data["host"],
            "detections": detections.data["detections"],
            "alerts": alerts.data["alerts"],
            "summary": summary.data["summary"],
        }, metadata={"hostname": hostname, **ingestion.metadata})

    def get_terminal_context(self, terminal_id, recent_limit=10):
        host = self.service.get_host_detail(terminal_id, recent_limit=recent_limit)
        detail = host.data["host"]
        hostname = detail.hostname if detail is not None else terminal_id
        detections = self.service.analyze_host(hostname)
        alerts = self.service.search_alerts(hostname=hostname, status="open")
        summary = self.service.operational_summary(hostname=hostname)
        return SOCResponseV1(data={
            "host": detail,
            "recent_events": list(detail.recent_activity) if detail is not None else [],
            "detections": detections.data["detections"],
            "alerts": alerts.data["alerts"],
            "summary": summary.data["summary"],
        }, metadata={"terminal_id": terminal_id, "hostname": hostname, "found": detail is not None})

    def security_posture(self, terminal_id=None):
        """Return a compact posture using exclusively public SOCService calls."""
        center_response = self.service.command_center(hostname=terminal_id, limit=5)
        center = center_response.data["command_center"]
        if terminal_id is not None:
            risk = self.service.get_host_risk(terminal_id).data["risk"]
        else:
            risk = center["top_risk_hosts"][0] if center["top_risk_hosts"] else {
                "hostname": None, "known_host": False, "score": 0, "level": "low"
            }
        queue = center["attention_queue"]
        urgent_alerts = queue["totals_by_priority"].get("P1", 0) + queue[
            "totals_by_priority"
        ].get("P2", 0)
        open_incidents = self.service.list_incidents(hostname=terminal_id).data["incidents"]
        open_incidents = [item for item in open_incidents if item.status != "closed"]

        risk_level = risk.level if hasattr(risk, "level") else risk.get("level", "low")
        risk_score = risk.score if hasattr(risk, "score") else risk.get("score", 0)
        risk_hostname = (
            risk.hostname if hasattr(risk, "hostname") else risk.get("hostname")
        )
        if center_response.status == "degraded" or center["overall_state"] == "degraded":
            state = "degraded"
        elif risk_level in {"high", "critical"} or urgent_alerts:
            state = "high_risk"
        elif center["attention_required"]:
            state = "attention"
        else:
            state = "clear"
        if center["recommendations"]:
            next_step = center["recommendations"][0]["recommended_next_step"]
        elif queue["entries"]:
            next_step = "Review the highest-ranked alert in the attention queue."
        elif state == "degraded":
            next_step = "Review SOC health and storage integrity before relying on posture data."
        else:
            next_step = "Continue normal monitoring."
        return SOCResponseV1(data={
            "posture": {
                "state": state,
                "attention_required": state != "clear",
                "risk": {
                    "hostname": risk_hostname, "score": risk_score, "level": risk_level,
                    "heuristic": True,
                },
                "urgent_alerts": urgent_alerts,
                "open_incidents": len(open_incidents),
                "references": {
                    "alert_ids": [item["alert"].alert_id for item in queue["entries"][:5]],
                    "incident_ids": [item.incident_id for item in open_incidents[:5]],
                },
                "top_reasons": list(center["reasons"][:5]),
                "recommended_next_step": next_step,
                "generated_at": center["generated_at"],
            }
        }, metadata={"terminal_id": terminal_id, "scope": "terminal" if terminal_id else "global"})

    def export_terminal_report(self, terminal_id, destination, *, recent_limit=10,
                               overwrite=False, generated_at=None):
        context = self.get_terminal_context(terminal_id, recent_limit=recent_limit)
        primitive = context.to_dict()["data"]
        host = primitive["host"]
        generated_at = generated_at or datetime.now(timezone.utc).isoformat()
        report = {
            "report_version": self.REPORT_VERSION,
            "generated_at": generated_at,
            "parameters": {"terminal_id": terminal_id, "recent_limit": recent_limit},
            "identity": {
                "terminal_id": terminal_id,
                "hostname": host.get("hostname") if host else None,
                "observed_names": host.get("observed_names", []) if host else [],
            },
            "statistics": host,
            "recent_events": primitive["recent_events"],
            "detections": primitive["detections"],
            "alerts": primitive["alerts"],
            "summary": primitive["summary"],
        }
        exported = self.exporter.write(destination, report, overwrite=overwrite)
        return SOCResponseV1(
            data={"report": report, "export": exported},
            metadata={"terminal_id": terminal_id, "found": context.metadata["found"]},
        )
