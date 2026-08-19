from detection.process_rules import evaluate_process_rules
from detection.enrichment import enrich_detection
from storage.event_reader import EventReader


class DetectionEngine:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()

    def analyze_events(self, events):

        detections = []

        for event in events:

            detections.extend(
                enrich_detection(item) for item in evaluate_process_rules(event)
            )

        return detections

    def analyze_host(self, hostname):

        return self.analyze_events(self.reader.find_by_host(hostname))
