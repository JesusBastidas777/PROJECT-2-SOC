"""Small local playbooks expressed only as descriptive guidance."""


GENERIC_PLAYBOOK = {
    "validate": (
        "Review the alert evidence and confirm that the activity is unexpected.",
        "A false positive should be excluded before containment is considered.",
    ),
    "collect_evidence": (
        "Preserve relevant event, process, user, and host context for the investigation.",
        "Collect evidence before changes can remove useful context.",
    ),
    "contain": (
        "Consider isolating the host after validating the impact and operational risk.",
        "Isolation may interrupt legitimate workloads and requires operator approval.",
    ),
    "recover": (
        "Plan recovery only after the cause and affected scope have been established.",
        "Premature recovery can hide persistence or reintroduce the issue.",
    ),
    "escalate": (
        "Escalate to a human owner when evidence is incomplete or business impact is unclear.",
        "Higher-impact decisions require accountable human review.",
    ),
}


PLAYBOOKS = {
    "sensitive_process_execution": {
        "validate": (
            "Confirm whether execution of the sensitive administrative tool was authorized.",
            "Administrative tools can be legitimate but also carry elevated risk.",
        ),
        "collect_evidence": (
            "Review the process ancestry, user identity, command context, and nearby host events.",
            "Process context helps distinguish administration from misuse.",
        ),
    },
    "office_spawned_command_interpreter": {
        "validate": (
            "Validate whether the Office application was expected to launch a command interpreter.",
            "Unusual parent-child execution may originate from documents or automation.",
        ),
        "collect_evidence": (
            "Preserve the Office process chain, user context, and related document metadata.",
            "The originating document and process ancestry may explain the activity.",
        ),
    },
}
