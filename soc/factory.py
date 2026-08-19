"""Construct independent SOC component graphs from configuration."""

from dataclasses import dataclass

from alerting.alert_service import AlertService
from investigation.event_search import EventSearch
from inventory.host_catalog import HostCatalog
from investigation.investigation_service import InvestigationService
from normalization.event_normalizer import EventNormalizer
from monitoring.status_service import StatusService
from reporting.operational_summary import OperationalSummary
from soc.config import SOCConfig
from storage.event_reader import EventReader
from storage.event_store import EventStore
from storage.data_transfer import DataTransfer
from storage.integrity_service import IntegrityService


@dataclass
class SOCComponents:
    config: SOCConfig
    reader: EventReader
    store: EventStore
    normalizer: EventNormalizer
    search: EventSearch
    investigation: InvestigationService
    alerts: AlertService
    status: StatusService
    inventory: HostCatalog
    reporting: OperationalSummary
    transfer: DataTransfer
    integrity: IntegrityService


def build_components(config=None):
    config = config or SOCConfig.from_env()
    reader = EventReader(config.events_path)
    alerts = AlertService(config.alerts_path, lock_timeout=config.lock_timeout)
    status = StatusService(reader, alerts)
    investigation = InvestigationService(reader)
    store = EventStore(config.events_path, lock_timeout=config.lock_timeout)
    normalizer = EventNormalizer()
    return SOCComponents(
        config=config,
        reader=reader,
        store=store,
        normalizer=normalizer,
        search=EventSearch(reader),
        investigation=investigation,
        alerts=alerts,
        status=status,
        inventory=HostCatalog(reader, alerts),
        reporting=OperationalSummary(
            reader, alerts, investigation.detection_engine, status
        ),
        transfer=DataTransfer(reader, store, normalizer, config.lock_timeout),
        integrity=IntegrityService(config.events_path, config.lock_timeout),
    )
