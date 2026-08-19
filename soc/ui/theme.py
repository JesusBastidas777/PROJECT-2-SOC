TITLE = "#808000"
INFO = "yellow"
HEALTHY = "green"
CRITICAL = "red"
MUTED = "grey62"


def status_style(value):
    value = str(value or "unknown").lower()
    if value in {"healthy", "success", "clear", "ready", "low"}:
        return HEALTHY
    if value in {"critical", "high", "high_risk", "p1", "p2", "degraded"}:
        return CRITICAL
    if value in {"unknown", "unavailable", "none", "not observed"}:
        return MUTED
    return INFO
