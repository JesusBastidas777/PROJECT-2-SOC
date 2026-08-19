# FOREX integration guide

Create one `SOCService`, then pass it to `FOREXWorkflow`. Call
`security_posture()` globally or with a terminal identifier. The compact V1
response includes scope, observation state, risk, urgent alerts, incidents,
references, reasons, and next step. Unknown terminals are valid unobserved
results. FOREX never accesses JSONL, indices, internal services, or UI state.
