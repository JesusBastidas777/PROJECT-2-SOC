from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from soc.ui.theme import INFO, MUTED, TITLE, status_style


def alert_state(queue, selected_id=None):
    entries = list((queue or {}).get("entries") or [])
    ids = [item["alert"].alert_id for item in entries]
    selected_id = selected_id if selected_id in ids else (ids[0] if ids else None)
    selected = next((item["alert"] for item in entries if item["alert"].alert_id == selected_id), None)
    return {"entries": entries, "selected_id": selected_id, "selected": selected,
            "total": (queue or {}).get("total", len(entries))}


def render_alerts(state, max_rows=20):
    table = Table(expand=True)
    for name in ("PRIORITY", "HOST", "AGE", "STATUS", "ATTENTION REASON"):
        table.add_column(name, style=TITLE if name == "PRIORITY" else None)
    for entry in state["entries"][:max_rows]:
        alert = entry["alert"]
        age = entry.get("age_band") or "unknown"
        table.add_row(Text(alert.priority, style=status_style(alert.priority)), alert.hostname or "unknown",
                      age, alert.status or "unknown", entry.get("attention_reason") or "Attention required")
    if not state["entries"]: table.add_row("—", "—", "—", "—", "No active alerts")
    selected = state.get("selected")
    if selected:
        event = selected.event or {}
        detail = Table.grid(expand=True)
        for label, value in (("ALERT", selected.alert_id), ("RULE", selected.rule_name),
                             ("SEVERITY", selected.severity), ("EVIDENCE", event.get("evidence") or "unavailable"),
                             ("EVENT", selected.event_uid or event.get("event_uid") or "unavailable")):
            detail.add_row(Text(label, style=TITLE), Text(str(value), style=INFO))
    else:
        detail = Text("Select an alert to inspect details", style=MUTED)
    return Group(Panel(table, title="ATTENTION QUEUE", border_style=TITLE),
                 Panel(detail, title="SELECTED ALERT", border_style=TITLE))
