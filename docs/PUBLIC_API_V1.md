# SOC public API v1

Supported consumer imports from `soc` are `SOCConfig`, `SOCService`,
`SOCResponseV1`, `EventQueryV1`, `FOREXAdapter`, and `FOREXWorkflow`.

Every call returns an envelope with `schema_version`, `status`, `data`,
`errors`, and `metadata`. Version 1.0 is additive and consumers ignore unknown
fields. `to_dict()` is JSON-safe.

Legacy records may omit timestamps, evidence, event references, process/user
details, lifecycle timestamps, provenance, and enrichment. Lists and mappings
may be empty; lookups may return `None` with `metadata.found=false`.

`storage`, `alerting`, `incident`, `investigation`, `risk`, `reporting`, and
`detection` are private application layers, not consumer APIs.
