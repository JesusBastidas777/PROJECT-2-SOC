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
    search.add_argument("--event-uid")
    search.add_argument("--host", dest="hostname")
    search.add_argument("--process", dest="process_name")
    search.add_argument("--user")
    search.add_argument("--event-id")
    search.add_argument("--source")
    search.add_argument("--severity")
    search.add_argument("--start", dest="start_timestamp")
    search.add_argument("--end", dest="end_timestamp")
    search.add_argument("--limit", type=int)
    search.add_argument("--sort-order", choices=("newest", "oldest"), default="newest")
    search.add_argument("--cursor")

    investigate = commands.add_parser("investigate", help="investigate one host")
    investigate.add_argument("hostname")
    investigate.add_argument("--limit", type=int, dest="timeline_limit")
    investigate.add_argument("--oldest-first", action="store_true")

    alerts = commands.add_parser("alerts", help="query or manage alerts")
    alerts.add_argument("--host", dest="hostname")
    alerts.add_argument("--severity")
    alerts.add_argument("--priority", choices=("P1", "P2", "P3", "P4"))
    alerts.add_argument("--status", choices=("open", "acknowledged", "closed"))
    alerts.add_argument("--promote-host")
    alerts.add_argument("--alert-id")
    alerts.add_argument("--set-status", choices=("acknowledged", "closed"))

    commands.add_parser("status", help="show health and runtime metrics")
    hosts = commands.add_parser("hosts", help="list or inspect observed hosts")
    hosts.add_argument("hostname", nargs="?")
    hosts.add_argument("--detail", action="store_true")
    hosts.add_argument("--recent-limit", type=int, default=10)
    summary = commands.add_parser("summary", help="show an operational summary")
    summary.add_argument("--host", dest="hostname")
    summary.add_argument("--start", dest="start_timestamp")
    summary.add_argument("--end", dest="end_timestamp")
    summary.add_argument("--limit", type=int)
    export = commands.add_parser("export", help="export events as JSONL")
    export.add_argument("path", type=Path)
    export.add_argument("--host", dest="hostname")
    export.add_argument("--source")
    export.add_argument("--severity")
    export.add_argument("--start", dest="start_timestamp")
    export.add_argument("--end", dest="end_timestamp")
    import_command = commands.add_parser("import", help="import canonical JSONL events")
    import_command.add_argument("path", type=Path)
    import_command.add_argument("--dry-run", action="store_true")
    integrity = commands.add_parser("integrity", help="audit or repair event storage")
    integrity.add_argument("--repair", action="store_true")
    integrity.add_argument("--quarantine-path", type=Path)
    retention = commands.add_parser("retention", help="plan or apply event retention")
    retention.add_argument("--max-age-days", type=float)
    retention.add_argument("--max-bytes", type=int)
    retention.add_argument("--apply", action="store_true")
    compact = commands.add_parser("compact-alerts", help="plan or compact alert history")
    compact.add_argument("--apply", action="store_true")
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
                "event_uid", "hostname", "process_name", "user", "event_id", "source",
                "severity", "start_timestamp", "end_timestamp", "limit", "sort_order", "cursor",
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
            name: getattr(args, name) for name in ("hostname", "severity", "status", "priority")
            if getattr(args, name) is not None
        }
        return service.search_alerts(**filters)
    if args.command == "hosts":
        if args.detail:
            if not args.hostname:
                raise ValueError("--detail requires a hostname")
            return service.get_host_detail(args.hostname, recent_limit=args.recent_limit)
        return service.get_host(args.hostname) if args.hostname else service.list_hosts()
    if args.command == "summary":
        filters = {
            name: getattr(args, name)
            for name in ("hostname", "start_timestamp", "end_timestamp", "limit")
            if getattr(args, name) is not None
        }
        return service.operational_summary(**filters)
    if args.command == "export":
        filters = {
            name: getattr(args, name)
            for name in ("hostname", "source", "severity", "start_timestamp", "end_timestamp")
            if getattr(args, name) is not None
        }
        return service.export_events(args.path, **filters)
    if args.command == "import":
        return service.import_events(args.path, dry_run=args.dry_run)
    if args.command == "integrity":
        return service.repair_storage(args.quarantine_path) if args.repair else service.audit_storage()
    if args.command == "retention":
        options = {"max_age_days": args.max_age_days, "max_bytes": args.max_bytes}
        return service.apply_retention(**options) if args.apply else service.plan_retention(**options)
    if args.command == "compact-alerts":
        return service.compact_alerts() if args.apply else service.plan_alert_compaction()
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
