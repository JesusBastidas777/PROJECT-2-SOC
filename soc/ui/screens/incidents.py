from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from soc.ui.theme import CRITICAL, INFO, MUTED, TITLE, status_style


LABELS = {"validate": "VALIDATION", "collect_evidence": "EVIDENCE COLLECTION",
          "contain": "CONTAINMENT", "recover": "RECOVERY", "escalate": "ESCALATION"}


def render_incidents(state, max_rows=20):
    incidents = list(state.get("incidents") or [])[:max_rows]
    table = Table(expand=True)
    for name in ("INCIDENT", "PRIORITY", "STATUS", "HOSTS", "UPDATED"):
        table.add_column(name, style=TITLE if name == "INCIDENT" else None)
    for item in incidents:
        table.add_row(item.incident_id, Text(item.priority or "unknown", style=status_style(item.priority)),
                      item.status or "unknown", ", ".join(item.hosts or []) or "unknown", str(item.updated_at or "unknown"))
    if not incidents: table.add_row("No open incidents", "—", "—", "—", "—")
    selected = state.get("selected")
    if not selected:
        detail = Text("Select an incident to inspect details", style=MUTED)
    else:
        timeline = (state.get("timeline") or {}).get("entries") or []
        alerts = state.get("alerts") or []
        grid = Table.grid(expand=True)
        grid.add_row(Text("INCIDENT", style=TITLE), Text(selected.incident_id, style=INFO))
        grid.add_row(Text("ASSOCIATED ALERTS", style=TITLE), Text(str([getattr(a, "alert_id", "missing") if a else "missing" for a in alerts]), style=INFO))
        grid.add_row(Text("TIMELINE", style=TITLE), Text(str(timeline[:max_rows]), style=INFO))
        detail = grid
    guidance = state.get("guidance") or {}
    sections = []
    for key, label in LABELS.items():
        items = (guidance.get("recommendations") or {}).get(key) or []
        text = items[0].get("recommendation") if items else "Unavailable"
        sections.append(Panel(Text(text, style=INFO), title=label, border_style=TITLE))
    advisory = Group(Text("ADVISORY ONLY — no response is executed", style=CRITICAL), *sections)
    return Group(Panel(table, title="INCIDENTS", border_style=TITLE),
                 Panel(detail, title="INCIDENT DETAIL", border_style=TITLE),
                 Panel(advisory, title="RESPONSE GUIDANCE", border_style=CRITICAL))
