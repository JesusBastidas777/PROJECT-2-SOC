"""Stable programmatic entry point for SOC consumers such as FOREX."""

from soc.config import SOCConfig
from soc.factory import build_components
from soc.models import (
    CorrelationV1, DetectionV1, EventQueryV1, HostProfileV1,
    HostDetailV1, HostRecordV1, HostRiskV1, InvestigationV1, OperationalSummaryV1,
    SOCResponseV1,
)


class SOCService:
    """Public facade. Consumers should not depend on internal components."""

    def __init__(self, config=None, components=None):
        self.config = config or (components.config if components else SOCConfig.from_env())
        self._components = components or build_components(self.config)

    def ingest_event(self, event):
        with self._components.status.measure("ingest_event"):
            normalized = self._components.normalizer.normalize(event)
            stored_event, stored = self._components.store.store_once(normalized)
            if stored:
                self._components.status.record_ingestion()
            else:
                self._components.status.record_duplicate()
        return SOCResponseV1(
            data={"event": stored_event},
            metadata={"stored": stored, "duplicate": not stored},
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
        with self._components.status.measure("search_events"):
            page = self._components.search.search_page(
                max_limit=self.config.search_limit_max, **filters
            )
            events = page["events"]
        return SOCResponseV1(
            data={"events": events, "query": query},
            metadata={
                "count": len(events), "has_more": page["has_more"],
                "next_cursor": page["next_cursor"],
            },
        )

    def get_event(self, event_uid):
        """Return one identified event without exposing storage internals."""
        with self._components.status.measure("get_event"):
            event = self._components.reader.find_by_uid(event_uid)
        return SOCResponseV1(
            data={"event": event}, metadata={"found": event is not None}
        )

    def investigate_host(self, hostname, timeline_limit=None, newest_first=True):
        limit = timeline_limit or self.config.timeline_limit
        with self._components.status.measure("investigate_host"):
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
        with self._components.status.measure("analyze_host"):
            detections = self._components.investigation.detection_engine.analyze_host(hostname)
        public = [DetectionV1.from_mapping(item) for item in detections]
        return SOCResponseV1(
            data={"hostname": hostname, "detections": public},
            metadata={"count": len(public)},
        )

    def create_alerts(self, hostname):
        detections = self._components.investigation.detection_engine.analyze_host(hostname)
        alerts = self._components.alerts.promote(detections)
        return SOCResponseV1(data={"alerts": alerts}, metadata={"count": len(alerts)})

    def search_alerts(self, **filters):
        alerts = self._components.alerts.search(**filters)
        return SOCResponseV1(data={"alerts": alerts}, metadata={"count": len(alerts)})

    def attention_queue(self, **filters):
        queue = self._components.attention.build(**filters)
        return SOCResponseV1(data={"queue": queue}, metadata={
            "count": len(queue["entries"]), "total": queue["total"],
        })

    def correlate_alerts(self, **options):
        groups = self._components.alert_grouping.correlate(**options)
        return SOCResponseV1(
            data={"groups": groups}, metadata={"count": len(groups), "derived": True}
        )

    def create_incident(self, *, alert_ids=None, group_id=None, title=None, summary=None):
        incident = self._components.incidents.create(
            alert_ids=alert_ids, group_id=group_id, title=title, summary=summary
        )
        return SOCResponseV1(data={"incident": incident})

    def get_incident(self, incident_id):
        incident = self._components.incidents.get(incident_id)
        return SOCResponseV1(
            data={"incident": incident}, metadata={"found": incident is not None}
        )

    def list_incidents(self, **filters):
        incidents = self._components.incidents.list(**filters)
        return SOCResponseV1(
            data={"incidents": incidents}, metadata={"count": len(incidents)}
        )

    def transition_incident(self, incident_id, status):
        incident = self._components.incidents.transition(incident_id, status)
        return SOCResponseV1(data={"incident": incident})

    def get_incident_timeline(self, incident_id, **options):
        timeline = self._components.incident_timeline.build(incident_id, **options)
        return SOCResponseV1(
            data={"timeline": timeline},
            metadata={"count": len(timeline["entries"]), "total": timeline["total"]},
        )

    def transition_alert(self, alert_id, status):
        alert = self._components.alerts.transition(alert_id, status)
        return SOCResponseV1(data={"alert": alert})

    def list_hosts(self):
        hosts = [HostRecordV1.from_mapping(item) for item in self._components.inventory.list()]
        return SOCResponseV1(data={"hosts": hosts}, metadata={"count": len(hosts)})

    def get_host(self, hostname):
        item = self._components.inventory.get(hostname)
        return SOCResponseV1(
            data={"host": HostRecordV1.from_mapping(item) if item else None},
            metadata={"found": item is not None},
        )

    def get_host_detail(self, hostname, recent_limit=10):
        item = self._components.host_details.build(hostname, recent_limit=recent_limit)
        return SOCResponseV1(
            data={"host": HostDetailV1.from_mapping(item) if item else None},
            metadata={"found": item is not None, "hostname": hostname},
        )

    def get_host_risk(self, hostname):
        risk = self._components.risk.calculate(hostname)
        return SOCResponseV1(
            data={"risk": HostRiskV1.from_mapping(risk)},
            metadata={"hostname": hostname, "known_host": risk["known_host"]},
        )

    def operational_summary(self, **filters):
        with self._components.status.measure("operational_summary"):
            summary = self._components.reporting.build(**filters)
        return SOCResponseV1(data={"summary": OperationalSummaryV1.from_mapping(summary)})

    def export_events(self, destination, **filters):
        return SOCResponseV1(data={"export": self._components.transfer.export_events(
            destination, **filters
        )})

    def import_events(self, source, *, dry_run=False):
        return SOCResponseV1(data={"import": self._components.transfer.import_events(
            source, dry_run=dry_run
        )})

    def audit_storage(self):
        return SOCResponseV1(data={"integrity": self._components.integrity.audit()})

    def repair_storage(self, quarantine_path=None):
        return SOCResponseV1(data={"integrity": self._components.integrity.repair(
            quarantine_path
        )})

    def plan_retention(self, *, max_age_days=None, max_bytes=None):
        return SOCResponseV1(data={"retention": self._components.retention.plan(
            max_age_days=max_age_days, max_bytes=max_bytes
        )})

    def apply_retention(self, *, max_age_days=None, max_bytes=None):
        return SOCResponseV1(data={"retention": self._components.retention.apply(
            max_age_days=max_age_days, max_bytes=max_bytes
        )})

    def plan_alert_compaction(self):
        return SOCResponseV1(data={
            "compaction": self._components.alert_compaction.plan()
        })

    def compact_alerts(self):
        return SOCResponseV1(data={
            "compaction": self._components.alert_compaction.apply()
        })

    def create_backup(self, destination):
        return SOCResponseV1(data={"backup": self._components.backup.create(destination)})

    def verify_backup(self, source):
        result = self._components.backup.verify(source)
        return SOCResponseV1(
            status="success" if result["valid"] else "degraded",
            data={"backup": result},
        )

    def restore_backup(self, source, *, dry_run=False):
        return SOCResponseV1(data={
            "restore": self._components.backup.restore(source, dry_run=dry_run)
        })

    def housekeeping(self, *, plan_only=True, **options):
        return SOCResponseV1(data={
            "maintenance": self._components.housekeeping.run(
                plan_only=plan_only, **options
            )
        })

    def maintenance_history(self, limit=20):
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        entries = self._components.journal.read(limit=limit)
        return SOCResponseV1(
            data={"maintenance": entries}, metadata={"count": len(entries)}
        )

    def health(self):
        health = self._components.status.health()
        return SOCResponseV1(
            status="success" if health.state == "healthy" else "degraded",
            data={"health": health},
        )

    def metrics(self):
        return SOCResponseV1(data={"metrics": self._components.status.metrics()})

    def status(self):
        health = self._components.status.health()
        metrics = self._components.status.metrics()
        return SOCResponseV1(
            status="success" if health.state == "healthy" else "degraded",
            data={
                "health": health, "metrics": metrics,
                "maintenance_last": self._components.journal.latest_completed(),
            },
        )
