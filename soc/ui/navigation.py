from soc.ui import VIEWS


def normalize_view(value):
    candidate = str(value or "overview").lower()
    if candidate not in VIEWS:
        raise ValueError(f"unknown SOC UI view: {value}")
    return candidate


def next_view(current, offset=1):
    current = normalize_view(current)
    return VIEWS[(VIEWS.index(current) + offset) % len(VIEWS)]
