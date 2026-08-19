


from normalization.event_contract import OPTIONAL_FIELDS, utc_timestamp, validate_event


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
        validate_event(normalized_event)
        return normalized_event
