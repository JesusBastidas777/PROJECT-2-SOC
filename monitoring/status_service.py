"""Local health checks and lightweight runtime metrics."""

from contextlib import contextmanager
from datetime import datetime, timezone
from time import perf_counter

from soc.models import HealthV1, MetricsV1
from storage.errors import StorageError


class StatusService:
    def __init__(self, event_reader, alert_service):
        self.event_reader = event_reader
        self.alert_service = alert_service
        self.last_ingestion = None
        self.operation_durations_ms = {}

    @contextmanager
    def measure(self, operation):
        started = perf_counter()
        try:
            yield
        finally:
            self.operation_durations_ms[operation] = round(
                (perf_counter() - started) * 1000, 3
            )

    def record_ingestion(self):
        self.last_ingestion = datetime.now(timezone.utc).isoformat()

    def metrics(self):
        events = self.event_reader.read_events()
        invalid = self.event_reader.invalid_line_count
        open_alerts = len(self.alert_service.search(status="open"))
        return MetricsV1(
            events_stored=len(events),
            invalid_events=invalid,
            open_alerts=open_alerts,
            last_ingestion=self.last_ingestion,
            operation_durations_ms=dict(self.operation_durations_ms),
        )

    def health(self):
        checks = {"event_storage": "ok", "alert_storage": "ok"}
        state = "healthy"
        try:
            metrics = self.metrics()
            if metrics.invalid_events:
                state = "degraded"
                checks["event_storage"] = "invalid_records"
        except StorageError:
            state = "degraded"
            checks["event_storage"] = "unavailable"
        return HealthV1(state=state, checks=checks)
