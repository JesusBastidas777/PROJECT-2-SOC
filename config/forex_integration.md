# FOREX integration reference

FOREX should import only the stable `soc` package:

```python
from soc import FOREXAdapter, FOREXWorkflow, SOCConfig, SOCService

service = SOCService(SOCConfig.from_env())
adapter = FOREXAdapter()
response = adapter.ingest(service, forex_event)
workflow = FOREXWorkflow(service)
assessment = workflow.ingest_and_assess(forex_event)
context = workflow.get_terminal_context("FOREX-01")
report = workflow.export_terminal_report("FOREX-01", "reports/forex-01.json")
posture = workflow.security_posture("FOREX-01")
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

All workflow methods return `SOCResponseV1` and call only public `SOCService`
methods. Reports are versioned, self-contained JSON with host identity and
statistics, recent events, detections, open alerts, operational summary,
parameters, and generation time. Export uses atomic creation and refuses to
overwrite an existing destination unless `overwrite=True` is explicit.

For the smallest decision boundary, call `security_posture()` globally or pass
a terminal ID. It returns only a versioned posture state, explainable risk,
urgent-alert and open-incident counts, top reasons, a descriptive next step,
generation time, and bounded alert/incident references. It does not return the
full event stream and does not execute response actions.
