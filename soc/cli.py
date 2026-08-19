"""Command line interface backed exclusively by SOCService."""

import argparse
import json
import sys
from pathlib import Path

from soc.config import SOCConfig
from soc.errors import SOCError
from soc.service import SOCService


def build_parser():
    parser = argparse.ArgumentParser(prog="soc", description="Local SOC toolkit")
    parser.add_argument("--events-path", type=Path)
    parser.add_argument("--alerts-path", type=Path)
    parser.add_argument("--human", action="store_true", help="pretty human-oriented output")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="ingest one JSON event")
    ingest.add_argument("event", help="JSON object, or @path to read a UTF-8 file")

    search = commands.add_parser("search", help="search stored events")
    search.add_argument("--host", dest="hostname")
    search.add_argument("--process", dest="process_name")
    search.add_argument("--user")
    search.add_argument("--event-id")
    search.add_argument("--source")
    search.add_argument("--severity")
    search.add_argument("--start", dest="start_timestamp")
    search.add_argument("--end", dest="end_timestamp")
    search.add_argument("--limit", type=int)

    investigate = commands.add_parser("investigate", help="investigate one host")
    investigate.add_argument("hostname")
    investigate.add_argument("--limit", type=int, dest="timeline_limit")
    investigate.add_argument("--oldest-first", action="store_true")

    alerts = commands.add_parser("alerts", help="query or manage alerts")
    alerts.add_argument("--host", dest="hostname")
    alerts.add_argument("--severity")
    alerts.add_argument("--status", choices=("open", "acknowledged", "closed"))
    alerts.add_argument("--promote-host")
    alerts.add_argument("--alert-id")
    alerts.add_argument("--set-status", choices=("acknowledged", "closed"))

    commands.add_parser("status", help="show health and runtime metrics")
    return parser


def _read_event(argument):
    payload = Path(argument[1:]).read_text(encoding="utf-8") if argument.startswith("@") else argument
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("event JSON must be an object")
    return value


def _invoke(service, args):
    if args.command == "ingest":
        return service.ingest_event(_read_event(args.event))
    if args.command == "search":
        filters = {
            name: getattr(args, name) for name in (
                "hostname", "process_name", "user", "event_id", "source", "severity",
                "start_timestamp", "end_timestamp", "limit",
            ) if getattr(args, name) is not None
        }
        return service.search_events(**filters)
    if args.command == "investigate":
        return service.investigate_host(
            args.hostname, timeline_limit=args.timeline_limit,
            newest_first=not args.oldest_first,
        )
    if args.command == "alerts":
        if args.promote_host:
            return service.create_alerts(args.promote_host)
        if args.alert_id or args.set_status:
            if not (args.alert_id and args.set_status):
                raise ValueError("--alert-id and --set-status must be used together")
            return service.transition_alert(args.alert_id, args.set_status)
        filters = {
            name: getattr(args, name) for name in ("hostname", "severity", "status")
            if getattr(args, name) is not None
        }
        return service.search_alerts(**filters)
    return service.status()


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    config = SOCConfig.from_env(
        **{name: getattr(args, name) for name in ("events_path", "alerts_path")
           if getattr(args, name) is not None}
    )
    try:
        response = _invoke(SOCService(config), args)
        payload = response.to_dict()
        if args.human:
            print(f"SOC {payload['status'].upper()} (schema {payload['schema_version']})")
            print(json.dumps(payload["data"], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (SOCError, ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        error = exc.to_dict() if isinstance(exc, SOCError) else {
            "code": "invalid_request", "message": str(exc)
        }
        print(json.dumps(error, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
