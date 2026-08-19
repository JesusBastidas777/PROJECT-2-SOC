"""Construct independent SOC component graphs from configuration."""

from dataclasses import dataclass

from alerting.alert_service import AlertService
from alerting.attention_queue import AttentionQueue
from correlation.alert_grouping import AlertGrouping
from investigation.event_search import EventSearch
from incident.incident_service import IncidentService
from incident.incident_timeline import IncidentTimeline
from investigation.host_detail import HostDetail
from inventory.host_catalog import HostCatalog
from investigation.investigation_service import InvestigationService
from normalization.event_normalizer import EventNormalizer
from monitoring.status_service import StatusService
from reporting.operational_summary import OperationalSummary
from risk.host_risk import HostRiskService
from soc.config import SOCConfig
from storage.event_reader import EventReader
from storage.event_store import EventStore
from storage.data_transfer import DataTransfer
from storage.integrity_service import IntegrityService
from storage.retention_service import RetentionService
from storage.compaction_service import AlertCompactionService
from storage.backup_service import BackupService
from maintenance.housekeeping_service import HousekeepingService
from maintenance.operational_journal import OperationalJournal


@dataclass
class SOCComponents:
    config: SOCConfig
    reader: EventReader
    store: EventStore
    normalizer: EventNormalizer
    search: EventSearch
    investigation: InvestigationService
    alerts: AlertService
    attention: AttentionQueue
    status: StatusService
    inventory: HostCatalog
    reporting: OperationalSummary
    transfer: DataTransfer
    integrity: IntegrityService
    host_details: HostDetail
    retention: RetentionService
    alert_compaction: AlertCompactionService
    backup: BackupService
    journal: OperationalJournal
    housekeeping: HousekeepingService
    risk: HostRiskService
    alert_grouping: AlertGrouping
    incidents: IncidentService
    incident_timeline: IncidentTimeline


def build_components(config=None):
    config = config or SOCConfig.from_env()
    reader = EventReader(config.events_path)
    alerts = AlertService(config.alerts_path, lock_timeout=config.lock_timeout)
    status = StatusService(reader, alerts)
    investigation = InvestigationService(reader)
    store = EventStore(config.events_path, lock_timeout=config.lock_timeout)
    normalizer = EventNormalizer()
    inventory = HostCatalog(reader, alerts)
    integrity = IntegrityService(config.events_path, config.lock_timeout)
    retention = RetentionService(
        config.events_path, store.uid_index, config.retention_archive_dir,
        config.lock_timeout,
    )
    alert_compaction = AlertCompactionService(
        config.alerts_path, config.alert_archive_dir, config.lock_timeout
    )
    backup = BackupService(
        config.events_path, config.alerts_path, store.uid_index,
        config.backup_dir, config.lock_timeout, incidents_path=config.incidents_path,
    )
    journal = OperationalJournal(config.maintenance_journal_path, config.lock_timeout)
    housekeeping = HousekeepingService(
        integrity, backup, retention, alert_compaction,
        journal, config.backup_dir,
    )
    risk = HostRiskService(inventory, alerts, investigation.detection_engine, reader)
    alert_grouping = AlertGrouping(alerts, risk)
    incidents = IncidentService(
        config.incidents_path, alerts, alert_grouping, config.lock_timeout
    )
    return SOCComponents(
        config=config,
        reader=reader,
        store=store,
        normalizer=normalizer,
        search=EventSearch(reader),
        investigation=investigation,
        alerts=alerts,
        attention=AttentionQueue(alerts),
        status=status,
        inventory=inventory,
        reporting=OperationalSummary(
            reader, alerts, investigation.detection_engine, status
        ),
        transfer=DataTransfer(reader, store, normalizer, config.lock_timeout),
        integrity=integrity,
        host_details=HostDetail(reader, alerts, inventory),
        retention=retention,
        alert_compaction=alert_compaction,
        backup=backup,
        journal=journal,
        housekeeping=housekeeping,
        risk=risk,
        alert_grouping=alert_grouping,
        incidents=incidents,
        incident_timeline=IncidentTimeline(incidents, alerts, reader),
    )
