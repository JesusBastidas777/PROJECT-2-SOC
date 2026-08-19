# FOREX public contract v1

FOREX imports only `SOCConfig`, `SOCService`, and optionally the immutable query/response
dataclasses in `soc.models`. It must not import storage, investigation, detection, alerting,
index, cache, or JSONL implementation modules.

```python
from soc import SOCConfig, SOCService
from soc.models import EventQueryV1

service = SOCService(SOCConfig.from_env())
result = service.search_events(EventQueryV1(hostname="HOST-01", limit=100))
payload = result.to_dict()
```

The stable methods are `ingest_event`, `search_events`, `get_event`, `investigate_host`, `analyze_host`,
`create_alerts`, `search_alerts`, `transition_alert`, `list_hosts`, `get_host`, `health`,
`operational_summary`, `export_events`, `import_events`, `audit_storage`,
`repair_storage`, `metrics`, and `status`.

`get_host_detail(hostname, recent_limit=10)` is an additive detailed view with
consolidated names, activity bounds, event dimensions, frequent processes and
users, open alerts by priority, and recent activity. Host lookup ignores case
and surrounding whitespace; `get_host` remains unchanged.

Event searches accept `event_uid` for direct indexed lookup and `sort_order`
(`newest` by default or `oldest`). Results are ordered deterministically by
timestamp, event UID, and stable stored position. Legacy records without valid
timestamps or UIDs remain searchable.

Search pagination uses an opaque `cursor` bound to the filters and sort order.
Responses add `has_more` and `next_cursor` metadata while preserving
`data.events`. Pagination is anchored to the last returned event: newly
ingested events that sort before that anchor are not replayed, while events
that sort after it can appear on later pages. `SOC_SEARCH_LIMIT_MAX` bounds a
requested page size (500 by default).

Event retention is explicit and disabled unless a caller invokes
`plan_retention` or `apply_retention` with an age or size policy. Planning is
read-only. Applying archives removed JSONL records and a checksummed manifest
before atomically replacing the active log. Missing or invalid timestamps are
retained by default and the rebuildable UID index is refreshed afterward.

Alert compaction is separately available through `plan_alert_compaction` and
`compact_alerts`. It archives the complete append-only lifecycle history and a
checksummed manifest before keeping one current record per alert in the active
log. Repeating compaction on an already compact log is a no-op. Event records
are never compacted by this operation.

`create_backup`, `verify_backup`, and `restore_backup` manage a consistent
events-and-alerts snapshot with relative paths, sizes, SHA-256 checksums, and a
versioned logical signature. Restore supports dry-run, creates a pre-restore
safety backup, replaces both stores under ordered locks, rolls back both on a
partial failure, and rebuilds derived UID data.
Every method returns `SOCResponseV1`. Its JSON shape is:

```json
{"schema_version":"1.0","status":"success","data":{},"errors":[],"metadata":{}}
```

`status` may be `success` or `degraded`. Domain failures raise a subclass of `SOCError`;
`SOCError.to_dict()` returns a stable `code`, `message`, and optional `details` mapping.
Configuration paths are explicit or use `SOC_BASE_DIR`, `SOC_EVENTS_PATH`, and
`SOC_ALERTS_PATH`; they never depend on the process current working directory.

New events include a stable `event_uid`, `ingested_at`,
`event_schema_version`, and a minimal `provenance` mapping. These fields are
additive: `event_id` retains its producer-specific meaning and legacy stored
events without identity metadata remain readable.

`ingest_event` is idempotent for identified events. Its response metadata
contains `stored` and `duplicate`; a retry returns the previously stored event
without appending another JSONL record.

`list_hosts` and `get_host` expose a derived inventory. Host lookup ignores
leading/trailing whitespace and letter case, while stored events retain their
observed host value.

Alerts expose operational `priority` (`P1`-`P4`), `event_uid`, and explicit
`created_at`, `updated_at`, `acknowledged_at`, and `closed_at` lifecycle fields.
The legacy `timestamp` field remains available. Alert queries may filter by
priority and are ordered by priority then creation time.

`operational_summary` returns a typed, deterministic aggregation for an
optional UTC interval and host. It includes event dimensions, active hosts,
alert priority/state, top detections, data-quality counters, and an
`attention_required` indicator.

JSONL transfer uses the same validation and idempotency rules as direct
ingestion. Integrity auditing is read-only. Repair is explicit and runs under
an exclusive lock, preserving the original as a backup and copying invalid
records with line details to a quarantine JSONL file.

FOREX may optionally use the public `FOREXAdapter` to map `terminal_id`,
`type`, and `forex_event_id` into the canonical contract. The adapter preserves
unknown producer fields and delegates validation and storage to `SOCService`.
See `config/forex_integration.md` for an executable reference workflow.
