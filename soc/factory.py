"""Construct independent SOC component graphs from configuration."""

from dataclasses import dataclass

from investigation.event_search import EventSearch
from investigation.investigation_service import InvestigationService
from normalization.event_normalizer import EventNormalizer
from soc.config import SOCConfig
from storage.event_reader import EventReader
from storage.event_store import EventStore


@dataclass
class SOCComponents:
    config: SOCConfig
    reader: EventReader
    store: EventStore
    normalizer: EventNormalizer
    search: EventSearch
    investigation: InvestigationService


def build_components(config=None):
    config = config or SOCConfig.from_env()
    reader = EventReader(config.events_path)
    return SOCComponents(
        config=config,
        reader=reader,
        store=EventStore(config.events_path),
        normalizer=EventNormalizer(),
        search=EventSearch(reader),
        investigation=InvestigationService(reader),
    )
