"""End-to-end FOREX integration example using only the public SOC package."""

import json
import tempfile

from soc import FOREXWorkflow, SOCConfig, SOCService


def run_workflow(service, forex_event):
    return FOREXWorkflow(service).ingest_and_assess(forex_event).to_dict()


def main():
    event = {
        "forex_event_id": "order-20260819-001",
        "terminal_id": "FOREX-01",
        "type": "process_creation",
        "severity": "high",
        "process_name": "psexec.exe",
        "timestamp": "2026-08-19T00:00:00Z",
        "symbol": "EURUSD",
    }
    with tempfile.TemporaryDirectory() as directory:
        result = run_workflow(SOCService(SOCConfig(base_dir=directory)), event)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
