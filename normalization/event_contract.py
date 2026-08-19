"""Canonical SOC event contract and validation helpers."""

from datetime import datetime, timezone
import re

from soc.errors import ValidationError


REQUIRED_FIELDS = ("timestamp", "host", "event_type", "source", "severity")
OPTIONAL_FIELDS = (
    "event_id", "event_uid", "ingested_at", "event_schema_version", "provenance",
    "process_name", "pid", "parent_process", "user",
    "src_ip", "dst_ip", "src_port", "dst_port", "protocol",
    "file_name", "file_path", "file_hash",
    "rule_name", "mitre_technique", "confidence",
)
EVENT_SCHEMA_VERSION = "1.0"
EVENT_UID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class EventValidationError(ValidationError):
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
    if event.get("ingested_at") is not None:
        utc_timestamp(event["ingested_at"])
    event_uid = event.get("event_uid")
    if event_uid is not None and (
        not isinstance(event_uid, str) or EVENT_UID_PATTERN.fullmatch(event_uid) is None
    ):
        raise EventValidationError(
            "event_uid must be 1-128 safe identifier characters"
        )
    provenance = event.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        raise EventValidationError("provenance must be a mapping")
    return event
