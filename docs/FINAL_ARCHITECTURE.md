# Final SOC application architecture

`SOCService` is the only domain facade used by the CLI, terminal UI, and
FOREX. Every public operation returns `SOCResponseV1`. Presentation code may
format responses, but never opens JSONL or instantiates internal services.

The Python API, headless CLI, and optional Rich UI remain independent. JSONL
is the durable store and `FOREXWorkflow(service)` is the FOREX boundary.

| Screen | Public calls |
| --- | --- |
| Overview | `command_center()` |
| Alerts | `attention_queue()`, `get_alert()`, `transition_alert()` |
| Hosts | `list_hosts()`, `get_host_detail()`, `get_host_risk()`, `investigate_host()` |
| Incidents | `list_incidents()`, `get_incident()`, `get_alert()`, `get_incident_timeline()`, `recommend_response()`, `transition_incident()` |
| FOREX | Public `FOREXWorkflow` methods |

Refresh is read-only. Mutations are explicit lifecycle transitions. Response
guidance remains advisory-only.
