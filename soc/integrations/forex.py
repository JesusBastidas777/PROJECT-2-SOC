"""Minimal translation boundary for FOREX-produced events."""

import hashlib
import re


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
