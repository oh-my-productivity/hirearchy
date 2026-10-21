"""The features a command uses, as fakes that keep every call they are given (``calls``: name, arguments) and answer what a test said: the ports of the
members and the mail of the organization (``FakeOffice``), of its services (``FakeServices``), of what it shows (``FakeReadings``), of the mail and the agents
(``FakeMail``), of the blueprints (``FakeBlueprints``), of its upkeep (``FakeUpkeep``) and of the views of the observability (``FakeViews``).
Every call of a fake may be made to fail with ``refuse`` (an ``OrgError``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from hirearchy.agents import AgentDirectory
from hirearchy.blueprint import BlueprintApplier, BlueprintLoader, BlueprintValidator, Issue, PlanRenderer, Summary
from hirearchy.bootstrap import OrgInitializer
from hirearchy.daemon import SchedulerState, SchedulerStatus
from hirearchy.dashdata import SnapshotRenderer
from hirearchy.dispatch import MessageSender, TaskAssigner
from hirearchy.eligibility import FailureCounter, PauseStore
from hirearchy.health import AgentHealth, HealthAnalyzer, HealthRenderer, OrgHealth
from hirearchy.hierarchy import Hiring
from hirearchy.kernel import JsonObject, Message, OrgError
from hirearchy.kiro import McpServerLocator, ProfileProvisioner
from hirearchy.mail import BatchStore, MailboxReader, TaskQuery
from hirearchy.observability import (
    EventQueries,
    IntegrityChecks,
    MetricQueries,
    NowQueries,
    ObservabilityRenderer,
    TraceQueries,
)
from hirearchy.overview import OrgTree
from hirearchy.progress import ProgressReporter
from hirearchy.reflection import ServiceReports
from hirearchy.review import HealthReviewer, Note, Review
from hirearchy.services import Contract, ContractNormalizer, Criterion, Playbook, ServiceCatalog, ServiceCommands, number_criteria
from hirearchy.skill import SkillInstaller
from hirearchy.snapshots import OrgSnapshotter
from hirearchy.upgrade import RulesUpgrader, Upgrade

Call = tuple[str, tuple[object, ...], dict[str, object]]
T0 = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)


class Recording:
    """The calls made, in order, and a way to make the next ones fail."""

    def __init__(self) -> None:
        self.calls: list[Call] = []
        self.refuse: OrgError | None = None

    def note(self, name: str, *args: object, **kwargs: object) -> None:
        self.calls.append((name, args, kwargs))
        if self.refuse is not None:
            raise self.refuse

    def names(self) -> list[str]:
        return [name for name, _, _ in self.calls]

    def last(self, name: str) -> tuple[tuple[object, ...], dict[str, object]]:
        return next((args, kwargs) for n, args, kwargs in reversed(self.calls) if n == name)


class FakeOffice(Recording, Hiring, TaskAssigner, MessageSender, OrgSnapshotter, OrgInitializer):
    """Hiring, delegating, sending, the snapshots and the initializer: a hire is ``<actor>/<name>``, a message is ``m-<n>`` to whom it was sent."""

    def __init__(self) -> None:
        super().__init__()
        self._n = 0

    def _message(self, to: str, type: str, budget: int) -> Message:
        self._n += 1
        return Message(sender="root", to=to, type=type, body="", budget=budget, id=f"m-{self._n}")

    def hire(self, actor: str, name: str, role: str, charter: str, **kwargs: object) -> str:
        self.note("hire", actor, name, role, charter, **kwargs)
        return name if actor == "root" else f"{actor}/{name}"

    def delegate(self, actor: str, to: str, title: str, goal: str, acceptance: str, inputs: Sequence[str] | None = None, budget: int | None = None,
                 revises: str | None = None, source: str | None = None) -> Message:
        self.note("delegate", actor, to, title, goal, acceptance, inputs, budget, revises, source)
        return self._message(to, "task", budget or 0)

    def send(self, actor: str, to: str, body: str, **kwargs: object) -> Message:
        self.note("send", actor, to, body, **kwargs)
        budget = kwargs.get("budget")
        return self._message(to, "note", budget if isinstance(budget, int) else 0)

    def commit(self, message: str) -> None:
        self.note("commit", message)

    def init(self, root: Path, mission: str | None = None, config: Mapping[str, object] | None = None) -> None:
        self.note("init", root, mission, config)


class FakeServices(Recording, ServiceCommands, ServiceCatalog, ContractNormalizer):
    """The service commands (answering ``done: <name>``), the catalog (``contracts``) and the normalizer (``topic*:text`` -> a spec)."""

    def __init__(self, contracts: Mapping[tuple[str, str], Contract] | None = None) -> None:
        super().__init__()
        self.contracts = dict(contracts or {})

    def define_service(self, actor: str, owner: str, name: str, **kwargs: object) -> str:
        self.note("define_service", actor, owner, name, **kwargs)
        return f"defined service `{name}` for {owner}"

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        self.note("retire_service", actor, owner, name, reason)
        return f"retired service `{name}` of {owner}"

    def request(self, actor: str, service: str, inputs: Mapping[str, object] | None, **kwargs: object) -> Message:
        self.note("request", actor, service, dict(inputs or {}), **kwargs)
        budget = kwargs.get("budget")
        return Message(sender=actor, to="ceo", type="task", body="", budget=budget if isinstance(budget, int) else 4, service=service, id="r-1")

    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
        self.note("feedback", actor, task_id, verdict, note, source=source, criterion=None if criterion is None else list(criterion), confirms=confirms)
        return Message(sender=actor, to="ceo", type="note", body="", id="f-1", source=source, criterion=", ".join(criterion) if criterion else None)

    def read_contract(self, owner: str, name: str) -> Contract | None:
        self.note("read_contract", owner, name)
        return self.contracts.get((owner, name))

    def criteria(self, owner: str, name: str) -> list[Criterion]:
        contract = self.contracts.get((owner, name))
        return number_criteria([(contract.version, contract.defined_by, contract.acceptance)]) if contract else []

    def playbook_versions(self, owner: str, name: str) -> list[Playbook]:
        return []

    def parse_input_spec(self, spec: str) -> JsonObject:
        self.note("parse_input_spec", spec)
        name, _, text = spec.partition(":")
        return {"name": name.rstrip("*"), "description": text, "required": name.endswith("*")}


class FakeReadings(Recording, OrgTree, TaskQuery, SchedulerStatus, HealthAnalyzer, HealthRenderer, ProgressReporter, ServiceReports, SnapshotRenderer):
    """What the commands that show the organization ask: each answer is a field (``outstanding``, ``scheduler_line``, ...)."""

    def __init__(self) -> None:
        super().__init__()
        self.outstanding_tasks: list[Message] = []
        self.scheduler_line = "scheduler: stopped"

    def tree(self) -> str:
        self.note("tree")
        return "root (human): unread 0, delegated 0"

    def outstanding(self, addr: str) -> list[Message]:
        self.note("outstanding", addr)
        return list(self.outstanding_tasks)

    def describe(self) -> str:
        self.note("describe")
        return self.scheduler_line

    def org_health(self, root: str = "root", now: datetime | None = None) -> OrgHealth:
        self.note("org_health", root)
        return OrgHealth(root, T0, [], {})

    def render_text(self, health: OrgHealth) -> str:
        self.note("render_text", health.root)
        return f"{len(health.agents)} agents, {len(health.flagged)} flagged"

    def describe_progress(self, task_id: str | None = None, wait_seconds: int = 0) -> str:
        self.note("describe_progress", task_id, wait_seconds)
        return "progress text"

    def services_text(self, actor: str) -> str:
        self.note("services_text", actor)
        return "services text"

    def render_once(self, width: int = 110) -> str:
        self.note("render_once", width)
        return "once text"


class FakeMail(Recording, MailboxReader, BatchStore, AgentDirectory, PauseStore, FailureCounter):
    """The mail of root (``inbox``, what ``begin`` moves into flight), the agents (``agents_known``) and the pauses and failures."""

    def __init__(self) -> None:
        super().__init__()
        self.inbox: list[Message] = []
        self.known = {"ceo", "ceo/eng"}

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        self.note("messages", addr, *boxes)
        return list(self.inbox)

    def begin(self, addr: str) -> list[Message]:
        self.note("begin", addr)
        return list(self.inbox)

    def end(self, addr: str, ok: bool) -> None:
        self.note("end", addr, ok)

    def require(self, addr: str) -> str:
        self.note("require", addr)
        short = addr.strip("/")
        if short not in self.known:
            raise OrgError(f"no such agent: {addr}")
        return short

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        self.note("resume", addr, reason, by)

    def clear(self, addr: str) -> None:
        self.note("clear", addr)


class FakeBlueprints(Recording, BlueprintLoader, BlueprintValidator, PlanRenderer, BlueprintApplier):
    """A loader that answers ``{"mission": <path>}``, a validator that answers ``issues`` and a renderer that lists them."""

    def __init__(self, issues: Sequence[Issue] = ()) -> None:
        super().__init__()
        self.issues = list(issues)

    def load(self, source: object) -> JsonObject:
        self.note("load", source)
        return {"mission": str(source)}

    def validate(self, bp: Mapping[str, object], *, org_exists: bool = False, allowed_roots: Sequence[str | Path] | None = None) -> list[Issue]:
        self.note("validate", dict(bp), org_exists=org_exists, allowed_roots=allowed_roots)
        return list(self.issues)

    def render_plan(self, bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        self.note("render_plan", dict(bp), list(issues or []), allowed_roots=allowed_roots)
        return "# Plan for approval\n" + "\n".join(i.render() for i in issues or [])

    def apply(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None) -> Summary:
        self.note("apply", dict(bp), allowed_roots=allowed_roots)
        return Summary(["lead", "lead/writer"], "t-1", "lead", 10)


class FakeUpkeep(Recording, RulesUpgrader, SkillInstaller, HealthReviewer, ProfileProvisioner, McpServerLocator):
    """The upgrade of the rules, the skill, the health review, the kiro profile and where the MCP server starts."""

    def __init__(self) -> None:
        super().__init__()
        self.notes: list[Note] = []

    def upgrade_rules(self, dry_run: bool = False) -> Upgrade:
        self.note("upgrade_rules", dry_run)
        return Upgrade(True, 2, 1, ["+a", "-b"], written=not dry_run)

    def install_skill(self, dest: str | Path | None = None, force: bool = False) -> str:
        self.note("install_skill", dest, force)
        return f"{dest}/hirearchy/SKILL.md\ninstalled the hirearchy skill"

    def review(self, now: datetime | None = None, dry_run: bool = False) -> Review:
        self.note("review", now, dry_run)
        return Review(T0, 3, len(self.notes), list(self.notes))

    def profile_name(self, tools: Sequence[str]) -> str:
        return "-".join(["hirearchy", *tools])

    def ensure_profile(self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None, confine: bool = False) -> str:
        self.note("ensure_profile", list(tools))
        return self.profile_name(tools)

    def command(self) -> dict[str, object]:
        self.note("command")
        return {"command": "hirearchy", "args": ["mcp"]}


class FakeViews(Recording, NowQueries, TraceQueries, MetricQueries, EventQueries, IntegrityChecks, ObservabilityRenderer):
    """The views of the observability: each answers the dict in its field, and the renderer shows ``render_<view>: <the dict's keys>``."""

    def __init__(self) -> None:
        super().__init__()
        self.now: JsonObject = {"scheduler": "stopped"}
        self.tr: JsonObject = {"task": "t-1", "when": T0}
        self.metric: JsonObject = {"runs": 0}
        self.event_list: list[JsonObject] = [{"kind": "msg.deliver", "n": 1}, {"kind": "run.end", "n": 2}]
        self.checks: JsonObject = {"ok": True, "checks": []}

    def now_view(self, now: datetime | None = None) -> JsonObject:
        self.note("now_view")
        return dict(self.now)

    def trace(self, task_id: str, now: datetime | None = None) -> JsonObject:
        self.note("trace", task_id)
        return dict(self.tr)

    def metrics(self, since: str | datetime | None = "24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> JsonObject:
        self.note("metrics", since, by, agent=agent)
        return dict(self.metric)

    def events_view(self, since: str | datetime | None = None, until: str | datetime | None = None, agent: str | None = None, kind: str | None = None,
                    trace: str | None = None, errors: bool = False, limit: int | None = None, now: datetime | None = None) -> JsonObject:
        self.note("events_view", since, until, agent, kind, trace, errors, limit)
        return {"events": list(self.event_list), "total": len(self.event_list), "shown": len(self.event_list)}

    def check(self, now: datetime | None = None) -> JsonObject:
        self.note("check")
        return dict(self.checks)

    def render_now(self, v: JsonObject, max_lines: int | None = None) -> str:
        return f"render_now: {sorted(v)}"

    def render_trace(self, tr: JsonObject, max_lines: int | None = None) -> str:
        return f"render_trace: {sorted(tr)}"

    def render_metrics(self, m: JsonObject, limit: int = 50) -> str:
        return f"render_metrics: {sorted(m)} limit {limit}"

    def render_events(self, view: JsonObject, max_lines: int | None = None) -> str:
        return f"render_events: {sorted(view)}"

    def render_check(self, res: JsonObject) -> str:
        return f"render_check: ok={res['ok']}"


def agent_health(addr: str = "ceo") -> AgentHealth:
    return AgentHealth(addr, 1, "idle", 5, 5, 0, 0, 0, None, 0, 0, 0, None, 0, 0, None, None)


# A fake subclasses the Protocols whose methods a test uses and answers those; the others keep the empty body of the Protocol, which mypy counts as abstract.
# These are the only places that make one.


def new_office() -> FakeOffice:
    return FakeOffice()  # type: ignore[abstract]


def new_services(contracts: Mapping[tuple[str, str], Contract] | None = None) -> FakeServices:
    return FakeServices(contracts)  # type: ignore[abstract]


def new_readings() -> FakeReadings:
    return FakeReadings()  # type: ignore[abstract]


def new_mail() -> FakeMail:
    return FakeMail()  # type: ignore[abstract]


def new_blueprints(issues: Sequence[Issue] = ()) -> FakeBlueprints:
    return FakeBlueprints(issues)  # type: ignore[abstract]


def new_upkeep() -> FakeUpkeep:
    return FakeUpkeep()  # type: ignore[abstract]


def new_views() -> FakeViews:
    return FakeViews()  # type: ignore[abstract]
