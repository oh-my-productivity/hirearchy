"""In-memory fakes of the ``blueprint`` ports, the harnesses and the registry the contract suites iterate over.

``MemoryRoleLibrary`` obeys the same contract suite as the real ``PackagedRoleLibrary``, so a consumer's unit test may use it instead of the
``roles/`` directory. ``MemoryTextFiles`` stands for the disk under a ``YamlBlueprintLoader``; ``StaticOrgContext`` is the organization a
blueprint is planned against; ``ScriptedConfinementPolicy`` is what kiro would answer. The validator is made of pure rules over those ports,
so it has no fake of its own: its harnesses differ in the role library and in the organization they are given."""
from __future__ import annotations
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from ..kernel import NAME_RE, JsonObject
from ..kernel.testing import DictEnvironment
from ..kiro import ConfinementPolicy
from ..kiro.testing import kiro_confinement
from ..services import ContractNormalizer
from ..services.testing import normalizer as contract_normalizer
from ..settings import DEFAULT_CONFIG
from ._access import PolicyAccessReport
from ._budgeting import BudgetPlanner
from ._files import FsTextFiles
from ._loader import YamlBlueprintLoader
from ._org import NoOrgContext, PresentOrAbsentOrg
from ._pathcheck import RootedPathChecker
from ._protocols import AccessReport, AgentResolution, OrgContext, PathChecking, ServiceRules, TextFiles, WorkspaceRoots
from ._resolver import AgentResolver
from ._roles import PackagedRoleLibrary
from ._roots import EnvironmentWorkspaceRoots
from ._service_rules import ServiceBlueprintRules
from ._validator import RuleBlueprintValidator
from .api import BlueprintLoader, BlueprintValidator, Role, RoleLibrary
PURE = {"IssueText"}  # data with one derived view (``Issue.render``): one implementation, no fake

PACKAGED_ROLES = Path(__file__).resolve().parent.parent / 'roles'

class MemoryRoleLibrary(RoleLibrary):

    def __init__(self, roles: Sequence[Role]=()) -> None:
        self._roles = {r.name: r for r in roles}

    def put(self, role: Role) -> None:
        raise NotImplementedError('red: C-blueprint-1')

    def role_names(self) -> list[str]:
        raise NotImplementedError('red: C-blueprint-1')

    def get_role(self, name: str) -> Role | None:
        raise NotImplementedError('red: C-blueprint-1')

class MemoryTextFiles(TextFiles):
    """Files kept in a dictionary; ``reads`` lists every path that was read, in order."""

    def __init__(self, files: Mapping[Path, str] | None=None) -> None:
        self.files: dict[Path, str] = dict(files or {})
        self.reads: list[Path] = []

    def is_file(self, path: Path) -> bool:
        raise NotImplementedError('red: C-blueprint-1')

    def read(self, path: Path) -> str:
        raise NotImplementedError('red: C-blueprint-1')

class StaticOrgContext(OrgContext):
    """An organization that is a few facts: its settings over the defaults, its directory, its top-level agents and the services it already offers."""

    def __init__(self, root: Path | None=None, config: Mapping[str, object] | None=None, agents: Sequence[str]=(), services: Sequence[str]=()) -> None:
        self._root = root
        self._config: JsonObject = {**DEFAULT_CONFIG, **(config or {})}
        self._agents = set(agents)
        self._services = set(services)

    def config(self) -> JsonObject:
        raise NotImplementedError('red: C-blueprint-1')

    def root(self) -> Path | None:
        raise NotImplementedError('red: C-blueprint-1')

    def exists(self, addr: str) -> bool:
        raise NotImplementedError('red: C-blueprint-1')

    def service_names(self) -> set[str]:
        raise NotImplementedError('red: C-blueprint-1')

class ScriptedConfinementPolicy(ConfinementPolicy):
    """A confinement policy that answers the same ``toolsSettings`` whatever it is asked, and records what it was asked."""

    def __init__(self, settings: Mapping[str, object] | None=None) -> None:
        self.settings: dict[str, object] = dict(settings or {})
        self.calls: list[tuple[Path, list[str], Path | None, list[Path]]] = []

    def file_confinement(self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]) -> tuple[list[str], dict[str, object]]:
        raise NotImplementedError('red: C-blueprint-1')

