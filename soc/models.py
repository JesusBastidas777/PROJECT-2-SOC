"""Versioned, JSON-safe public response models."""

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional


def to_primitive(value):
    if is_dataclass(value):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_primitive(item) for item in value]
    return value


@dataclass(frozen=True)
class EventQueryV1:
    event_uid: Optional[str] = None
    hostname: Optional[str] = None
    process_name: Optional[str] = None
    user: Optional[str] = None
    event_id: Any = None
    source: Optional[str] = None
    severity: Optional[str] = None
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    limit: Optional[int] = None
    sort_order: str = "newest"


@dataclass(frozen=True)
class HostProfileV1:
    hostname: str
    total_events: int = 0
    processes: Dict[str, int] = field(default_factory=dict)
    unique_processes: int = 0
    most_frequent_process: Optional[str] = None
    most_frequent_count: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    users: List[str] = field(default_factory=list)
    unique_users: int = 0
    event_ids: List[Any] = field(default_factory=list)
    recent_processes: List[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value):
        return cls(**{
            name: value[name] for name in cls.__dataclass_fields__ if name in value
        })


@dataclass(frozen=True)
class CorrelationV1:
    hostname: str
    parent_process: str
    process_name: str
    count: int
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    @classmethod
    def from_mapping(cls, value):
        return cls(**{name: value.get(name) for name in cls.__dataclass_fields__})


@dataclass(frozen=True)
class DetectionV1:
    rule_name: str
    severity: str
    reason: str
    event: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value):
        return cls(
            rule_name=value.get("rule_name", "unknown"),
            severity=value.get("severity", "unknown"),
            reason=value.get("reason", ""),
            event=dict(value.get("event") or {}),
        )


@dataclass(frozen=True)
class AlertV1:
    alert_id: str
    timestamp: str
    status: str
    hostname: str
    severity: str
    rule_name: str
    reason: str
    event: Dict[str, Any] = field(default_factory=dict)
    priority: str = "P4"
    event_uid: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    closed_at: Optional[str] = None

    @classmethod
    def from_mapping(cls, value):
        values = {
            name: value[name] for name in cls.__dataclass_fields__ if name in value
        }
        values.setdefault("created_at", value.get("timestamp"))
        values.setdefault("updated_at", value.get("timestamp"))
        values.setdefault("event_uid", (value.get("event") or {}).get("event_uid"))
        values.setdefault("priority", {
            "critical": "P1", "high": "P2", "medium": "P3",
        }.get(str(value.get("severity") or "").lower(), "P4"))
        return cls(**values)


@dataclass(frozen=True)
class MetricsV1:
    events_stored: int
    invalid_events: int
    open_alerts: int
    last_ingestion: Optional[str]
    operation_durations_ms: Dict[str, float] = field(default_factory=dict)
    duplicates_rejected: int = 0


@dataclass(frozen=True)
class HealthV1:
    state: str
    checks: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class HostRecordV1:
    hostname: str
    observed_names: List[str] = field(default_factory=list)
    total_events: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    max_severity: str = "unknown"
    open_alerts: int = 0

    @classmethod
    def from_mapping(cls, value):
        return cls(**{name: value[name] for name in cls.__dataclass_fields__ if name in value})


@dataclass(frozen=True)
class OperationalSummaryV1:
    window: Dict[str, Optional[str]]
    hostname: Optional[str]
    total_events: int
    events_by_severity: Dict[str, int] = field(default_factory=dict)
    events_by_source: Dict[str, int] = field(default_factory=dict)
    events_by_type: Dict[str, int] = field(default_factory=dict)
    active_hosts: int = 0
    top_hosts: List[Dict[str, Any]] = field(default_factory=list)
    alerts_by_priority: Dict[str, int] = field(default_factory=dict)
    alerts_by_status: Dict[str, int] = field(default_factory=dict)
    top_detections: List[Dict[str, Any]] = field(default_factory=list)
    duplicates_rejected: int = 0
    invalid_records: int = 0
    last_event: Optional[str] = None
    attention_required: bool = False

    @classmethod
    def from_mapping(cls, value):
        return cls(**{name: value[name] for name in cls.__dataclass_fields__ if name in value})


@dataclass(frozen=True)
class InvestigationV1:
    host_profile: HostProfileV1
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    process_correlations: List[CorrelationV1] = field(default_factory=list)
    detections: List[DetectionV1] = field(default_factory=list)
    query: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SOCResponseV1:
    schema_version: str = "1.0"
    status: str = "success"
    data: Any = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return to_primitive(self)
