


from datetime import datetime, timezone


class EventNormalizer :

    @staticmethod
    def _normalize_timestamp(timestamp):

        if isinstance(timestamp, str):

            try:

                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                return timestamp

            except ValueError:

                pass

        return datetime.now(timezone.utc).isoformat()

    def normalize(self, event) :

        normalized_event = {

        "host": event.get("hostname"),
        "event_id": event.get("event_id"),
        "process_name": event.get("process_name"),
        "timestamp": self._normalize_timestamp(event.get("timestamp"))

        }

        return normalized_event
