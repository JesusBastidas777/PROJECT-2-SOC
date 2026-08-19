from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from soc.ui.theme import INFO, MUTED, TITLE, status_style


def render_overview(center, max_rows=20):
    center = dict(center or {})
    max_rows = max(1, min(int(max_rows), 100))
    summary = Table.grid(expand=True)
    state = center.get("overall_state") or "unknown"
    summary.add_row(Text("OVERALL STATE", style=TITLE), Text(str(state).upper(), style=status_style(state)))
    health = center.get("health") or {}
    health_state = getattr(health, "state", None) or (health.get("state") if isinstance(health, dict) else None) or "unknown"
    integrity = center.get("integrity") or {}
    summary.add_row(Text("HEALTH", style=TITLE), Text(str(health_state).upper(), style=status_style(health_state)))
    summary.add_row(Text("INTEGRITY", style=TITLE), Text("DEGRADED" if integrity.get("invalid") else "HEALTHY", style=status_style("degraded" if integrity.get("invalid") else "healthy")))

    queue = center.get("attention_queue") or {}
    priorities = queue.get("totals_by_priority") or {}
    urgent = priorities.get("P1", 0) + priorities.get("P2", 0)
    summary.add_row(Text("URGENT ALERTS", style=TITLE), Text(str(urgent), style=INFO))

    def table(title, columns, rows, empty):
        result = Table(show_header=True, expand=True)
        for column in columns: result.add_column(column, style=TITLE if column == columns[0] else None)
        for row in list(rows or [])[:max_rows]: result.add_row(*[str(value if value is not None else "unknown") for value in row])
        if not rows: result.add_row(empty, *(["—"] * (len(columns) - 1)))
        return Panel(result, title=title, border_style=TITLE)

    risks = [(item.get("hostname"), item.get("score"), item.get("level")) for item in center.get("top_risk_hosts") or []]
    incidents = [(getattr(item, "incident_id", "unknown"), getattr(item, "priority", "unknown"), getattr(item, "status", "unknown")) for item in center.get("open_incidents") or []]
    stale = [(getattr(item, "incident_id", "unknown"), getattr(item, "updated_at", None)) for item in center.get("stale_incidents") or []]
    reasons = [Text(str(reason), style=INFO) for reason in (center.get("reasons") or [])[:max_rows]] or [Text("No active reasons", style=MUTED)]
    recommendations = center.get("recommendations") or []
    next_step = recommendations[0].get("recommended_next_step") if recommendations else "Continue normal monitoring."
    return Group(
        summary,
        table("TOP RISK HOSTS", ("HOST", "SCORE", "LEVEL"), risks, "No observed hosts"),
        table("OPEN INCIDENTS", ("INCIDENT", "PRIORITY", "STATUS"), incidents, "No open incidents"),
        table("STALE INCIDENTS", ("INCIDENT", "UPDATED"), stale, "No stale incidents"),
        Panel(Group(*reasons), title="REASONS", border_style=TITLE),
        Panel(Text(next_step, style=INFO), title="RECOMMENDED NEXT STEP", border_style=TITLE),
    )
