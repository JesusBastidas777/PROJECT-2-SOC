from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from soc.ui.theme import INFO, MUTED, TITLE, status_style


def render_hosts(state, max_rows=20):
    hosts = list(state.get("hosts") or [])[:max_rows]
    table = Table(expand=True)
    for name in ("HOST", "LAST SEEN", "EVENTS", "SEVERITY", "ALERTS", "RISK"):
        table.add_column(name, style=TITLE if name == "HOST" else None)
    for host in hosts:
        risk = state.get("risks", {}).get(host.hostname.casefold())
        level = getattr(risk, "level", "unknown") if risk else "unknown"
        table.add_row(host.hostname, str(host.last_seen or "unknown"), str(host.total_events),
                      host.max_severity or "unknown", str(host.open_alerts), Text(level, style=status_style(level)))
    if not hosts: table.add_row("No observed hosts", "—", "0", "unknown", "0", "unknown")
    detail = state.get("detail")
    if detail is None:
        body = Text("Host not observed. Select a host to investigate.", style=MUTED)
    else:
        risk = state.get("selected_risk")
        investigation = state.get("investigation")
        grid = Table.grid(expand=True)
        grid.add_row(Text("IDENTITY", style=TITLE), Text(detail.hostname, style=INFO))
        grid.add_row(Text("RISK", style=TITLE), Text(f"{risk.score} {risk.level}: {risk.explanation}" if risk else "unknown", style=status_style(risk.level if risk else None)))
        grid.add_row(Text("RECENT ACTIVITY", style=TITLE), Text(str(len(detail.recent_activity[:max_rows])), style=INFO))
        grid.add_row(Text("FREQUENT PROCESSES", style=TITLE), Text(str(detail.frequent_processes[:max_rows]), style=INFO))
        grid.add_row(Text("FREQUENT USERS", style=TITLE), Text(str(detail.frequent_users[:max_rows]), style=INFO))
        grid.add_row(Text("EVENTS", style=TITLE), Text(str(investigation.timeline[:max_rows] if investigation else []), style=INFO))
        grid.add_row(Text("DETECTIONS", style=TITLE), Text(str(investigation.detections[:max_rows] if investigation else []), style=INFO))
        grid.add_row(Text("CORRELATIONS", style=TITLE), Text(str(investigation.process_correlations[:max_rows] if investigation else []), style=INFO))
        body = grid
    return Group(Panel(table, title="HOST INVENTORY", border_style=TITLE),
                 Panel(body, title="INVESTIGATION", border_style=TITLE))
