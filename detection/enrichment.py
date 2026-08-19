"""Stable, local context for rule detections without external intelligence."""

import hashlib
import json


RULE_CONTEXT = {
    "sensitive_process_execution": ("credential_or_admin_tool", "high"),
    "office_spawned_command_interpreter": ("suspicious_process_chain", "high"),
    "source_reported_high_severity": ("source_severity", "medium"),
}


def _identity(rule_name, event):
    identity = {
        "rule_name": rule_name,
        "event_uid": event.get("event_uid"),
        "host": event.get("host") or event.get("hostname"),
        "timestamp": event.get("timestamp"),
        "process_name": event.get("process_name"),
        "parent_process": event.get("parent_process"),
        "event_id": event.get("event_id"),
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return "det-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def enrich_detection(detection):
    """Return an enriched detection while retaining the original event reference."""
    enriched = dict(detection)
    event = detection.get("event") or {}
    rule_name = detection.get("rule_name") or "unknown"
    category, confidence = RULE_CONTEXT.get(rule_name, ("local_rule_match", "medium"))
    evidence = {
        key: event.get(key) for key in (
            "process_name", "parent_process", "user", "source", "severity"
        ) if event.get(key) is not None
    }
    enriched.update({
        "detection_id": _identity(rule_name, event),
        "category": category,
        "confidence": confidence,
        "evidence": evidence,
        "context": {
            "hostname": event.get("host") or event.get("hostname"),
            "rule_source": "local_process_rules",
            "matched_fields": sorted(evidence),
        },
        "event_uid": event.get("event_uid"),
    })
    enriched["event"] = event
    return enriched
