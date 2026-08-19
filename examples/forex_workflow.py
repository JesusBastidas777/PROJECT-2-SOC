"""End-to-end FOREX integration example using only the public SOC package."""

import json
import tempfile

from soc import FOREXWorkflow, SOCConfig, SOCService


def run_workflow(service, forex_event):
    return FOREXWorkflow(service).ingest_and_assess(forex_event).to_dict()


def get_security_posture(service, terminal_id=None):
    """One-call security posture suitable for a FOREX decision boundary."""
    return FOREXWorkflow(service).security_posture(terminal_id).to_dict()


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
        service = SOCService(SOCConfig(base_dir=directory))
        result = run_workflow(service, event)
        posture = get_security_posture(service, "FOREX-01")
    print(json.dumps({"assessment": result, "posture": posture}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
