"""The reviewer over an organization on disk and over memory, and the registry the contract suites iterate over.

``ReviewWorld`` is what a test gets of the reviewer: the reviewer itself and the means to prepare an organization (agents, their health, budgets, pause
flags, delegations, run logs, ORG.md) behind the ports it reads, and to look at what it did (the notes delivered, the ledger, the events). The health of
the agents is what a test puts in (``FixedHealthAnalyzer``: this package reviews a report, it does not measure one), the budgets are numbers
(``FixedBudget``), the rest is real: over disk the reviewer reads the mailboxes, the run logs, the flag files and the ledger of a directory; over
memory it reads the in-memory ports with a ``FakeClock`` that only moves when told. The same suites run over both (``tests/test_contract_*.py``), so a
consumer's unit test may use the memory world.

``ScriptedHealthReviewer`` is the stand-in for the reviewer itself, for the consumers that only decide *when* to review or print its result
(``scheduler``, ``cli``): a test puts in the reviews it wants answered and reads which calls were made.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path

from ..agents import AgentDirectory, CharterReader, RetiredArchive
from ..agents.testing import fs_agents
from ..budget.testing import FixedBudget
from ..delivery.testing import DeliveryHarness, fs_pipeline, memory_pipeline
from ..eligibility.testing import PauseHarness, fs_pauses, memory_pauses
from ..health import AgentHealth
from ..health.testing import FixedHealthAnalyzer
from ..kernel import RUNTIME, JsonObject, LedgerStore, Message, OrgPaths
from ..kernel.testing import FakeClock, ListEventSink, MemoryLedgerStore, fs_ledger_store
from ..mail.testing import MemoryMailbox
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ..settings.testing import SettingsHarness, fs_org_settings, memory_org_settings
from ..templates import Notices
from ..templates.testing import static_notices
from ._cadence import LedgerReviewCadence
from ._ledger import StoreReviewLedger
from ._outbox import DeliveryNoteOutbox
from ._planner import HealthReviewPlanner
from ._reserve import BudgetReserveCheck
from ._reviewer import LedgerHealthReviewer
from ._runs import ArchivedRunTotal
from .api import HealthReviewer, Review

PURE = {"ReviewReport"}  # data with one derived view (``render``): one implementation, no fake

ORG_MD = "---\nmission: test\n---\nrules\n"  # the ORG.md every world starts with: no review_every_*, so the defaults (25 runs, a day)


def org_md(**settings: float | str) -> str:
    """An ORG.md that sets these top-level keys (``review_every_runs=5``, ...)."""
    block = "".join(f"{name}: {value}\n" for name, value in settings.items())
    return f"---\nmission: test\n{block}---\nrules\n"


def healthy(addr: str) -> AgentHealth:
    """The health of an agent with nothing to report: no flag."""
    return AgentHealth(
        addr=addr, depth=addr.count("/") + 1, state="idle", budget_left=10, budget_received=10, runs_used=0, tasks_received=0, open_tasks=0,
        oldest_open_age=None, done=0, failed=0, blocked=0, runs_per_task=None, rework=0, empty_runs=0, last_activity=None, since_activity=None,
    )


# ------------------------------------------------------------------------------ the fake of the reviewer itself


class ScriptedHealthReviewer(HealthReviewer):
    """Answers with the reviews a test put in. ``calls`` keeps what it was asked, in order: ``("review", now, dry_run)``,
    ``("review_if_due", now, False)``, ``("total_runs", None, False)``, ``("read_ledger", None, False)``."""

    calls: list[tuple[str, datetime | None, bool]]

    def __init__(self, review: Review, due: Review | None = None, runs: int = 0, ledger: JsonObject | None = None) -> None:
        self._review = review
        self._due = due
        self._runs = runs
        self._ledger = ledger
        self.calls = []

    def review(self, now: datetime | None = None, dry_run: bool = False) -> Review:
        self.calls.append(("review", now, dry_run))
        return self._review

    def review_if_due(self, now: datetime) -> Review | None:
        self.calls.append(("review_if_due", now, False))
        return self._due

    def total_runs(self) -> int:
        self.calls.append(("total_runs", None, False))
        return self._runs

    def read_ledger(self) -> JsonObject | None:
        self.calls.append(("read_ledger", None, False))
        return self._ledger


# ------------------------------------------------------------------------------ the worlds


@dataclass(frozen=True)
class ReviewWorld:
    """The reviewer over one organization, and the means to prepare it and to look at what it did. Addresses: ``ceo``, ``ceo/eng``, ...; root exists."""

    reviewer: HealthReviewer
    clock: FakeClock  # the reviewer's and the delivery's; it moves only when told (plus a microsecond per reading)
    events: ListEventSink  # what the reviewer emitted
    notices: Notices  # the wording the notes are made of
    health: FixedHealthAnalyzer  # what the analyzer says about each agent
    ledgers: LedgerStore  # the ledger store behind the reviewer
    hire: Callable[[str, int], None]  # (addr, budget): the agent exists, with this many runs left and nothing to report
    flag: Callable[[str, str, str], None]  # (addr, flag, reason): the analyzer says the agent has this flag
    heal: Callable[[str], None]  # the analyzer says the agent has no flag
    pause: Callable[[str, str], None]  # (addr, reason): the agent is paused
    resume: Callable[[str], None]  # the agent is no longer paused
    set_budget: Callable[[str, int], None]  # the agent has this many runs left
    delegate: Callable[[str, str], Message]  # (sender, to): a task sent and not answered (it counts as an outstanding delegation of the sender)
    add_runs: Callable[[str, int], None]  # (addr, n): the agent has made n more runs
    add_retired_runs: Callable[[int], None]  # n more run logs inside the retired trees
    configure: Callable[[str], None]  # ORG.md becomes this text (``org_md(...)``)
    notes: Callable[[str], list[Message]]  # the notes of the runtime the address has received, in order
    ledger_text: Callable[[], str | None]  # the text of ``.runtime/reviews.json``, None when there is none
    put_ledger_text: Callable[[str], None]  # arbitrary text in the ledger
    delivered: Callable[[], int]  # how many messages of the runtime were delivered in all


def _world(
    tmp_path: Path, pipeline: DeliveryHarness, directory: AgentDirectory, charters: CharterReader, archive: RetiredArchive, pauses: PauseHarness,
    runs: RunsHarness, settings: SettingsHarness, ledgers: LedgerStore, ledger_text: Callable[[], str | None], put_ledger_text: Callable[[str], None],
    put_file: Callable[[str, str], None],
) -> ReviewWorld:
    mail = pipeline.mail
    assert mail is not None
    clock, events, notices = pipeline.clock, ListEventSink(), static_notices()
    settings.put(ORG_MD)
    budgets = FixedBudget(mail.tasks, directory, charters)
    health = FixedHealthAnalyzer(directory, clock)
    total = ArchivedRunTotal(directory, runs.reader, archive)
    ledger = StoreReviewLedger(ledgers)
    reviewer = LedgerHealthReviewer(
        HealthReviewPlanner(directory, health, BudgetReserveCheck(pauses.store, budgets, mail.tasks), notices, total), ledger, total,
        LedgerReviewCadence(ledger, total, settings.settings), DeliveryNoteOutbox(pipeline.delivery), events, clock,
    )
    logs = {"n": 0}

    def hire(addr: str, budget: int) -> None:
        mail.agent(addr)
        pauses.agent(addr)
        runs.add_agent(addr)
        budgets.held[addr] = budget
        health.put(healthy(addr))

    def flag(addr: str, name: str, reason: str) -> None:
        current = health.agent_health(addr)
        health.put(replace(current, flags={**current.flags, name: reason}))

    def heal(addr: str) -> None:
        health.put(replace(health.agent_health(addr), flags={}))

    def delegate(sender: str, to: str) -> Message:
        return pipeline.delivery.deliver(Message(sender=sender, to=to, type="task", title="Job", body="goal", budget=1))

    def add_runs(addr: str, n: int) -> None:
        for _ in range(n):
            logs["n"] += 1
            runs.put_log(addr, f"20260101T{logs['n']:012d}.log", "")

    def add_retired_runs(n: int) -> None:
        for _ in range(n):
            logs["n"] += 1
            put_file(f".retired/ceo-S/runs/20260101T{logs['n']:012d}.log", "x")

    def notes(addr: str) -> list[Message]:
        return [m for m in mail.reader.received(addr) if m.sender == RUNTIME]

    def delivered() -> int:
        return sum(len(notes(a)) for a in ["root", *directory.agents()])

    return ReviewWorld(
        reviewer, clock, events, notices, health, ledgers, hire, flag, heal, pauses.store.pause, lambda addr: pauses.store.resume(addr),
        lambda addr, n: budgets.held.__setitem__(addr, n), delegate, add_runs, add_retired_runs, settings.put, notes, ledger_text, put_ledger_text,
        delivered,
    )


def fs_world(tmp_path: Path) -> ReviewWorld:
    """The reviewer over an organization directory."""
    disk, ledgers = fs_agents(tmp_path), fs_ledger_store(tmp_path)
    file = OrgPaths(tmp_path).ledger_file("reviews")
    return _world(
        tmp_path, fs_pipeline(tmp_path), disk.directory, disk.charters, disk.archive, fs_pauses(tmp_path), fs_runs(tmp_path), fs_org_settings(tmp_path),
        ledgers.store, lambda: file.read_text(encoding="utf-8") if file.is_file() else None, lambda raw: ledgers.put_raw("reviews", raw), disk.put,
    )


def memory_world(tmp_path: Path) -> ReviewWorld:
    """The reviewer over the in-memory ports."""
    pipeline = memory_pipeline(tmp_path)
    box = pipeline.mail.reader if pipeline.mail is not None else None
    assert isinstance(box, MemoryMailbox)
    ledgers = MemoryLedgerStore()
    return _world(
        tmp_path, pipeline, box.agents, box.agents, box.agents, memory_pauses(tmp_path), memory_runs(tmp_path), memory_org_settings(tmp_path),
        ledgers, lambda: ledgers.texts.get("reviews"), lambda raw: ledgers.texts.__setitem__("reviews", raw), box.agents.put,
    )


def later(world: ReviewWorld, seconds: float) -> datetime:
    """The time ``seconds`` after the origin of the clock of the world."""
    return world.clock.origin + timedelta(seconds=seconds)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    HealthReviewer: [fs_world, memory_world],
}
