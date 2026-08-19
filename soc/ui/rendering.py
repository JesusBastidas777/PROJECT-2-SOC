from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from soc.ui import VIEWS
from soc.ui.theme import CRITICAL, INFO, MUTED, TITLE, status_style


def build_shell(state, max_rows=20):
    """Pure, bounded renderer for a pre-collected UI state."""
    max_rows = max(1, min(int(max_rows), 100))
    nav = Table.grid(expand=True)
    for _ in VIEWS:
        nav.add_column()
    nav.add_row(*[
        Text(name.upper(), style=INFO if name == state.view else MUTED)
        for name in VIEWS
    ])
    if state.error:
        body = Panel(Text(state.error, style=CRITICAL), title="DEGRADED", border_style=CRITICAL)
    else:
        body = Panel(
            Text(f"{state.view.title()} view is ready", style=INFO),
            title=state.view.upper(), border_style=TITLE,
        )
    footer = Text(
        f"Status {state.status.upper()} | Last update {state.updated_at or 'unknown'}"
        + (" | STALE" if state.stale else ""),
        style=status_style(state.status),
    )
    return Panel(Group(nav, body, footer), title="FOREX SOC", border_style=TITLE)
