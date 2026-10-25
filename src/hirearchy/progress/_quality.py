"""The quality view (0b): the tasks a blocked result holds runs on, and those left blocked (4.5), pure over what ``mail`` reads; and
``DerivedQualityReport``, which puts a view together from the records, the task states, the budgets, the FAIL counts and ORG.md and renders it."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..kernel import JsonObject, Message, OrgError, clip_line, latest_results
from ..mail import MailboxReader, TaskQuery, moved_past
from ..reflection import CaseRecords, QualityThresholds, ServiceRecord, quality_thresholds
from ._ports import ConfigSource, FailCounts, TaskStates, TaskTeams
from ._quality_facts import HeldTask, MovedPast, QualityView, RecordView, verifiers
from ._quality_render import quality_data, quality_text
from .api import QualityReport

SERVICE_CHARS = 80  # the longest service name `quality` accepts
ERROR_CHARS = 200  # characters of an exception's words in the view
ORG_MD_UNREADABLE = "ORG.md cannot be read (its settings block does not parse): the default thresholds are used."


def held_tasks(tasks: Sequence[Message], latest: Mapping[str, Message], received: Sequence[Message]) -> list[Message]:
    """The tasks of ``tasks`` (the assignee's tasks whose latest result is ``blocked``) that ``mail.moved_past`` does not release (pure): the ones
    ``budget_to_return`` holds the assignee's runs on. ``latest`` maps a task id to its latest result; ``received`` is what the assignee received."""
    return [t for t in tasks if (blocked := latest.get(t.id)) is not None and not moved_past(t, blocked, received)]


def _chain(task: Message, received: Sequence[Message]) -> set[str]:
    """The ids of the tasks the sender of ``task`` sent the assignee that are connected to it through ``revises``, in both directions, ``task`` itself
    included: the chain of ``mail.moved_past`` (the same closure, kept here because ``mail`` does not publish it)."""
    mine = [t for t in received if t.type == "task" and t.sender == task.sender]
    chain = {task.id}
    grown = True
    while grown:
        more = {t.id for t in mine if t.revises in chain} | {t.revises for t in mine if t.id in chain and t.revises}
        grown = not more <= chain
        chain |= more
    return chain


def left_blocked(task: Message, blocked: Message, received: Sequence[Message]) -> int:
    """How many tasks the sender of the held ``task`` has sent its assignee since ``blocked`` (the task's latest result), outside the task's chain
    (pure): 0 when none, otherwise the task is left blocked, "moved past without a verdict" in the gate's words (4.5)."""
    chain = _chain(task, received)
    return sum(1 for t in received if t.type == "task" and t.sender == task.sender and t.id > blocked.id and t.id not in chain)


def blocked_listing(tasks: Sequence[Message], latest: Mapping[str, Message], received: Sequence[Message]) -> tuple[HeldTask, ...]:
    """The held tasks of one agent, oldest block first, when at least one of them is left blocked; else none (pure). The moved-past section lists an
    agent with every task it holds, because while any exists its later results return no runs (4.5)."""
    held = sorted(
        (HeldTask(t, latest[t.id], left_blocked(t, latest[t.id], received)) for t in held_tasks(tasks, latest, received)), key=lambda h: h.blocked.id,
    )
    return tuple(held) if any(h.left_blocked for h in held) else ()


def service_name(service: str | None) -> str | None:
    """The service a call asks for (13, 14): stripped, ``None`` when empty; an ``OrgError`` for a name of more than 80 characters."""
    name = (service or "").strip()
    if len(name) > SERVICE_CHARS:
        raise OrgError(f"service is a service name (at most {SERVICE_CHARS} characters): {clip_line(name, SERVICE_CHARS)}")
    return name or None


class DerivedQualityReport(QualityReport):
    """The quality view over the records of the cases, the states of the open tasks, the budgets the held tasks hold, the FAIL counts of the signers
    and ORG.md's thresholds. Everything is read again per call and nothing is stored or written. A part that cannot be read reads ``unknown`` with the
    error's words; the records that cannot be built are lines of the view (13)."""

    def __init__(
        self, records: CaseRecords, states: TaskStates, teams: TaskTeams, tasks: TaskQuery, mail: MailboxReader, budgets: BudgetQuery,
        agents: AgentDirectory, fails: FailCounts, config: ConfigSource,
    ) -> None:
        self._records = records
        self._states = states
        self._teams = teams
        self._tasks = tasks
        self._mail = mail
        self._budgets = budgets
        self._agents = agents
        self._fails = fails
        self._config = config

    def quality_text(self, service: str | None = None) -> str:
        return quality_text(self._view(service))

    def quality_data(self, service: str | None = None) -> JsonObject:
        return quality_data(self._view(service))

    def _view(self, service: str | None) -> QualityView:
        name = service_name(service)
        records = self._records.records(name)
        thresholds, notes = self._thresholds()
        moved = self._moved_past()
        left = frozenset(h.task.id for m in moved for h in m.tasks if h.left_blocked)
        return QualityView(thresholds, notes, tuple(self._record_view(r, left) for r in records), moved, name)

    def _thresholds(self) -> tuple[QualityThresholds, tuple[str, ...]]:
        try:
            config = self._config.config()
        except (OrgError, OSError):  # ORG.md does not parse: the defaults, and the user is told
            return QualityThresholds(), (ORG_MD_UNREADABLE,)
        return quality_thresholds(config)

    def _record_view(self, record: ServiceRecord, left: frozenset[str]) -> RecordView:
        if record.error or record.client_kind != "human":  # a nested service is one line of counts
            return RecordView(record, left_blocked=left)
        stalled, stalled_error = self._stalled(record)
        fails: dict[str, tuple[int, int]] = {}
        errors: dict[str, str] = {}
        for v in verifiers(record):
            try:
                fails[v.addr] = self._fails.fails(v.addr)
            except (OrgError, OSError) as exc:
                errors[v.addr] = clip_line(str(exc), ERROR_CHARS)
        return RecordView(record, stalled, stalled_error, left, fails, errors)

    def _stalled(self, record: ServiceRecord) -> tuple[dict[str, bool], str]:
        """Which open cases are stalled now (`TaskStates`: the state starts with ``stalled (``), or why that is unknown."""
        try:
            return {
                c.id: self._states.state_of(c.tasks[-1], c.result, self._teams.team_of(c.tasks[-1])).state.startswith("stalled (")
                for c in record.cases if c.state == "open"
            }, ""
        except (OrgError, OSError) as exc:
            return {}, clip_line(str(exc), ERROR_CHARS)

    def _moved_past(self) -> tuple[MovedPast, ...]:
        out: list[MovedPast] = []
        for addr in self._agents.agents():
            try:
                blocked = self._tasks.blocked_tasks(addr)
                if not blocked:
                    continue
                received = self._mail.received(addr)
                listing = blocked_listing(blocked, latest_results(self._mail.sent(addr)), received)
            except (OrgError, OSError) as exc:
                out.append(MovedPast(addr, None, error=clip_line(str(exc), ERROR_CHARS)))
                continue
            if not listing:
                continue
            try:
                held = self._budgets.budget(addr)
                out.append(MovedPast(addr, held, "" if held is not None else "no budget is derived for it", tasks=listing))
            except (OrgError, OSError) as exc:
                out.append(MovedPast(addr, None, clip_line(str(exc), ERROR_CHARS), tasks=listing))
        return tuple(out)
