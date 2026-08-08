



















from storage.event_reader import EventReader


class HostProfile:

    def __init__(self):

        self.reader = EventReader()

    def build(self, hostname):

        events = self.reader.find_by_host(hostname)

        processes_count = {}

        most_frequent_process = None

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

        profile = {

            "hostname": hostname,

            "total_events": len(events),

            "processes": processes_count,

            "unique_processes": len(processes_count),

            "most_frequent_process": most_frequent_process

        }

        return profile



















