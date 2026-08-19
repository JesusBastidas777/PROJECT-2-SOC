# FOREX integration reference

FOREX should import only the stable `soc` package:

```python
from soc import FOREXAdapter, SOCConfig, SOCService

service = SOCService(SOCConfig.from_env())
adapter = FOREXAdapter()
response = adapter.ingest(service, forex_event)
```

`FOREXAdapter.adapt` maps `terminal_id` to `host`, `type` to `event_type`,
defaults `source` to `forex`, and derives a stable namespaced `event_uid` from
`forex_event_id`. Unknown FOREX fields are retained for later investigation.
Validation and persistence remain the responsibility of `SOCService`.

Retries with the same `forex_event_id` are idempotent. Callers should inspect
`response.metadata["stored"]` and `response.metadata["duplicate"]`. Domain
failures continue to use the structured `SOCError` hierarchy.

Run the complete local example with:

```text
python3 -m examples.forex_workflow
```

The workflow ingests an event, retries safely when called again, discovers its
host, promotes detections to alerts, and obtains an operational summary. It
does not require a network service or any external dependency.
