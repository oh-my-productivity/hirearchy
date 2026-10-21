"""The traces over the mailboxes on disk and over the in-memory ones: what the contract suites iterate over.

There is no fake of ``traces`` of its own: the lookup and the stamper are pure logic over a ``MailboxReader`` (ARCHITECTURE.md 3.14), so the
fake is the in-memory mailboxes of ``mail.testing``. ``TraceHarness`` is what a test gets: the lookup, the stamper built on it, and the
mailbox harness to prepare and inspect files behind their back.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import ROOT, norm
from ..mail.testing import MailHarness, fs_mailbox, memory_mailbox
from ._lookup import MailboxTraceLookup
from ._ports import AgentPresence
from ._stamper import RuleTraceStamper
from .api import TraceLookup, TraceStamper


class CharterPresence(AgentPresence):
    """An address is an agent when its ``AGENT.md`` is there (root always is): read through the means of a mailbox harness."""

    def __init__(self, read: Callable[[str], str | None]) -> None:
        self._read = read

    def exists(self, addr: str) -> bool:
        a = norm(addr)
        return a == ROOT or self._read(f"{a}/AGENT.md") is not None


@dataclass(frozen=True)
class TraceHarness:
    """The ports of ``traces`` over one organization, and the means to prepare and inspect its files behind their back."""

    lookup: TraceLookup
    stamper: TraceStamper
    mail: MailHarness


def _over(mail: MailHarness) -> TraceHarness:
    lookup = MailboxTraceLookup(mail.reader, CharterPresence(mail.read))
    return TraceHarness(lookup, RuleTraceStamper(lookup), mail)


def fs_traces(tmp_path: Path) -> TraceHarness:
    return _over(fs_mailbox(tmp_path))


def memory_traces(tmp_path: Path) -> TraceHarness:
    return _over(memory_mailbox(tmp_path))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    TraceLookup: [fs_traces, memory_traces],
    TraceStamper: [fs_traces, memory_traces],
}
