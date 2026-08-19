"""Stable programmatic entry point for SOC consumers such as FOREX."""

from soc.config import SOCConfig
from soc.factory import build_components
from soc.models import (
    CorrelationV1, DetectionV1, EventQueryV1, HostProfileV1,
    InvestigationV1, SOCResponseV1,
)


class SOCService:
    """Public facade. Consumers should not depend on internal components."""

    def __init__(self, config=None, components=None):
        self.config = config or (components.config if components else SOCConfig.from_env())
        self._components = components or build_components(self.config)

    def ingest_event(self, event):
        normalized = self._components.normalizer.normalize(event)
        self._components.store.store(normalized)
        return SOCResponseV1(
            data={"event": normalized}, metadata={"stored": True}
        )

    def search_events(self, query=None, **filters):
        if query is not None:
            if filters:
                raise TypeError("pass either query or keyword filters, not both")
            if not isinstance(query, EventQueryV1):
                raise TypeError("query must be EventQueryV1")
            filters = {
                name: getattr(query, name) for name in query.__dataclass_fields__
                if getattr(query, name) is not None
            }
        else:
            query = EventQueryV1(**filters)
        events = self._components.search.search(**filters)
        return SOCResponseV1(
            data={"events": events, "query": query}, metadata={"count": len(events)}
        )

    def investigate_host(self, hostname, timeline_limit=None, newest_first=True):
        limit = timeline_limit or self.config.timeline_limit
        result = self._components.investigation.investigate_host(
            hostname, timeline_limit=limit, newest_first=newest_first
        )
        investigation = InvestigationV1(
            host_profile=HostProfileV1.from_mapping(result["host_profile"]),
            timeline=list(result["timeline"]),
            process_correlations=[
                CorrelationV1.from_mapping(item)
                for item in result["process_correlations"]
            ],
            detections=[DetectionV1.from_mapping(item) for item in result["detections"]],
            query=dict(result["query"]),
        )
        return SOCResponseV1(data=investigation, metadata={"hostname": hostname})

    def analyze_host(self, hostname):
        detections = self._components.investigation.detection_engine.analyze_host(hostname)
        public = [DetectionV1.from_mapping(item) for item in detections]
        return SOCResponseV1(
            data={"hostname": hostname, "detections": public},
            metadata={"count": len(public)},
        )
