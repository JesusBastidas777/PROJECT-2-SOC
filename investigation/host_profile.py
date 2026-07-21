



from storage.event_reader import EventReader


class HostProfile:

    def __init__(self):

        self.reader = EventReader()

    def build(self, hostname):

        events = self.reader.find_by_host(hostname)

        profile = {

            "hostname": hostname,

            "total_events": len(events)

        }

        return profile






