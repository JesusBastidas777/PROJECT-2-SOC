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

The stable methods are `ingest_event`, `search_events`, `investigate_host`, `analyze_host`,
`create_alerts`, `search_alerts`, `transition_alert`, `health`, `metrics`, and `status`.
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
