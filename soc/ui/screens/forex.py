from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from soc.ui.theme import INFO, MUTED, TITLE, status_style


def reference_targets(posture):
    references = (posture or {}).get("references") or {}
    return {"alerts": list(references.get("alert_ids") or []),
            "hosts": [posture.get("risk", {}).get("hostname")] if posture.get("risk", {}).get("hostname") else [],
            "incidents": list(references.get("incident_ids") or [])}


def render_forex(state, max_rows=20):
    posture = state.get("posture") or {}
    risk = posture.get("risk") or {}
    grid = Table.grid(expand=True)
    values = (("SCOPE", posture.get("scope")), ("STATE", posture.get("state")),
              ("OBSERVED", posture.get("observed")), ("RISK SCORE", risk.get("score")),
              ("RISK LEVEL", risk.get("level")), ("URGENT ALERTS", posture.get("urgent_alerts")),
              ("OPEN INCIDENTS", posture.get("open_incidents")),
              ("GENERATED", posture.get("generated_at")))
    for label, value in values:
        display = "not observed" if label == "OBSERVED" and value is False else (value if value is not None else "unknown")
        grid.add_row(Text(label, style=TITLE), Text(str(display), style=status_style(value) if label in {"STATE", "RISK LEVEL"} else INFO))
    reasons = posture.get("top_reasons") or []
    reason_text = "\n".join(str(item) for item in reasons[:max_rows]) or "No active reasons"
    next_step = posture.get("recommended_next_step") or "Unavailable"
    terminals = state.get("terminals") or []
    selector = ", ".join(terminals[:max_rows]) or "No observed terminals"
    targets = reference_targets(posture)
    return Group(Panel(Text(selector, style=INFO if terminals else MUTED), title="TERMINALS", border_style=TITLE),
                 Panel(grid, title="SECURITY POSTURE", border_style=TITLE),
                 Panel(Text(reason_text, style=INFO), title="TOP REASONS", border_style=TITLE),
                 Panel(Text(next_step, style=INFO), title="RECOMMENDED NEXT STEP", border_style=TITLE),
                 Panel(Text(str(targets), style=INFO), title="NAVIGATE: ALERTS · HOSTS · INCIDENTS", border_style=TITLE))
