import json
import tempfile
from pathlib import Path

from ingestion.event_receiver import EventReceiver
from investigation.investigation_service import InvestigationService
from normalization.event_normalizer import EventNormalizer
from storage.event_reader import EventReader
from storage.event_store import EventStore


def main():

    receiver = EventReceiver()
    normalizer = EventNormalizer()

    raw_events = [
        {
            "hostname": "DESKTOP-01",
            "event_id": 4688,
            "process_name": "powershell.exe",
            "pid": 4242,
            "parent_process": "winword.exe",
            "user": "analyst",
            "event_type": "process_creation",
            "source": "edr",
            "severity": "high",
            "timestamp": "2026-08-18T10:05:00+00:00",
        },
        {
            "hostname": "DESKTOP-01",
            "event_id": 1,
            "process_name": "whoami.exe",
            "pid": 4243,
            "parent_process": "powershell.exe",
            "user": "analyst",
            "event_type": "process_creation",
            "source": "sysmon",
            "severity": "low",
            "timestamp": "2026-08-18T10:06:00+00:00",
        },
    ]

    with tempfile.TemporaryDirectory() as directory:

        log_file = Path(directory) / "events.jsonl"
        store = EventStore(log_file)

        for raw_event in raw_events:

            received_event = receiver.receive(raw_event)
            store.store(normalizer.normalize(received_event))

        service = InvestigationService(EventReader(log_file))
        investigation = service.investigate_host("DESKTOP-01")

        print("\nFOREX INVESTIGATION")
        print(json.dumps(investigation, indent=2))


if __name__ == "__main__":

    main()
