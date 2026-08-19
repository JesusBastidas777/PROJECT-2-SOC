import hashlib
import json

from normalization.event_contract import (
    EVENT_SCHEMA_VERSION, OPTIONAL_FIELDS, utc_timestamp, validate_event,
)


class EventNormalizer :

    @staticmethod
    def _normalize_timestamp(timestamp):
        return utc_timestamp(timestamp)

    def normalize(self, event) :

        if not isinstance(event, dict):
            validate_event(event)
        normalized_event = dict(event)
        normalized_event.pop("hostname", None)
        normalized_event["host"] = event.get("host", event.get("hostname"))
        normalized_event["timestamp"] = self._normalize_timestamp(event.get("timestamp"))
        for field in OPTIONAL_FIELDS:
            normalized_event.setdefault(field, None)
        normalized_event["event_schema_version"] = (
            event.get("event_schema_version") or EVENT_SCHEMA_VERSION
        )
        normalized_event["ingested_at"] = utc_timestamp(event.get("ingested_at"))
        normalized_event["provenance"] = dict(event.get("provenance") or {})
        normalized_event["provenance"].setdefault("source", normalized_event["source"])
        if normalized_event["event_uid"] is None:
            identity = {
                key: value for key, value in normalized_event.items()
                if key not in {"event_uid", "ingested_at", "provenance"}
            }
            payload = json.dumps(
                identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            normalized_event["event_uid"] = "evt-" + hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest()[:24]
        validate_event(normalized_event)
        return normalized_event
