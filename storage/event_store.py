


class EventStore:

    def __init__(self):

        self.events = []

    def store(self,event):

        self.events.append(event)

        print("Event stored:")

        print(event)

    def count(self):

        return len(self.events)

    def show_summary(self):

        print(f"Total events: {self.count()}")
