import os
import time
from datetime import datetime, timezone

from soc import FOREXWorkflow
from soc.ui.errors import describe_error
from soc.ui.navigation import normalize_view
from soc.ui.rendering import build_shell
from soc.ui.state import UIState


class SOCApplication:
    def __init__(self, service, *, view="overview", refresh_seconds=15, max_rows=20,
                 selected_alert=None, priority=None, hostname=None, alert_status="open"):
        self.service = service
        self.workflow = FOREXWorkflow(service)
        self.view = normalize_view(view)
        if refresh_seconds <= 0:
            raise ValueError("refresh_seconds must be positive")
        self.refresh_seconds = float(refresh_seconds)
        self.max_rows = max(1, min(int(max_rows), 100))
        self.selected_alert, self.priority, self.hostname = selected_alert, priority, hostname
        self.alert_status = alert_status

    def collect(self):
        updated = datetime.now(timezone.utc).isoformat()
        if self.view == "overview":
            from soc.ui.screens.overview import render_overview
            response = self.service.command_center(limit=self.max_rows)
            center = response.data["command_center"]
            return UIState(view=self.view, payload=render_overview(center, self.max_rows),
                           status=response.status, updated_at=center.get("generated_at") or updated)
        if self.view == "alerts":
            from soc.ui.screens.alerts import alert_state, render_alerts
            if self.alert_status == "closed":
                alerts = self.service.search_alerts(hostname=self.hostname, priority=self.priority, status="closed").data["alerts"]
                queue = {"entries": [{"alert": item, "age_band": "closed", "attention_reason": "Closed alert"} for item in alerts], "total": len(alerts)}
            else:
                queue = self.service.attention_queue(hostname=self.hostname, priority=self.priority,
                    limit=self.max_rows, include_acknowledged=self.alert_status == "acknowledged").data["queue"]
                if self.alert_status == "acknowledged":
                    queue = {**queue, "entries": [item for item in queue["entries"] if item["alert"].status == "acknowledged"]}
            value = alert_state(queue, self.selected_alert)
            self.selected_alert = value["selected_id"]
            return UIState(view=self.view, payload=render_alerts(value, self.max_rows), updated_at=updated)
        if self.view == "hosts":
            from soc.ui.screens.hosts import render_hosts
            hosts = self.service.list_hosts().data["hosts"]
            selected = self.hostname or (hosts[0].hostname if hosts else None)
            risks = {host.hostname.casefold(): self.service.get_host_risk(host.hostname).data["risk"] for host in hosts[:self.max_rows]}
            detail = self.service.get_host_detail(selected, recent_limit=self.max_rows).data["host"] if selected else None
            risk = self.service.get_host_risk(selected).data["risk"] if selected else None
            investigation = self.service.investigate_host(selected, timeline_limit=self.max_rows).data if detail else None
            value = {"hosts": hosts, "risks": risks, "detail": detail,
                     "selected_risk": risk, "investigation": investigation}
            return UIState(view=self.view, payload=render_hosts(value, self.max_rows), updated_at=updated)
        return UIState(view=self.view, updated_at=updated)

    def transition_selected_alert(self, status):
        if not self.selected_alert:
            raise ValueError("no alert is selected")
        return self.service.transition_alert(self.selected_alert, status)

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
        app = SOCApplication(service, **{k: v for k, v in options.items() if k not in {"once", "console", "alert_action"}})
        if options.get("alert_action"):
            app.transition_selected_alert(options["alert_action"])
        return app.run(
            once=options.get("once", False), console=options.get("console")
        )
    except KeyboardInterrupt:
        return 0
