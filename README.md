# FOREX SOC

Local, JSONL-backed security operations console with a stable Python facade,
headless CLI, Rich terminal UI, and dedicated FOREX workflow.

## Install and run

Python 3.11–3.14 is supported. Install with `python3 -m pip install -e .`.

```bash
python3 -m soc.cli --help
python3 -m soc.cli ui --once
python3 -m soc.cli ui --view alerts --once
```

Omit `--once` for periodic refresh. Set `NO_COLOR=1` for plain output. Use
`--host FOREX-01` with Hosts or FOREX views and `--max-rows` to bound output.
The normal CLI and Python API do not require starting the UI.

```python
from soc import FOREXWorkflow, SOCConfig, SOCService

service = SOCService(SOCConfig.from_env())
posture = FOREXWorkflow(service).security_posture("FOREX-01")
```

Response recommendations are advisory-only. No UI refresh executes response or
performs lifecycle transitions.
