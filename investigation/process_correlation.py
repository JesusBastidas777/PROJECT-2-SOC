from datetime import datetime, timezone

from storage.event_reader import EventReader


class ProcessCorrelation:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()

    @staticmethod
    def _parsed_timestamp(value):

        if not isinstance(value, str):

            return None

        try:

            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

            if parsed.tzinfo is None:

                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed

        except ValueError:

            return None

    def correlate(self, hostname=None):

        if hostname is None:

            events = self.reader.read_events()

        else:

            events = self.reader.find_by_host(hostname)

        grouped = {}

        for event in events:

            host = event.get("host")
            parent_process = event.get("parent_process")
            process_name = event.get("process_name")

            if host is None or parent_process is None or process_name is None:

                continue

            key = host, parent_process, process_name

            if key not in grouped:

                grouped[key] = {
                    "hostname": host,
                    "parent_process": parent_process,
                    "process_name": process_name,
                    "count": 0,
                    "first_seen": None,
                    "last_seen": None,
                    "_first_time": None,
                    "_last_time": None,
                }

            correlation = grouped[key]
            correlation["count"] += 1
            event_time = self._parsed_timestamp(event.get("timestamp"))

            if event_time is None:

                continue

            if correlation["_first_time"] is None or event_time < correlation["_first_time"]:

                correlation["_first_time"] = event_time
                correlation["first_seen"] = event["timestamp"]

            if correlation["_last_time"] is None or event_time > correlation["_last_time"]:

                correlation["_last_time"] = event_time
                correlation["last_seen"] = event["timestamp"]

        results = []

        for correlation in grouped.values():

            correlation.pop("_first_time")
            correlation.pop("_last_time")
            results.append(correlation)

        return results
