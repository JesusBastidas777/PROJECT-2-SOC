from datetime import datetime, timezone

from storage.event_reader import EventReader


class EventSearch:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()

    @staticmethod
    def _parse_timestamp(value):

        if not isinstance(value, str):

            return None

        try:

            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))

            if timestamp.tzinfo is None:

                timestamp = timestamp.replace(tzinfo=timezone.utc)

            return timestamp

        except ValueError:

            return None

    def search(
        self,
        hostname=None,
        process_name=None,
        user=None,
        event_id=None,
        source=None,
        severity=None,
        start_timestamp=None,
        end_timestamp=None,
        limit=None,
    ):

        if limit is not None and limit <= 0:

            return []

        if hostname is not None:

            events = self.reader.find_by_host(hostname)

        elif process_name is not None:

            events = self.reader.find_by_process(process_name)

        else:

            events = self.reader.read_events()

        start = self._parse_timestamp(start_timestamp)
        end = self._parse_timestamp(end_timestamp)
        matches = []

        for event in events:

            if process_name is not None and event.get("process_name") != process_name:

                continue

            if user is not None and event.get("user") != user:

                continue

            if event_id is not None and event.get("event_id") != event_id:

                continue

            if source is not None and event.get("source") != source:

                continue

            if severity is not None and event.get("severity") != severity:

                continue

            if start is not None or end is not None:

                event_time = self._parse_timestamp(event.get("timestamp"))

                if event_time is None:

                    continue

                if start is not None and event_time < start:

                    continue

                if end is not None and event_time > end:

                    continue

            matches.append(event)

            if limit is not None and len(matches) >= limit:

                break

        return matches
