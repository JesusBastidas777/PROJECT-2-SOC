


from ingestion.event_receiver import EventReceiver

from normalization.event_normalizer import EventNormalizer

from storage.event_store import EventStore

from storage.event_reader import EventReader

def main():

    receiver = EventReceiver()

    normalizer = EventNormalizer()

    store = EventStore()

    reader = EventReader()

    raw_event = {

    "hostname": "DESKTOP-01",
    "event_id": 4688,
    "process_name": "powershell.exe"

    }

    event = receiver.receive(raw_event)

    normalized_event = normalizer.normalize(event)

    store.store(normalized_event)

    raw_event2 = {

    "hostname": "DESKTOP-02",
    "event_id": 1,
    "process_name": "cmd.exe"

    }

    event2 = receiver.receive(raw_event2)

    normalized_event2 = normalizer.normalize(event2)

    store.store(normalized_event2)

    print(store.events)

    print(store.count())

    store.show_summary()

    events = reader.read_events()

    matches = reader.find_by_host("DESKTOP-01")

    print("\nEvents from DESKTOP-01:")

    print(matches)

    print(events)

    matches = reader.find_by_host("DESKTOP-01")

    print("\nEvents from DESKTOP-01:")

    print(matches)

if __name__ == "__main__":

    main()



