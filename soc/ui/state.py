from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UIState:
    view: str
    payload: Any = None
    status: str = "success"
    updated_at: str | None = None
    error: str | None = None
    stale: bool = False
    metadata: dict = field(default_factory=dict)