def role_library_of(*, packaged: bool) -> RoleLibrary:
    """The role templates that ship with orgmcp: read from ``roles/`` or, as a fake, kept in memory."""
    real = PackagedRoleLibrary(PACKAGED_ROLES)
    if packaged:
        return real
    return MemoryRoleLibrary([role for name in real.role_names() if (role := real.get_role(name)) is not None])

def access_over(policy: ConfinementPolicy | None=None) -> AccessReport:
    return PolicyAccessReport(policy or kiro_confinement(Path()))

def paths_over(environment: DictEnvironment) -> PathChecking:
    return RootedPathChecker(environment)

def roots_over(environment: DictEnvironment, temp_dir: Path) -> WorkspaceRoots:
    return EnvironmentWorkspaceRoots(environment, lambda: temp_dir)

def resolver_over(roles: RoleLibrary, paths: PathChecking) -> AgentResolution:
    return AgentResolver(roles, paths)

def service_rules_over(normalizer: ContractNormalizer, paths: PathChecking) -> ServiceRules:
    return ServiceBlueprintRules(normalizer, paths, BudgetPlanner())

def validator_of(roles: RoleLibrary, org: OrgContext, *, environment: DictEnvironment, temp_dir: Path, policy: ConfinementPolicy | None=None) -> BlueprintValidator:
    """The validator over the given role library and organization, with the real rules and the real kiro confinement policy (unless one is given)."""
    paths = paths_over(environment)
    return RuleBlueprintValidator(resolver_over(roles, paths), paths, BudgetPlanner(), access_over(policy), service_rules_over(contract_normalizer(temp_dir), paths), roots_over(environment, temp_dir), PresentOrAbsentOrg(org, NoOrgContext()))

@dataclass(frozen=True)
class RoleHarness:
    library: RoleLibrary
    put: Callable[[Role], None]

@dataclass(frozen=True)
class LoaderHarness:
    loader: BlueprintLoader
    put_file: Callable[[Path, str], None]
    reads: Callable[[], list[Path]]
    directory: Path

@dataclass(frozen=True)
class ValidatorHarness:
    validator: BlueprintValidator
    roles: RoleLibrary
    environment: DictEnvironment
    tmp: Path
    put_org: Callable[[StaticOrgContext], BlueprintValidator]

def _role_text(role: Role) -> str:
    tools = '[' + ', '.join(role.tools) + ']'
    return f'---\ntitle: {role.title}\nkind: {role.kind}\ntier: {role.tier}\ntools: {tools}\nbase_runs: {role.base_runs}\nsummary: {role.summary}\n---\n{role.body}\n'

def packaged_roles(tmp_path: Path) -> RoleHarness:
    directory = tmp_path / 'roles'
    directory.mkdir()

    def put(role: Role) -> None:
        (directory / f'{role.name}.md').write_text(_role_text(role), encoding='utf-8')
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
        path.write_text(text, encoding='utf-8')
    return LoaderHarness(YamlBlueprintLoader(RecordingFiles()), put, lambda: list(reads), tmp_path)

def _validator_harness(tmp_path: Path, packaged: bool) -> ValidatorHarness:
    environment = DictEnvironment(home=tmp_path, cwd=tmp_path)
    roles = role_library_of(packaged=packaged)

    def over(org: StaticOrgContext) -> BlueprintValidator:
        return validator_of(roles, org, environment=environment, temp_dir=tmp_path / 'temp')
    return ValidatorHarness(over(StaticOrgContext()), roles, environment, tmp_path, over)

def validator_over_packaged_roles(tmp_path: Path) -> ValidatorHarness:
    return _validator_harness(tmp_path, packaged=True)

def validator_over_memory_roles(tmp_path: Path) -> ValidatorHarness:
    return _validator_harness(tmp_path, packaged=False)
IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {RoleLibrary: [packaged_roles, memory_roles], BlueprintLoader: [loader_over_memory, loader_over_disk], BlueprintValidator: [validator_over_packaged_roles, validator_over_memory_roles]}
