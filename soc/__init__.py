"""Stable composition layer for the SOC application."""

from soc.config import SOCConfig
from soc.models import EventQueryV1, SOCResponseV1

__all__ = [
    "EventQueryV1", "FOREXAdapter", "FOREXWorkflow", "SOCConfig", "SOCComponents",
    "SOCResponseV1", "SOCService",
    "build_components"
]


def __getattr__(name):
    if name in {"SOCComponents", "build_components"}:
        from soc.factory import SOCComponents, build_components
        return {"SOCComponents": SOCComponents, "build_components": build_components}[name]
    if name == "SOCService":
        from soc.service import SOCService
        return SOCService
    if name in {"FOREXAdapter", "FOREXWorkflow"}:
        from soc.integrations import FOREXAdapter, FOREXWorkflow
        return {"FOREXAdapter": FOREXAdapter, "FOREXWorkflow": FOREXWorkflow}[name]
    raise AttributeError(name)
