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
        short = norm(owner)
        if "/" in short or norm(actor) == ROOT or self._agents.exists(short):
            return short
        return child_addr(actor, short)


class CappedPlaybookTexts(PlaybookTexts):
    """A playbook is a non-empty body within ``playbook_max_words`` of the settings."""

    def __init__(self, settings: OrgSettings) -> None:
        self._settings = settings

    def body(self, content: str | None) -> str:
        text = (content or "").replace("\r\n", "\n")
        body = (split_frontmatter(text)[1] if text.startswith("---\n") else text).strip()
        if not body:
            raise OrgError("the playbook is empty: write the workflow (steps: who does what, in which order, which check)")
        cap, words = playbook_word_cap(self._settings.config()), len(body.split())
        if words > cap:
            raise OrgError(
                f"the playbook is {words} words; the limit is {cap} (playbook_max_words). Condense it to the steps that "
                "matter and move detail into a file under your work/ directory."
            )
        return body


class EventedPlaybookWriter(PlaybookWriter):
    """Writes a playbook version through the store and records ``service.revise``."""

    def __init__(self, store: ServiceStore, clock: Clock, events: EventSink) -> None:
        self._store = store
        self._clock = clock
        self._events = events

    def write(self, owner: str, name: str, version: int, body: str, by: str, reason: str, archive_version: int | None = None) -> str:
        meta = {"service": name, "version": version, "revised": self._clock.now().isoformat(timespec="microseconds"), "by": by, "reason": reason}
        path = self._store.write_playbook(owner, name, version, meta, body, archive_version)
        self._events.emit("service.revise", actor=by, owner=owner, service=name, version=version, by=by)
        return path
