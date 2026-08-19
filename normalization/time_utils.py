"""Shared timestamp parsing and ordering helpers."""

from datetime import datetime, timezone


UTC_MIN = datetime.min.replace(tzinfo=timezone.utc)


def parse_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def event_time_key(event):
    parsed = parse_timestamp(event.get("timestamp"))
    return (parsed is not None, parsed or UTC_MIN)
