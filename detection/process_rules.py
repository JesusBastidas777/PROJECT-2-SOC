SENSITIVE_PROCESSES = {
    "mimikatz.exe",
    "procdump.exe",
    "psexec.exe",
}

OFFICE_PROCESSES = {
    "excel.exe",
    "outlook.exe",
    "powerpnt.exe",
    "winword.exe",
}

COMMAND_INTERPRETERS = {
    "cmd.exe",
    "cscript.exe",
    "powershell.exe",
    "pwsh.exe",
    "wscript.exe",
}


def _detection(rule_name, reason, severity, event):

    return {
        "rule_name": rule_name,
        "reason": reason,
        "severity": severity,
        "event": event,
    }


def evaluate_process_rules(event):

    process_name = (event.get("process_name") or "").lower()
    parent_process = (event.get("parent_process") or "").lower()
    detections = []

    if process_name in SENSITIVE_PROCESSES:

        detections.append(_detection(
            "sensitive_process_execution",
            f"Sensitive process executed: {process_name}",
            "high",
            event,
        ))

    if parent_process in OFFICE_PROCESSES and process_name in COMMAND_INTERPRETERS:

        detections.append(_detection(
            "office_spawned_command_interpreter",
            f"Office process {parent_process} started {process_name}",
            "high",
            event,
        ))

    if str(event.get("severity") or "").lower() == "high":

        detections.append(_detection(
            "source_reported_high_severity",
            "The event source marked this event as high severity",
            "high",
            event,
        ))

    return detections
