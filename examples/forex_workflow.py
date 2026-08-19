"""End-to-end FOREX integration example using only the public SOC package."""

import json
import tempfile

from soc import FOREXAdapter, SOCConfig, SOCService


def run_workflow(service, forex_event):
    adapter = FOREXAdapter()
    ingestion = adapter.ingest(service, forex_event)
    hostname = ingestion.data["event"]["host"]
    alerts = service.create_alerts(hostname)
    return {
        "ingestion": ingestion.to_dict(),
        "host": service.get_host(hostname).to_dict(),
        "alerts": alerts.to_dict(),
        "summary": service.operational_summary(hostname=hostname).to_dict(),
    }


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
