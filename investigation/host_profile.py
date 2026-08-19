









from storage.event_reader import EventReader
from investigation.host_timeline import HostTimeline
import logging

logger = logging.getLogger(__name__)


class HostProfile:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()

        self.timeline = HostTimeline(self.reader)

        self.profile_cache = {}

        self.profile_cache_mtime = {}

    def build(self, hostname):

        current_mtime = self.reader.signature()

        if (
            hostname in self.profile_cache
            and self.profile_cache_mtime.get(hostname) == current_mtime
        ):

            return self.profile_cache[hostname]

        events = self.reader.find_by_host(hostname)

        processes_count = {}

        most_frequent_process = None

        most_frequent_count = 0

        users = []

        event_ids = []

        for event in events:

            process_name = event.get("process_name")

            if process_name is None:

                continue

            if process_name not in processes_count:

                processes_count[process_name] = 0

            processes_count[process_name] += 1

            user = event.get("user")

            if user is not None and user not in users:

                users.append(user)

            event_id = event.get("event_id")

            if event_id is not None and event_id not in event_ids:

                event_ids.append(event_id)

        if processes_count:

            most_frequent_process = max(
                processes_count,
                key=processes_count.get
            )

            most_frequent_count = processes_count[most_frequent_process]

        chronological_events = self.timeline.build(hostname)
        timestamped_events = [
            event for event in chronological_events if event.get("timestamp")
        ]
        newest_events = list(reversed(chronological_events))
        recent_processes = [
            event.get("process_name")
            for event in newest_events
            if event.get("process_name") is not None
        ][:5]

        profile = {

            "hostname": hostname,

            "total_events": len(events),

            "processes": processes_count,

            "unique_processes": len(processes_count),

            "most_frequent_process": most_frequent_process,

            "most_frequent_count": most_frequent_count,

            "first_seen": (
                timestamped_events[0].get("timestamp") if timestamped_events else None
            ),

            "last_seen": (
                timestamped_events[-1].get("timestamp") if timestamped_events else None
            ),

            "users": users,

            "unique_users": len(users),

            "event_ids": event_ids,

            "recent_processes": recent_processes

        }

        self.profile_cache[hostname] = profile

        self.profile_cache_mtime[hostname] = current_mtime

        return profile

    def show_summary(self, hostname):
        profile = self.build(hostname)
        logger.info("host profile: %s", profile)
        return profile













