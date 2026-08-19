# SOC 1.0.0rc1 release candidate

Release checklist:

- [x] Stable `SOCService` and `SOCResponseV1` 1.0 contract
- [x] CLI and Python API remain independent of UI execution
- [x] Rich UI provides Overview, Alerts, Hosts, Incidents, and FOREX
- [x] `NO_COLOR`, bounded rows, one-shot and periodic refresh
- [x] Refresh is read-only; mutations are explicit transitions
- [x] Failed refresh retains the last valid snapshot as stale/degraded
- [x] FOREX consumes `FOREXWorkflow(service)` only
- [x] Guidance is visibly advisory-only
- [x] Empty and legacy data are supported
- [x] Full regression, compilation, CLI and UI smoke validation

DAY #77 is reserved for demonstration and release evidence; it contains no
implementation planned by this release candidate.
