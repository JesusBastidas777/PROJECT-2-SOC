from normalization.time_utils import parse_timestamp
from storage.event_reader import EventReader
from soc.errors import QueryError


class EventSearch:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()

    @staticmethod
    def _parse_timestamp(value):
        return parse_timestamp(value)

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

        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            raise QueryError("limit must be a positive integer", details={"limit": limit})

        if hostname is not None:

            events = self.reader.find_by_host(hostname)

        elif process_name is not None:

            events = self.reader.find_by_process(process_name)

        else:

            events = self.reader.read_events()

        start = self._parse_timestamp(start_timestamp)
        end = self._parse_timestamp(end_timestamp)
        if start_timestamp is not None and start is None:
            raise QueryError("start_timestamp must be a valid ISO-8601 value")
        if end_timestamp is not None and end is None:
            raise QueryError("end_timestamp must be a valid ISO-8601 value")
        if start is not None and end is not None and start > end:
            raise QueryError("start_timestamp must not be after end_timestamp")
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
