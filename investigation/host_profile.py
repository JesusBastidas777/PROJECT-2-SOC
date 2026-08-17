









from storage.event_reader import EventReader


class HostProfile:

    def __init__(self):

        self.reader = EventReader()

        self.profile_cache = {}

        self.profile_cache_mtime = {}

    def build(self, hostname):

        current_mtime = self.reader.log_file.stat().st_mtime

        if (
            hostname in self.profile_cache
            and self.profile_cache_mtime.get(hostname) == current_mtime
        ):

            return self.profile_cache[hostname]

        events = self.reader.find_by_host(hostname)

        processes_count = {}

        most_frequent_process = None

        most_frequent_count = 0

        for event in events:

            process_name = event["process_name"]

            if process_name not in processes_count:

                processes_count[process_name] = 0

            processes_count[process_name] += 1

        if processes_count:

            most_frequent_process = max(
                processes_count,
                key=processes_count.get
            )

            most_frequent_count = processes_count[most_frequent_process]

        profile = {

            "hostname": hostname,

            "total_events": len(events),

            "processes": processes_count,

            "unique_processes": len(processes_count),

            "most_frequent_process": most_frequent_process,

            "most_frequent_count": most_frequent_count

        }

        self.profile_cache[hostname] = profile

        self.profile_cache_mtime[hostname] = current_mtime

        return profile

























