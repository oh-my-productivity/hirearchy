"""The old module-level functions of ``orgmcp.blueprint``, as thin adapters over the classes of the package.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). Each builds the classes over the parts that ``orgmcp.app`` installed (``assembly_of``: the
process environment, the scheduler's confinement policy, the contract normalizer, the roles directory) and, when it is given one, over the ``Org`` it
is handed (duck-typed: a feature may not import the facade). ``apply`` also takes the ports its ``Org`` has *now* (``org.runtime``), so an ``Org`` whose
runtime was opened with other ports applies through them.

The constants of the plan and of the schema keep their old names here. ``plan_id``, ``render_plan``, ``plan_for_user``, ``propose_text``, ``propose``,
``default_playbook`` and ``apply`` ask the classes of the plan side (``_render``, ``_identity``, ``_playbooks``, ``_applier``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..kernel import JsonObject
from ._assembly import applier_of, assembly_of
from ._budgeting import KINDS as KINDS
from ._budgeting import REWORK_RUNS as REWORK_RUNS
from ._budgeting import SLACK as SLACK
from ._budgeting import TIGHT as TIGHT
from ._host import OrgFacts, OrgWithPorts
from ._plan_texts import HIDDEN_WARNINGS as HIDDEN_WARNINGS
from ._plan_texts import PLAN_DRAFT_HEADING as PLAN_DRAFT_HEADING
from ._plan_texts import PLAN_END as PLAN_END
from ._plan_texts import PLAN_HEADING as PLAN_HEADING
from ._plan_texts import PLAN_ID_LENGTH as PLAN_ID_LENGTH
from ._plan_texts import PLAN_SHOW as PLAN_SHOW
from ._plan_texts import SHOWN_CRITERIA as SHOWN_CRITERIA
from ._plan_texts import SHOWN_SERVICE_CRITERIA as SHOWN_SERVICE_CRITERIA
from ._plan_texts import SHOWN_WARNINGS as SHOWN_WARNINGS
from ._plan_texts import TOOL_WORDS as TOOL_WORDS
from ._resolver import declared_inputs as declared_inputs
from ._resolver import review_roots as review_roots
from ._rules import edits_others_files as edits_others_files
from ._text import CLIP as CLIP
from ._text import GOAL_CLIP as GOAL_CLIP
from ._view import AGENT_KEYS as AGENT_KEYS
from ._view import NEEDS_KEYS as NEEDS_KEYS
from ._view import REQUEST_KEYS as REQUEST_KEYS
from ._view import SERVICE_KEYS as SERVICE_KEYS
from ._view import TASK_KEYS as TASK_KEYS
from ._view import WEB_TOOLS as WEB_TOOLS
from ._view import WRITE_TOOLS as WRITE_TOOLS
from .api import Agent as Agent
from .api import BlueprintError as BlueprintError
from .api import Issue as Issue
from .api import Role as Role
from .api import Summary as Summary
from .api import errors as errors

ROLES_DIR = Path(__file__).parent.parent / "roles"  # where the flat module had them (``test_wire_blueprint`` pins it to the one the wiring finds)


# ------------------------------------------------------------------------------ the first half: adapters over the classes of the package


def role_names() -> list[str]:
    return assembly_of(None).roles.role_names()


def get_role(name: str) -> Role | None:
    return assembly_of(None).roles.get_role(name)


def load(source: object) -> JsonObject:
    """A blueprint from a path (``Path`` or an existing file name) or from YAML/JSON text."""
    return assembly_of(None).loader.load(source)


def load_text(text: str) -> JsonObject:
    """A blueprint from YAML/JSON text only. Never reads a file, whatever the text looks like (for text from a tool call)."""
    return assembly_of(None).loader.load_text(text)


def _resolve(bp: Mapping[str, object], org: OrgFacts | None, roots: Sequence[Path], issues: list[Issue]) -> list[Agent]:
    a = assembly_of(org)
    return a.resolver.resolve(bp, a.org, roots, issues)


def validate(bp: Mapping[str, object], *, org: OrgFacts | None = None, allowed_roots: Sequence[str | Path] | None = None) -> list[Issue]:
    """All problems with a blueprint. Errors block ``apply``; warnings are shown in the plan.

    ``org`` supplies the limits (``max_depth``) and the names already taken; ``allowed_roots`` the directories
    agents' workspaces and the deliverable path may be in (default: home, temp dir and the current directory, or
    ``$ORGMCP_WORKSPACE_ROOTS``).
    """
    return assembly_of(org).validator.validate(bp, org_exists=org is not None, allowed_roots=allowed_roots)


def org_files_readable(a: Agent) -> bool:
    """Can this agent open files in the organization (its own and its teammates' ``work/``) with the tools it holds?"""
    return assembly_of(None).access.org_files_readable(a)


def access_facts(a: Agent) -> dict[str, object]:
    """What the runtime lets this agent reach with kiro's file tools: the ONE computation behind both the technical ``Access:`` line and the plain-words one."""
    return dict(assembly_of(None).access.facts(a))


def _access(a: Agent) -> str:
    """One line on what the runtime lets this agent reach with kiro's file tools (and what it only instructs)."""
    return assembly_of(None).access.line(a)


def estimate(agents: Sequence[Agent]) -> dict[str, object]:
    """Runs one pass plus one rework cycle needs. The model behind the budget check and the budget split."""
    return dict(assembly_of(None).budgets.estimate(agents))


def planned_total(bp: Mapping[str, object], est_total: int) -> int:
    return assembly_of(None).budgets.planned_total(bp, est_total)


def budget_split(agents: Sequence[Agent], total: int) -> dict[str, dict[str, object]]:
    """addr -> {grant, keeps}: what the parent hands down at first, and what the agent keeps for itself."""
    return {addr: dict(split) for addr, split in assembly_of(None).budgets.budget_split(agents, total).items()}


def service_budget(s: Mapping[str, object], est_total: int, cap: int | None) -> int:
    """Runs handed down with each request of service ``s``: its own ``budget``, else the estimate plus slack within the cap."""
    return assembly_of(None).budgets.service_budget(s, est_total, cap)


def _svc_budgets(bp: Mapping[str, object], agents: Sequence[Agent]) -> dict[str, int]:
    return assembly_of(None).budgets.service_budgets(bp, agents)


# ------------------------------------------------------------------------------ the second half: adapters over the plan side and the applier


def default_playbook(owner: Agent, agents: Sequence[Agent], service: Mapping[str, object], budget: int) -> str:
    """Playbook v1 of a service when the blueprint gives none: the lead charter's procedure for THIS team, as steps."""
    return assembly_of(None).plan.playbooks.default_playbook(owner, agents, service, budget)


def plan_id(bp: Mapping[str, object]) -> str:
    """A short stable hash of the normalized blueprint (whatever its YAML layout, comments or key order): what ``apply_org`` requires."""
    return assembly_of(None).plan.identity.plan_id(bp)


def _agent_access(a: Agent) -> str:
    """What the agent may touch, in plain words: the same facts as the ``Access:`` line (``access_facts``)."""
    return assembly_of(None).plan.access_words.describe(a)


def render_plan(
    bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, org: OrgFacts | None = None, allowed_roots: Sequence[str | Path] | None = None,
) -> str:
    """The plan the user approves: goal, needs, org tree, budget, review, deliverable, checkpoints, warnings."""
    return assembly_of(org).plan.renderer.render_plan(bp, issues, allowed_roots=allowed_roots)


def plan_for_user(
    bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, org: OrgFacts | None = None, allowed_roots: Sequence[str | Path] | None = None,
) -> str:
    """The compact, plain-language plan the assistant shows to the user verbatim (about 40 lines at most)."""
    return assembly_of(org).plan.renderer.plan_for_user(bp, issues, allowed_roots=allowed_roots)


def propose_text(bp: Mapping[str, object], org: OrgFacts | None = None, *, target: str = "", allowed_roots: Sequence[str | Path] | None = None) -> str:
    """What ``propose_org`` returns: the block for the user, the full details and the plan_id."""
    return assembly_of(org).plan.renderer.propose_text(bp, target=target, allowed_roots=allowed_roots)


def propose(source: object, *, org: OrgFacts | None = None, allowed_roots: Sequence[str | Path] | None = None) -> str:
    """Load a blueprint (text, path or dict), validate it and return the plan text. Writes nothing."""
    return assembly_of(org).plan.renderer.propose(source, allowed_roots=allowed_roots)


def apply(org: OrgWithPorts, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None) -> Summary:
    """Create the agents (parents first, as root through each parent), define the services, and give the first task.

    The first task is a plain task, a first request for a service (``task.service``), or none (services only: they
    are ready to be requested). Refuses on any validation error or existing name, before writing anything. If a hire,
    a service definition or the delegation fails midway, everything created is retired again and the error is raised.
    """
    return applier_of(org).apply(bp, allowed_roots=allowed_roots)
