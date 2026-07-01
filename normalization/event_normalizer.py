


class EventNormalizer :

    def normalize(self, event) :

        normalized_event = {

        "host": event.get("hostname"),
        "event_id": event.get("event_id"),
        "process_name": event.get("process_name")

        }

        return normalized_event
