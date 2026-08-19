from normalization.time_utils import event_time_key
from storage.event_reader import EventReader


class HostTimeline:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()

    @staticmethod
    def _sort_key(event):
        return event_time_key(event)

    def build(self, hostname, newest_first=False, limit=None):

        events = list(self.reader.find_by_host(hostname))
        events.sort(key=self._sort_key, reverse=newest_first)

        if limit is not None:

            return events[:max(limit, 0)]

        return events
