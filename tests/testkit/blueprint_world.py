"""The blueprint tests' view of the package: the old call shapes (``bpm.validate(bp, org=org)``, ``bpm.apply(org, bp)`` ...) over the new API.

The tests of ``hirearchy.blueprint`` were written against the flat module's functions. Those functions are gone, so a
test uses this world instead. Every method here is a thin call of a port of the runtime (``org.runtime.blueprint_validator``,
``.plan_renderer``, ``.blueprint_applier`` ...) or of the private class that now owns the old function (``BudgetPlanner``, ``PolicyAccessReport``,
``AgentResolver`` ...: allowed here, ``testkit`` is not part of ``hirearchy``). The assertion text of the tests stays as it was; only their import changed::

    from testkit.blueprint_world import bpm          # was: from hirearchy import blueprint as bpm

``World(overrides)`` is the same world over a runtime that has other ports (``ConfinementPolicy`` for a profile that does not let ``read`` open the
org ...). Without an ``org`` a call runs over a runtime of an organization that does not exist (constructors do no I/O); with one, over ``org.runtime``,
so an ``Org`` whose runtime was opened with other ports (``FlakyHiring`` ...) applies through them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from hirearchy.app import wire_blueprint, wire_mcp_server
from hirearchy.app._builder import Builder
from hirearchy.app.wiring import open_runtime, providers
from hirearchy.blueprint import EXAMPLE_KINDS, Agent, BlueprintError, BlueprintLoader, BlueprintValidator, Issue, RoleLibrary, errors
from hirearchy.blueprint._assembly import PlanParts, plan_parts
from hirearchy.blueprint._access import PolicyAccessReport
from hirearchy.blueprint._accesswords import PlainAccessWords
from hirearchy.blueprint._budgeting import KINDS, REWORK_RUNS, BudgetPlanner
from hirearchy.blueprint._org import NoOrgContext, RuntimeOrgContext
from hirearchy.blueprint._pathcheck import RootedPathChecker
from hirearchy.blueprint._plan_texts import PLAN_DRAFT_HEADING, PLAN_END, PLAN_HEADING, PLAN_ID_LENGTH, PLAN_SHOW
from hirearchy.blueprint._playbooks import StepsPlaybookWriter
from hirearchy.blueprint._resolver import AgentResolver
from hirearchy.blueprint._rules import blob, edits_others_files, is_code
from hirearchy.blueprint._roots import EnvironmentWorkspaceRoots
from hirearchy.blueprint._text import clip
from hirearchy.blueprint._view import WRITE_TOOLS, is_plain, is_request
from hirearchy.kernel import Environment
from hirearchy.kiro import ConfinementPolicy
from hirearchy.services import ContractNormalizer

NO_ORG = Path("/nonexistent/hirearchy-no-org")  # a root nobody opens: the runtime of "no organization yet"
Roots = Sequence[str | Path] | None


class Examples:
    """The ready-to-edit templates (``BlueprintExamples``), by the old names ``KINDS`` and ``example``."""

    KINDS = EXAMPLE_KINDS

    def __init__(self, world: World) -> None:
        self._world = world

    def example(self, kind: str = "research", base: Path | str = ".", service: bool = False) -> str:
        return self._world.runtime().blueprint_examples.example(kind, base, service)


class Services:
    """The service reads the blueprint tests make of an organization they applied a blueprint to (``ServiceCatalog``, ``ServiceReports``)."""

    @staticmethod
    def read_contract(org, owner, name):
        return org.runtime.service_catalog.read_contract(owner, name)

    @staticmethod
    def read_playbook(org, owner, name):
        return org.runtime.service_catalog.read_playbook(owner, name)

    @staticmethod
    def services_text(org, actor):
        return org.runtime.service_reports.services_text(actor)


class World:
    # what the flat module exported besides its functions
    Agent = Agent
    BlueprintError = BlueprintError
    Issue = Issue
    PLAN_HEADING = PLAN_HEADING
    PLAN_DRAFT_HEADING = PLAN_DRAFT_HEADING
    PLAN_END = PLAN_END
    PLAN_SHOW = PLAN_SHOW
    PLAN_ID_LENGTH = PLAN_ID_LENGTH
    WRITE_TOOLS = WRITE_TOOLS
    REWORK_RUNS = REWORK_RUNS
    KINDS = KINDS
    ROLES_DIR = wire_blueprint.roles_dir()

    def __init__(self, overrides: Mapping[type, object] | None = None) -> None:
        self._overrides = dict(overrides or {})
        self.examples = Examples(self)
        self.services = Services()

    # ------------------------------------------------------------------ the runtime a call runs over
    def runtime(self, org=None):
        if org is not None and not self._overrides:
            return org.runtime
        return open_runtime(Path(org.root) if org is not None else NO_ORG, self._overrides)

    def _plan(self, org=None) -> PlanParts | None:
        """The plan side before there is an organization (``NoOrgContext``: the defaults, no name taken); None when ``org`` is given: its runtime's."""
        if org is not None:
            return None
        b = Builder(NO_ORG, self._overrides, providers())
        paths = RootedPathChecker(b.get(Environment))
        return plan_parts(
            b.get(BlueprintLoader), b.get(BlueprintValidator), AgentResolver(b.get(RoleLibrary), paths),
            EnvironmentWorkspaceRoots(b.get(Environment), wire_blueprint.temp_dir), BudgetPlanner(), PolicyAccessReport(b.get(ConfinementPolicy)),
            b.get(ContractNormalizer), NoOrgContext(),
        )

    def _renderer(self, org=None):
        parts = self._plan(org)
        return parts.renderer if parts is not None else self.runtime(org).plan_renderer

    def _access_report(self) -> PolicyAccessReport:
        return PolicyAccessReport(self.runtime().confinement_policy)

    # ------------------------------------------------------------------ roles, loading, validating
    def errors(self, issues):
        return errors(issues)

    def role_names(self):
        return self.runtime().role_library.role_names()

    def get_role(self, name):
        return self.runtime().role_library.get_role(name)

    def load(self, source):
        return self.runtime().blueprint_loader.load(source)

    def load_text(self, text):
        return self.runtime().blueprint_loader.load_text(text)

    def validate(self, bp, *, org=None, allowed_roots: Roots = None):
        return self.runtime(org).blueprint_validator.validate(bp, org_exists=org is not None, allowed_roots=allowed_roots)

    # ------------------------------------------------------------------ the plan
    def render_plan(self, bp, issues=None, *, org=None, allowed_roots: Roots = None):
        return self._renderer(org).render_plan(bp, issues, allowed_roots=allowed_roots)

    def plan_for_user(self, bp, issues=None, *, org=None, allowed_roots: Roots = None):
        return self._renderer(org).plan_for_user(bp, issues, allowed_roots=allowed_roots)

    def propose_text(self, bp, org=None, *, target: str = "", allowed_roots: Roots = None):
        return self._renderer(org).propose_text(bp, target=target, allowed_roots=allowed_roots)

    def propose(self, source, *, org=None, allowed_roots: Roots = None):
        return self._renderer(org).propose(source, allowed_roots=allowed_roots)

    def plan_id(self, bp):
        return self.runtime().plan_identity.plan_id(bp)

    def default_playbook(self, owner, agents, service, budget):
        return StepsPlaybookWriter(BudgetPlanner()).default_playbook(owner, agents, service, budget)

    # ------------------------------------------------------------------ the budget
    def estimate(self, agents):
        return dict(BudgetPlanner().estimate(agents))

    def planned_total(self, bp, est_total):
        return BudgetPlanner().planned_total(bp, est_total)

    def budget_split(self, agents, total):
        return {addr: dict(split) for addr, split in BudgetPlanner().budget_split(agents, total).items()}

    def service_budget(self, s, est_total, cap):
        return BudgetPlanner().service_budget(s, est_total, cap)

    # ------------------------------------------------------------------ what an agent may reach
    def org_files_readable(self, a):
        return self._access_report().org_files_readable(a)

    def access_facts(self, a):
        return dict(self._access_report().facts(a))

    def _access(self, a):
        return self._access_report().line(a)

    def _agent_access(self, a):
        return PlainAccessWords(self._access_report()).describe(a)

    edits_others_files = staticmethod(edits_others_files)

    # ------------------------------------------------------------------ the agents of a blueprint, and the private readings of it
    def _resolve(self, bp, org, roots, issues):
        rt = self.runtime(org)
        context = RuntimeOrgContext(rt.settings, rt.agents, rt.service_catalog, rt.paths) if org is not None else NoOrgContext()
        return AgentResolver(rt.role_library, RootedPathChecker(rt.environment)).resolve(bp, context, roots, issues)

    _plain = staticmethod(is_plain)
    _is_request = staticmethod(is_request)
    _is_code = staticmethod(is_code)
    _blob = staticmethod(blob)
    _clip = staticmethod(clip)

    # ------------------------------------------------------------------ apply
    def apply(self, org, bp, *, allowed_roots: Roots = None):
        return self.runtime(org).blueprint_applier.apply(bp, allowed_roots=allowed_roots)


bpm = World()  # the default world: the real ports of the process
ex = bpm.examples
services_mod = bpm.services


def kiro_runner():
    """``(org, addr, prompt) -> (argv, cwd, env)``: the command the scheduler would run for ``addr`` (``RunCommandBuilder``)."""

    def build(org, addr: str, prompt: str):
        command = org.runtime.run_command_builder.build(addr, prompt)
        return list(command.argv), command.cwd, dict(command.env)

    return build


def server_of_the_environment():
    """The MCP server of the identity the environment names (``ORG_ROOT``, ``ORG_AGENT`` ...): what ``hirearchy mcp`` serves."""
    binding, me = wire_mcp_server.binding_resolver().resolve()
    return wire_mcp_server.server_factory(binding).build(me)
