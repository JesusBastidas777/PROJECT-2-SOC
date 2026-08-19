from datetime import datetime, timezone

from storage.event_reader import EventReader


class HostTimeline:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()

    @staticmethod
    def _sort_key(event):

        timestamp = event.get("timestamp")

        if isinstance(timestamp, str):

            try:

                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                if parsed.tzinfo is None:

                    parsed = parsed.replace(tzinfo=timezone.utc)

                return True, parsed

            except ValueError:

                pass

        return False, datetime.min.replace(tzinfo=timezone.utc)

    def build(self, hostname, newest_first=False, limit=None):

        events = list(self.reader.find_by_host(hostname))
        events.sort(key=self._sort_key, reverse=newest_first)

        if limit is not None:

            return events[:max(limit, 0)]

        return events
