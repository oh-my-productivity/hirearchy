"""Small rules of the commands: who an owner is, what a playbook text may be, how a playbook is written."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import ROOT, Clock, EventSink, OrgError, child_addr, norm, split_frontmatter
from ..settings import OrgSettings
from ._cap import playbook_word_cap
from ._protocols import OwnerAddresses, PlaybookTexts, PlaybookWriter
from .api import ServiceStore


class DirectReportOwners(OwnerAddresses):
    """A manager may name a direct report by its short name; root names agents by their full address."""

    def __init__(self, agents: AgentDirectory) -> None:
        self._agents = agents

    def resolve(self, actor: str, owner: str) -> str:
        raise NotImplementedError


class CappedPlaybookTexts(PlaybookTexts):
    """A playbook is a non-empty body within ``playbook_max_words`` of the settings."""

    def __init__(self, settings: OrgSettings) -> None:
        self._settings = settings

    def body(self, content: str | None) -> str:
        raise NotImplementedError


class EventedPlaybookWriter(PlaybookWriter):
    """Writes a playbook version through the store and records ``service.revise``."""

    def __init__(self, store: ServiceStore, clock: Clock, events: EventSink) -> None:
        self._store = store
        self._clock = clock
        self._events = events

    def write(self, owner: str, name: str, version: int, body: str, by: str, reason: str, archive_version: int | None = None) -> str:
        raise NotImplementedError
