"""In-memory fakes of the ``blueprint`` ports, the harnesses and the registry the contract suites iterate over.

``MemoryRoleLibrary`` obeys the same contract suite as the real ``PackagedRoleLibrary``, so a consumer's unit test may use it instead of the
``roles/`` directory. ``MemoryTextFiles`` stands for the disk under a ``YamlBlueprintLoader``; ``StaticOrgContext`` is the organization a
blueprint is planned against; ``ScriptedConfinementPolicy`` is what kiro would answer. The validator is made of pure rules over those ports,
so it has no fake of its own: its harnesses differ in the role library and in the organization they are given."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Protocol

from ..agents import AgentDirectory
from ..agents.testing import MemoryAgents
from ..dispatch import TaskAssigner
from ..hierarchy import Hiring, Retired, Retirement
from ..kernel import NAME_RE, JsonObject, Message, OrgError, child_addr
from ..kernel.testing import DictEnvironment
from ..kiro import ConfinementPolicy
from ..kiro.testing import kiro_confinement
from ..services import ContractNormalizer, ServiceCommands
from ..services.testing import normalizer as contract_normalizer
from ..settings import DEFAULT_CONFIG
from ..snapshots import OrgSnapshotter
from ._access import PolicyAccessReport
from ._assembly import PlanParts, applier_over, plan_parts
from ._budgeting import BudgetPlanner
from ._files import FsTextFiles
from ._loader import YamlBlueprintLoader
from ._org import NoOrgContext, PresentOrAbsentOrg
from ._pathcheck import RootedPathChecker
from ._protocols import AccessReport, AgentResolution, OrgContext, PathChecking, ServiceRules, TextFiles, WorkspaceRoots
from ._provision import FsWorkspaceProvisioner
from ._resolver import AgentResolver
from ._roles import PackagedRoleLibrary
from ._roots import EnvironmentWorkspaceRoots
from ._service_rules import ServiceBlueprintRules
from ._validator import RuleBlueprintValidator
from .api import (
    BlueprintApplier,
    BlueprintExamples,
    BlueprintLoader,
    BlueprintValidator,
    PlanIdentity,
    PlanRenderer,
    Role,
    RoleLibrary,
    SummaryText,
    WorkspaceProvisioner,
)

PURE = {"IssueText", "SummaryText", "PlanIdentity", "BlueprintExamples"}  # data with one derived view / a pure function of its argument: one implementation, no fake

PACKAGED_ROLES = Path(__file__).resolve().parent.parent / "roles"  # the role templates that ship with hirearchy


# ------------------------------------------------------------------------------ fakes


class MemoryRoleLibrary(RoleLibrary):
    def __init__(self, roles: Sequence[Role] = ()) -> None:
        self._roles = {r.name: r for r in roles}

    def put(self, role: Role) -> None:
        self._roles[role.name] = role

    def role_names(self) -> list[str]:
        return sorted(self._roles)

    def get_role(self, name: str) -> Role | None:
        return self._roles.get(name) if NAME_RE.fullmatch(name) else None


class MemoryTextFiles(TextFiles):
    """Files kept in a dictionary; ``reads`` lists every path that was read, in order."""

    def __init__(self, files: Mapping[Path, str] | None = None) -> None:
        self.files: dict[Path, str] = dict(files or {})
        self.reads: list[Path] = []

    def is_file(self, path: Path) -> bool:
        return path in self.files

    def read(self, path: Path) -> str:
        self.reads.append(path)
        return self.files[path]


class StaticOrgContext(OrgContext):
    """An organization that is a few facts: its settings over the defaults, its directory, its top-level agents and the services it already offers."""

    def __init__(
        self, root: Path | None = None, config: Mapping[str, object] | None = None, agents: Sequence[str] = (), services: Sequence[str] = (),
    ) -> None:
        self._root = root
        self._config: JsonObject = {**DEFAULT_CONFIG, **(config or {})}
        self._agents = set(agents)
        self._services = set(services)

    def config(self) -> JsonObject:
        return dict(self._config)

    def root(self) -> Path | None:
        return self._root

    def exists(self, addr: str) -> bool:
        return addr in self._agents

    def service_names(self) -> set[str]:
        return set(self._services)


class ScriptedConfinementPolicy(ConfinementPolicy):
    """A confinement policy that answers the same ``toolsSettings`` whatever it is asked, and records what it was asked."""

    def __init__(self, settings: Mapping[str, object] | None = None) -> None:
        self.settings: dict[str, object] = dict(settings or {})
        self.calls: list[tuple[Path, list[str], Path | None, list[Path]]] = []

    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        self.calls.append((org_root, list(tools), workspace, list(inputs)))
        return list(tools), dict(self.settings)


class MemoryWorkspaceProvisioner(WorkspaceProvisioner):
    """Directories kept in a set. ``occupied`` are directories that hold a file, so that they cannot be removed."""

    def __init__(self, existing: Sequence[Path] = (), occupied: Sequence[Path] = ()) -> None:
        self.dirs: set[Path] = {Path("/"), *existing, *(parent for path in existing for parent in path.parents)}
        self.occupied: set[Path] = set(occupied)
        self.removed: list[Path] = []

    def ensure(self, path: Path) -> list[Path]:
        missing = [q for q in (path, *path.parents) if q not in self.dirs]
        self.dirs.update(missing)
        return missing

    def remove_if_empty(self, path: Path) -> bool:
        if path not in self.dirs or path in self.occupied or any(d != path and path in d.parents for d in self.dirs):
            return False
        self.dirs.discard(path)
        self.removed.append(path)
        return True


class Call(NamedTuple):
    """One call to a port of an application: its name, positional and keyword arguments."""

    name: str
    args: tuple[object, ...]
    kwargs: Mapping[str, object]


class CallRecording(Protocol):
    """What the recording ports need of the log they write to."""

    def add(self, name: str, *args: object, **kwargs: object) -> None:
        """Note a call."""
        ...

    def names(self) -> list[str]:
        """The names of the calls so far, in order."""
        ...

    def of(self, name: str) -> list[Call]:
        """The calls of this name, in order."""
        ...


class CallLog(CallRecording):
    """The calls to the recording ports of one application, in order."""

    def __init__(self) -> None:
        self.calls: list[Call] = []

    def add(self, name: str, *args: object, **kwargs: object) -> None:
        self.calls.append(Call(name, args, kwargs))

    def names(self) -> list[str]:
        return [c.name for c in self.calls]

    def of(self, name: str) -> list[Call]:
        return [c for c in self.calls if c.name == name]


class RecordingHiring(Hiring):
    """Hires into a ``MemoryAgents``: the agent exists the moment it is hired (a name that is taken is refused, like the real rules)."""

    def __init__(self, agents: MemoryAgents, log: CallRecording) -> None:
        self._agents = agents
        self._log = log

    def hire(
        self, actor: str, name: str, role: str, charter: str, *, model: str | None = None, tools: Sequence[str] | None = None,
        can_hire: bool = False, max_children: int = 5, workspace: str | None = None, inputs: Sequence[str] | None = None,
    ) -> str:
        addr = child_addr(actor, name)
        self._log.add("hire", actor, name, role, charter, model=model, tools=tools, can_hire=can_hire, max_children=max_children,
                      workspace=workspace, inputs=inputs)
        if self._agents.exists(addr):
            raise OrgError(f"{addr} already exists")
        self._agents.create(addr, {"role": role}, charter)
        return addr


class RecordingRetirement(Retirement):
    def __init__(self, agents: MemoryAgents, log: CallRecording) -> None:
        self._agents = agents
        self._log = log

    def retire(self, actor: str, name: str, reason: str) -> str:
        return self.retire_team(actor, name, reason).addr

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        self._log.add("retire", actor, name, reason)
        if not self._agents.exists(name):
            raise OrgError(f"no such agent: {name}")
        self._agents.archive(name, "stamp")
        return Retired(name, 0, None)


class RecordingTaskAssigner(TaskAssigner):
    def __init__(self, log: CallRecording) -> None:
        self._log = log

    def delegate(
        self, actor: str, to: str, title: str, goal: str, acceptance: str, inputs: Sequence[str] | None = None, budget: int | None = None,
        revises: str | None = None,
    ) -> Message:
        self._log.add("delegate", actor, to, title, goal, acceptance, inputs, budget, revises)
        return Message(actor, to, "task", goal, title=title, budget=budget or 0, id=f"task-{len(self._log.of('delegate'))}")


class RecordingServiceCommands(ServiceCommands):
    def __init__(self, log: CallRecording) -> None:
        self._log = log

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs: object = None, acceptance: object = None,
        deliverable: Mapping[str, object] | None = None, budget: int | None = None, playbook: str | None = None, locked: bool | None = None,
        notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None,
    ) -> str:
        self._log.add("define_service", actor, owner, name, description=description, inputs=inputs, acceptance=acceptance,
                      deliverable=deliverable, budget=budget, playbook=playbook, locked=locked)
        return f"defined {name}"

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        raise OrgError("an application does not retire services")

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
        extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
    ) -> Message:
        self._log.add("request", actor, service, inputs, title=title, note=note)
        return Message(actor, "lead", "task", "", title=title, budget=22, service=service, id=f"request-{len(self._log.of('request'))}")

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        raise OrgError("an application does not revise playbooks")

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        raise OrgError("an application gives no feedback")


class RecordingSnapshots(OrgSnapshotter):
    def __init__(self, log: CallRecording) -> None:
        self._log = log

    def init_repository(self) -> None:
        self._log.add("init_repository")

    def commit(self, message: str) -> None:
        self._log.add("commit", message)


class FailureSchedule(Protocol):
    def check(self) -> None:
        """Count a call; raise the error if it is the one that fails."""
        ...


class _Nth(FailureSchedule):
    """Counts the calls of one kind and says which one fails (1-based); ``None``: none."""

    def __init__(self, fail_on: int | None, error: str) -> None:
        self._fail_on = fail_on
        self._error = error
        self.calls = 0

    def check(self) -> None:
        self.calls += 1
        if self.calls == self._fail_on:
            raise OrgError(self._error)


class FlakyHiring(Hiring):
    """The hiring port that fails the ``fail_on``-th hire (1-based) with an ``OrgError`` and does the others through ``inner``."""

    def __init__(self, inner: Hiring, fail_on: int, error: str = "disk full") -> None:
        self._inner = inner
        self._nth = _Nth(fail_on, error)

    def hire(
        self, actor: str, name: str, role: str, charter: str, *, model: str | None = None, tools: Sequence[str] | None = None,
        can_hire: bool = False, max_children: int = 5, workspace: str | None = None, inputs: Sequence[str] | None = None,
    ) -> str:
        self._nth.check()
        return self._inner.hire(actor, name, role, charter, model=model, tools=tools, can_hire=can_hire, max_children=max_children,
                                workspace=workspace, inputs=inputs)


class FlakyTaskAssigner(TaskAssigner):
    """The task port that fails the ``fail_on``-th delegation (1-based, the first by default)."""

    def __init__(self, inner: TaskAssigner, fail_on: int = 1, error: str = "delegate failed") -> None:
        self._inner = inner
        self._nth = _Nth(fail_on, error)

    def delegate(
        self, actor: str, to: str, title: str, goal: str, acceptance: str, inputs: Sequence[str] | None = None, budget: int | None = None,
        revises: str | None = None,
    ) -> Message:
        self._nth.check()
        return self._inner.delegate(actor, to, title, goal, acceptance, inputs, budget, revises)


class FlakyServiceCommands(ServiceCommands):
    """The service port that fails the ``fail_define_on``-th definition and/or the ``fail_request_on``-th request (1-based)."""

    def __init__(self, inner: ServiceCommands, fail_define_on: int | None = None, fail_request_on: int | None = None, error: str = "disk full") -> None:
        self._inner = inner
        self._define = _Nth(fail_define_on, error)
        self._request = _Nth(fail_request_on, error)

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs: object = None, acceptance: object = None,
        deliverable: Mapping[str, object] | None = None, budget: int | None = None, playbook: str | None = None, locked: bool | None = None,
        notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None,
    ) -> str:
        self._define.check()
        return self._inner.define_service(
            actor, owner, name, description=description, inputs=inputs, acceptance=acceptance, deliverable=deliverable, budget=budget,
            playbook=playbook, locked=locked, notes=notes, add_acceptance=add_acceptance, remove_acceptance=remove_acceptance,
        )

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        return self._inner.retire_service(actor, owner, name, reason)

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
        extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
    ) -> Message:
        self._request.check()
        return self._inner.request(actor, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance, budget=budget, revises=revises)

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        return self._inner.revise_playbook(actor, service, content, reason)

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        return self._inner.feedback(actor, task_id, verdict, note)


# ------------------------------------------------------------------------------ the parts, made over fakes or over the real ports


def role_library_of(*, packaged: bool) -> RoleLibrary:
    """The role templates that ship with hirearchy: read from ``roles/`` or, as a fake, kept in memory."""
    real = PackagedRoleLibrary(PACKAGED_ROLES)
    if packaged:
        return real
    return MemoryRoleLibrary([role for name in real.role_names() if (role := real.get_role(name)) is not None])


def access_over(policy: ConfinementPolicy | None = None) -> AccessReport:
    return PolicyAccessReport(policy or kiro_confinement(Path()))


def paths_over(environment: DictEnvironment) -> PathChecking:
    return RootedPathChecker(environment)


def roots_over(environment: DictEnvironment, temp_dir: Path) -> WorkspaceRoots:
    return EnvironmentWorkspaceRoots(environment, lambda: temp_dir)


def resolver_over(roles: RoleLibrary, paths: PathChecking) -> AgentResolution:
    return AgentResolver(roles, paths)


def service_rules_over(normalizer: ContractNormalizer, paths: PathChecking) -> ServiceRules:
    return ServiceBlueprintRules(normalizer, paths, BudgetPlanner())


def validator_of(
    roles: RoleLibrary, org: OrgContext, *, environment: DictEnvironment, temp_dir: Path, policy: ConfinementPolicy | None = None,
) -> BlueprintValidator:
    """The validator over the given role library and organization, with the real rules and the real kiro confinement policy (unless one is given)."""
    paths = paths_over(environment)
    return RuleBlueprintValidator(
        resolver_over(roles, paths), paths, BudgetPlanner(), access_over(policy), service_rules_over(contract_normalizer(temp_dir), paths),
        roots_over(environment, temp_dir), PresentOrAbsentOrg(org, NoOrgContext()),
    )


def plan_parts_over(
    roles: RoleLibrary, org: OrgContext, *, environment: DictEnvironment, temp_dir: Path, policy: ConfinementPolicy | None = None,
) -> PlanParts:
    """The plan side over the given role library and organization, with the real rules, the real kiro policy (unless one is given) and the real
    contract normalizer."""
    paths, budgets, access = paths_over(environment), BudgetPlanner(), access_over(policy)
    normalizer = contract_normalizer(temp_dir)
    resolver, roots = resolver_over(roles, paths), roots_over(environment, temp_dir)
    validator = RuleBlueprintValidator(
        resolver, paths, budgets, access, service_rules_over(normalizer, paths), roots, PresentOrAbsentOrg(org, NoOrgContext()),
    )
    return plan_parts(YamlBlueprintLoader(FsTextFiles()), validator, resolver, roots, budgets, access, normalizer, org)


class AgentsOrgContext(OrgContext):
    """The organization of an application test: the agents that exist are the ones in a ``MemoryAgents``."""

    def __init__(self, root: Path, agents: AgentDirectory) -> None:
        self._root = root
        self._agents = agents

    def config(self) -> JsonObject:
        return dict(DEFAULT_CONFIG)

    def root(self) -> Path | None:
        return self._root

    def exists(self, addr: str) -> bool:
        return self._agents.exists(addr)

    def service_names(self) -> set[str]:
        return set()


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class RoleHarness:
    library: RoleLibrary
    put: Callable[[Role], None]  # a role template with exactly these values (the packaged one: its ``roles/<name>.md`` file)


@dataclass(frozen=True)
class LoaderHarness:
    loader: BlueprintLoader
    put_file: Callable[[Path, str], None]  # a file with this text, where the loader looks for files
    reads: Callable[[], list[Path]]  # the files the loader has read so far, in order
    directory: Path  # a directory where files can be put


@dataclass(frozen=True)
class ValidatorHarness:
    validator: BlueprintValidator
    roles: RoleLibrary
    environment: DictEnvironment  # the process the validator runs in (home, working directory)
    tmp: Path  # the only allowed root of the blueprints of the suites
    put_org: Callable[[StaticOrgContext], BlueprintValidator]  # the same kind of validator over this organization (``org_exists=True``)


def _role_text(role: Role) -> str:
    tools = "[" + ", ".join(role.tools) + "]"
    return (f"---\ntitle: {role.title}\nkind: {role.kind}\ntier: {role.tier}\ntools: {tools}\nbase_runs: {role.base_runs}\n"
            f"summary: {role.summary}\n---\n{role.body}\n")


def packaged_roles(tmp_path: Path) -> RoleHarness:
    directory = tmp_path / "roles"
    directory.mkdir()

    def put(role: Role) -> None:
        (directory / f"{role.name}.md").write_text(_role_text(role), encoding="utf-8")

    return RoleHarness(PackagedRoleLibrary(directory), put)


def memory_roles(tmp_path: Path) -> RoleHarness:
    fake = MemoryRoleLibrary()
    return RoleHarness(fake, fake.put)


def loader_over_memory(tmp_path: Path) -> LoaderHarness:
    files = MemoryTextFiles()
    return LoaderHarness(YamlBlueprintLoader(files), lambda path, text: files.files.__setitem__(path, text), lambda: list(files.reads), tmp_path)


def loader_over_disk(tmp_path: Path) -> LoaderHarness:
    reads: list[Path] = []

    class RecordingFiles(FsTextFiles):
        def read(self, path: Path) -> str:
            reads.append(path)
            return super().read(path)

    def put(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return LoaderHarness(YamlBlueprintLoader(RecordingFiles()), put, lambda: list(reads), tmp_path)


def _validator_harness(tmp_path: Path, packaged: bool) -> ValidatorHarness:
    environment = DictEnvironment(home=tmp_path, cwd=tmp_path)
    roles = role_library_of(packaged=packaged)

    def over(org: StaticOrgContext) -> BlueprintValidator:
        return validator_of(roles, org, environment=environment, temp_dir=tmp_path / "temp")

    return ValidatorHarness(over(StaticOrgContext()), roles, environment, tmp_path, over)


def validator_over_packaged_roles(tmp_path: Path) -> ValidatorHarness:
    return _validator_harness(tmp_path, packaged=True)


def validator_over_memory_roles(tmp_path: Path) -> ValidatorHarness:
    return _validator_harness(tmp_path, packaged=False)


@dataclass(frozen=True)
class RendererHarness:
    renderer: PlanRenderer
    tmp: Path  # the only allowed root of the blueprints of the suites
    put_org: Callable[[StaticOrgContext], PlanRenderer]  # the same kind of renderer over this organization (it exists: its names are taken)


def _renderer_harness(tmp_path: Path, packaged: bool) -> RendererHarness:
    environment = DictEnvironment(home=tmp_path, cwd=tmp_path)
    roles = role_library_of(packaged=packaged)

    def over(org: StaticOrgContext) -> PlanRenderer:
        return plan_parts_over(roles, org, environment=environment, temp_dir=tmp_path / "temp").renderer

    return RendererHarness(over(StaticOrgContext()), tmp_path, over)


def renderer_over_packaged_roles(tmp_path: Path) -> RendererHarness:
    return _renderer_harness(tmp_path, packaged=True)


def renderer_over_memory_roles(tmp_path: Path) -> RendererHarness:
    return _renderer_harness(tmp_path, packaged=False)


@dataclass(frozen=True)
class ApplierHarness:
    """An application over recording ports: what it asked of them is in ``log``, the agents it hired are in ``agents``."""

    applier: BlueprintApplier
    log: CallLog
    agents: MemoryAgents
    provisioner: WorkspaceProvisioner
    tmp: Path  # the only allowed root of the blueprints of the suites
    dir_exists: Callable[[Path], bool]  # a directory exists in the world of the provisioner
    with_ports: Callable[..., BlueprintApplier]  # the same application, some ports replaced: ``hiring=``, ``tasks=``, ``commands=`` (the recording ones are passed in)
    ports: "RecordingPorts"


@dataclass(frozen=True)
class RecordingPorts:
    hiring: Hiring
    retirement: Retirement
    tasks: TaskAssigner
    commands: ServiceCommands


def _applier_harness(tmp_path: Path, provisioner: WorkspaceProvisioner, dir_exists: Callable[[Path], bool]) -> ApplierHarness:
    environment = DictEnvironment(home=tmp_path, cwd=tmp_path)
    agents, log = MemoryAgents(), CallLog()
    org = AgentsOrgContext(tmp_path / "org", agents)
    plan = plan_parts_over(role_library_of(packaged=True), org, environment=environment, temp_dir=tmp_path / "temp")
    ports = RecordingPorts(RecordingHiring(agents, log), RecordingRetirement(agents, log), RecordingTaskAssigner(log), RecordingServiceCommands(log))
    snapshots, normalizer = RecordingSnapshots(log), contract_normalizer(tmp_path / "temp")

    def build(hiring: Hiring | None = None, tasks: TaskAssigner | None = None, commands: ServiceCommands | None = None) -> BlueprintApplier:
        return applier_over(plan, BudgetPlanner(), normalizer, hiring or ports.hiring, ports.retirement, agents, commands or ports.commands,
                            tasks or ports.tasks, snapshots, provisioner)

    return ApplierHarness(build(), log, agents, provisioner, tmp_path, dir_exists, build, ports)


def applier_over_memory_directories(tmp_path: Path) -> ApplierHarness:
    dirs = MemoryWorkspaceProvisioner(existing=[tmp_path])
    return _applier_harness(tmp_path, dirs, lambda path: path in dirs.dirs)


def applier_over_disk_directories(tmp_path: Path) -> ApplierHarness:
    return _applier_harness(tmp_path, FsWorkspaceProvisioner(), lambda path: path.exists())


@dataclass(frozen=True)
class ProvisionerHarness:
    provisioner: WorkspaceProvisioner
    base: Path  # a directory that exists
    exists: Callable[[Path], bool]
    put_file: Callable[[Path], None]  # a file in this directory (which must exist): the directory is no longer empty


def provisioner_on_disk(tmp_path: Path) -> ProvisionerHarness:
    def put(directory: Path) -> None:
        (directory / "file.txt").write_text("x", encoding="utf-8")

    return ProvisionerHarness(FsWorkspaceProvisioner(), tmp_path, lambda path: path.exists(), put)


def provisioner_in_memory(tmp_path: Path) -> ProvisionerHarness:
    fake = MemoryWorkspaceProvisioner(existing=[tmp_path])
    return ProvisionerHarness(fake, tmp_path, lambda path: path in fake.dirs, lambda directory: fake.occupied.add(directory))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    RoleLibrary: [packaged_roles, memory_roles],
    BlueprintLoader: [loader_over_memory, loader_over_disk],
    BlueprintValidator: [validator_over_packaged_roles, validator_over_memory_roles],
    PlanRenderer: [renderer_over_packaged_roles, renderer_over_memory_roles],
    BlueprintApplier: [applier_over_memory_directories, applier_over_disk_directories],
    WorkspaceProvisioner: [provisioner_on_disk, provisioner_in_memory],
}
