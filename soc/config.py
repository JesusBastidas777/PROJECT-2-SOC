"""Central, immutable runtime configuration."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _path(value: str, base_dir: Path) -> Path:
    candidate = Path(value).expanduser()
    return candidate if candidate.is_absolute() else base_dir / candidate


@dataclass(frozen=True)
class SOCConfig:
    base_dir: Path = PROJECT_ROOT
    events_path: Optional[Path] = None
    alerts_path: Optional[Path] = None
    timeline_limit: int = 10
    lock_timeout: float = 5.0
    search_limit_max: int = 500

    def __post_init__(self):
        base_dir = Path(self.base_dir).expanduser().resolve()
        object.__setattr__(self, "base_dir", base_dir)
        object.__setattr__(
            self, "events_path",
            _path(str(self.events_path or "storage/event_logs/events.jsonl"), base_dir),
        )
        object.__setattr__(
            self, "alerts_path",
            _path(str(self.alerts_path or "storage/alert_logs/alerts.jsonl"), base_dir),
        )
        if self.timeline_limit <= 0:
            raise ValueError("timeline_limit must be positive")
        if self.lock_timeout < 0:
            raise ValueError("lock_timeout must not be negative")
        if self.search_limit_max <= 0:
            raise ValueError("search_limit_max must be positive")

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None, **overrides):
        values = os.environ if env is None else env
        base_dir = Path(overrides.pop("base_dir", values.get("SOC_BASE_DIR", PROJECT_ROOT)))
        settings = {
            "base_dir": base_dir,
            "events_path": overrides.pop("events_path", values.get("SOC_EVENTS_PATH")),
            "alerts_path": overrides.pop("alerts_path", values.get("SOC_ALERTS_PATH")),
            "timeline_limit": overrides.pop(
                "timeline_limit", int(values.get("SOC_TIMELINE_LIMIT", "10"))
            ),
            "lock_timeout": overrides.pop(
                "lock_timeout", float(values.get("SOC_LOCK_TIMEOUT", "5"))
            ),
            "search_limit_max": overrides.pop(
                "search_limit_max", int(values.get("SOC_SEARCH_LIMIT_MAX", "500"))
            ),
        }
        if overrides:
            raise TypeError("unknown configuration: " + ", ".join(sorted(overrides)))
        return cls(**settings)
