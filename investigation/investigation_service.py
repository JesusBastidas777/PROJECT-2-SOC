from detection.detection_engine import DetectionEngine
from investigation.host_profile import HostProfile
from investigation.host_timeline import HostTimeline
from investigation.process_correlation import ProcessCorrelation
from storage.event_reader import EventReader


class InvestigationService:

    def __init__(self, reader=None):

        self.reader = reader or EventReader()
        self.host_profiles = HostProfile(self.reader)
        self.host_timelines = HostTimeline(self.reader)
        self.process_correlations = ProcessCorrelation(self.reader)
        self.detection_engine = DetectionEngine(self.reader)

    def investigate_host(self, hostname, timeline_limit=10, newest_first=True):

        return {
            "host_profile": self.host_profiles.build(hostname),
            "timeline": self.host_timelines.build(
                hostname,
                newest_first=newest_first,
                limit=timeline_limit,
            ),
            "process_correlations": self.process_correlations.correlate(hostname),
            "detections": self.detection_engine.analyze_host(hostname),
            "query": {
                "hostname": hostname,
                "timeline_limit": timeline_limit,
                "newest_first": newest_first,
            },
        }
