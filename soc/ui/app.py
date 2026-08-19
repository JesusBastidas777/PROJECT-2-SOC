import os
import time
from datetime import datetime, timezone

from soc import FOREXWorkflow
from soc.ui.errors import describe_error
from soc.ui.navigation import normalize_view
from soc.ui.rendering import build_shell
from soc.ui.state import UIState


class SOCApplication:
    def __init__(self, service, *, view="overview", refresh_seconds=15, max_rows=20):
        self.service = service
        self.workflow = FOREXWorkflow(service)
        self.view = normalize_view(view)
        if refresh_seconds <= 0:
            raise ValueError("refresh_seconds must be positive")
        self.refresh_seconds = float(refresh_seconds)
        self.max_rows = max(1, min(int(max_rows), 100))

    def collect(self):
        updated = datetime.now(timezone.utc).isoformat()
        if self.view == "overview":
            from soc.ui.screens.overview import render_overview
            response = self.service.command_center(limit=self.max_rows)
            center = response.data["command_center"]
            return UIState(view=self.view, payload=render_overview(center, self.max_rows),
                           status=response.status, updated_at=center.get("generated_at") or updated)
        return UIState(view=self.view, updated_at=updated)

    def render(self, state):
        return build_shell(state, max_rows=self.max_rows)

    def run(self, *, once=False, console=None):
        from rich.console import Console
        console = console or Console(no_color="NO_COLOR" in os.environ, highlight=False, markup=False)
        while True:
            try:
                state = self.collect()
            except Exception as error:
                state = UIState(view=self.view, status="degraded", error=describe_error(error)["message"])
            console.print(self.render(state))
            if once:
                return 0
            time.sleep(self.refresh_seconds)


def run_ui(service, **options):
    try:
        return SOCApplication(service, **{k: v for k, v in options.items() if k not in {"once", "console"}}).run(
            once=options.get("once", False), console=options.get("console")
        )
    except KeyboardInterrupt:
        return 0
