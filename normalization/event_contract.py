"""Canonical SOC event contract and validation helpers."""

from datetime import datetime, timezone


REQUIRED_FIELDS = ("timestamp", "host", "event_type", "source", "severity")
OPTIONAL_FIELDS = (
    "event_id", "process_name", "pid", "parent_process", "user",
    "src_ip", "dst_ip", "src_port", "dst_port", "protocol",
    "file_name", "file_path", "file_hash",
    "rule_name", "mitre_technique", "confidence",
)


class EventValidationError(ValueError):
    """Raised when an event cannot satisfy the canonical contract."""


def utc_timestamp(value):
    """Return an ISO-8601 timestamp normalized to UTC."""
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not isinstance(value, str):
        raise EventValidationError("timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventValidationError("timestamp must be a valid ISO-8601 value") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def validate_event(event, *, allow_legacy=False):
    if not isinstance(event, dict):
        raise EventValidationError("event must be a mapping")
    missing = [field for field in REQUIRED_FIELDS if event.get(field) in (None, "")]
    if missing and not allow_legacy:
        raise EventValidationError("missing required event fields: " + ", ".join(missing))
    if event.get("timestamp") is not None:
        utc_timestamp(event["timestamp"])
    return event
