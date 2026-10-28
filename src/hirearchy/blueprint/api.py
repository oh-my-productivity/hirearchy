"""The public surface of ``blueprint``: a whole organization for one goal, as a document the user can review before anything is built.

A blueprint is a plain mapping (YAML or JSON)::

    mission: one paragraph
    needs:                      # the elicited requirements, in the user's terms
      scope: ...
      deliverable: {description, format, max_words, path}
      quality_bar: ...  sources: ...  workspace: /abs/path  budget_runs: 25
      inputs: [/abs/read-only/folder]   # read-only sources for the agents (kiro enforces: they cannot write there)
      models: {cheap: <model id>, strong: <model id>}   model_policy: ...   # optional: no models = every agent on the org default
      review: true|false|text   approval: ...   progress: ...
      kind: research|writing|code    code: {tests, packaging, commits}
    agents:                     # exactly one top-level agent (budget flows down from it)
      - {name, role, template, charter, model, tools, workspace, inputs, can_hire, max_children, scale, children: [...]}
    task: {to, title, goal, acceptance: [exact, checkable items], inputs: [...], budget}
    services:                   # optional: standing tasks the top-level agent offers (see ``hirearchy.services``)
      - {name, owner, description, inputs: [{name, description, required}], acceptance: [...],
         deliverable: {description, format, max_words, path}, budget, playbook, locked}
    # with services, ``task`` is optional; it may be a first request: {service, inputs: {...}, title, note}

The package turns text into a *checked* blueprint and a checked blueprint into an organization: ``RoleLibrary`` is the packaged role templates
(``roles/*.md``), ``BlueprintLoader`` reads a blueprint from a path, a dict or YAML/JSON text and normalizes it, ``BlueprintValidator`` lists
everything wrong with it (errors block ``apply``, warnings are shown in the plan), ``PlanRenderer`` writes the plan the user approves (and the details
for the assistant), ``PlanIdentity`` says which blueprint a plan was made for, ``BlueprintApplier`` builds the organization (and undoes it when a step
fails) and ``BlueprintExamples`` are the ready-to-edit templates. ``WorkspaceProvisioner`` is the port to the directories the plan asks for.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, OrgError

__all__ = [
    "EXAMPLE_KINDS",
    "Agent",
    "BlueprintApplier",
    "BlueprintError",
    "BlueprintExamples",
    "BlueprintLoader",
    "BlueprintValidator",
    "ExtensionApplying",
    "Issue",
    "IssueText",
    "PlanIdentity",
    "PlanRenderer",
    "Role",
    "RoleLibrary",
    "Summary",
    "SummaryText",
    "WorkspaceProvisioner",
    "errors",
    "is_extension",
    "is_verifier",
]

EXAMPLE_KINDS = ("research", "documents", "code", "analysis")  # the kinds of ready-to-edit blueprint templates


class BlueprintError(OrgError):
    pass


@runtime_checkable
class IssueText(Protocol):
    """What an issue can show of itself."""

    def render(self) -> str:
        """``<level>: <path>: <message>``."""
        ...


@dataclass(frozen=True)
class Issue(IssueText):
    level: str  # "error" blocks apply; "warning" is shown in the plan
    path: str  # where in the blueprint, e.g. "needs.deliverable" or "agents[ceo/writer]"
    message: str  # what is wrong and how to fix it
    code: str = ""  # stable short name of the rule

    def render(self) -> str:
        return f"{self.level}: {self.path}: {self.message}"


def errors(issues: Sequence[Issue]) -> list[Issue]:
    """The issues that block ``apply``."""
    return [i for i in issues if i.level == "error"]


@dataclass(frozen=True)
class Role:
    """A role template (``roles/<name>.md``): the charter text and what the role needs to do its work."""

    name: str
    title: str
    kind: str  # manager | author | verifier
    tier: str  # cheap | strong: the model tier the role needs
    tools: tuple[str, ...]
    base_runs: int  # runs for one pass of the work (managers: see the budget estimate)
    summary: str
    body: str


@dataclass
class Agent:
    """One agent of a blueprint after resolution: its address, role, tools, workspace, inputs and model."""

    addr: str
    name: str
    parent: str | None  # address of the parent; None for the top-level agent
    where: str  # issue path
    role: str = ""
    template: Role | None = None
    kind: str = "author"
    extra: str = ""  # charter text from the blueprint (appended to the template, or the whole charter)
    model: str = ""  # resolved model id (never empty once resolved: the org default fills in)
    tier: str = ""
    tools: list[str] = field(default_factory=list)
    workspace: str | None = None
    inputs: list[str] = field(default_factory=list)  # read-only paths (absolute)
    can_hire: bool = False
    max_children: int = 5
    scale: int = 1
    children: list[str] = field(default_factory=list)
    raw: JsonObject = field(default_factory=dict)

    @property
    def depth(self) -> int:
        return self.addr.count("/") + 1


@runtime_checkable
class RoleLibrary(Protocol):
    def role_names(self) -> list[str]:
        """The names of the role templates, sorted."""
        ...

    def get_role(self, name: str) -> Role | None:
        """The template ``name``; None when the name is not a valid agent name or there is no such template."""
        ...


def is_verifier(meta: Mapping[str, object], roles: RoleLibrary) -> bool:
    """Whether the agent whose AGENT.md frontmatter is ``meta`` is a verifier (a check): its stored ``kind`` is ``verifier``; an agent with no
    ``kind`` key (one from before Phase 2, or one an agent hired without a template) is a verifier when its ``role`` is the ``title`` of a
    template whose ``kind`` is ``verifier``. Any other agent is not. Pure: the one definition the extension rules, the labels and the signals use."""
    kind = meta.get("kind")
    if kind is not None:
        return kind == "verifier"
    title = meta.get("role")
    if not isinstance(title, str) or not title:
        return False
    for name in roles.role_names():
        template = roles.get_role(name)
        if template is not None and template.kind == "verifier" and template.title == title:
            return True
    return False


def is_extension(bp: object) -> bool:
    """Whether ``bp`` extends the current organization (design 3, 5.1): a mapping with a top-level ``extend`` key, whatever it holds. Any other
    blueprint is a full blueprint, which builds a new team. Pure: the one definition the plan renderer, the applier and the tools use."""
    return isinstance(bp, Mapping) and "extend" in bp


@runtime_checkable
class BlueprintLoader(Protocol):
    def load(self, source: object) -> JsonObject:
        """A normalized blueprint from a ``Path``, an existing file name, a dict, or YAML/JSON text. A ``BlueprintError`` says why it is none."""
        ...

    def load_text(self, text: str) -> JsonObject:
        """A normalized blueprint from YAML/JSON text only. Never reads a file, whatever the text looks like (for text from a tool call)."""
        ...


@runtime_checkable
class BlueprintValidator(Protocol):
    def validate(
        self, bp: Mapping[str, object], *, org_exists: bool = False, allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False,
    ) -> list[Issue]:
        """All problems with a blueprint. Errors block ``apply``; warnings are shown in the plan.

        ``org_exists``: the organization exists, so its settings (``max_depth``, ``playbook_max_words``) apply and the names it already uses
        (agents, services) are taken; otherwise the defaults apply and nothing is taken. ``allowed_roots``: the directories agents' workspaces
        and the deliverable path may be in (default: home, the temp dir and the current directory, or ``$HIREARCHY_WORKSPACE_ROOTS``).
        ``require_sources``: over MCP, a criterion that declares no source (``criterion-source``) and a plan that records none of the user's words
        (``criterion-words``) are errors; by default (the terminal) they are warnings."""
        ...


@runtime_checkable
class SummaryText(Protocol):
    """What a summary can tell of itself."""

    def text(self) -> str:
        """What ``apply`` reports: the agents created, the services defined, the first task or request, and the warnings."""
        ...


@dataclass
class Summary(SummaryText):
    """What ``apply`` did."""

    agents: list[str]
    task_id: str  # "" when the blueprint gave no first task (services only)
    to: str
    budget: int
    warnings: list[Issue] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    service_request: str = ""  # the service the first task requested, if it is a request

    def text(self) -> str:
        lines = [f"created {len(self.agents)} agents: {', '.join(self.agents)}"]
        if self.services:
            lines.append(f"defined {len(self.services)} service(s) of {self.to}: {', '.join(self.services)} (contract and playbook v1)")
        if self.task_id and self.service_request:
            lines.append(f"first request: service {self.service_request}, task {self.task_id} -> {self.to} (budget {self.budget})")
        elif self.task_id:
            lines.append(f"task {self.task_id} -> {self.to} (budget {self.budget})")
        else:
            lines.append("no task was given: the services are ready and nothing runs yet. To use one: request(service, inputs) "
                         "(or `hirearchy request SERVICE --input key=value`), then start()")
        lines += [f"warning: {w.path}: {w.message}" for w in self.warnings]
        return "\n".join(lines)


@runtime_checkable
class PlanRenderer(Protocol):
    def render_plan(
        self, bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, allowed_roots: Sequence[str | Path] | None = None,
    ) -> str:
        """The details: goal, needs, organization tree, budget, review, deliverable, checkpoints, warnings and errors. ``issues`` default to what
        the validator finds."""
        ...

    def plan_for_user(
        self, bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, allowed_roots: Sequence[str | Path] | None = None,
    ) -> str:
        """The compact, plain-language block the assistant shows to the user verbatim (about 40 lines at most)."""
        ...

    def propose_text(
        self, bp: Mapping[str, object], *, target: str = "", allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False,
    ) -> str:
        """What ``propose_org`` returns: ``target`` line, the block for the user, the details and the ``plan_id`` (none when the blueprint has errors;
        with ``require_sources``, also when a criterion declares no source or the plan records none of the user's words)."""
        ...

    def propose(self, source: object, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        """Load a blueprint (text, path or dict), validate it and return the details. Writes nothing."""
        ...


@runtime_checkable
class PlanIdentity(Protocol):
    def plan_id(self, bp: Mapping[str, object]) -> str:
        """12 hex digits of the normalized blueprint: the same blueprint (whatever its YAML layout, comments or key order) always gives the same id,
        any change to a value gives another, and the organization it is planned against does not matter. Nothing is stored."""
        ...


@runtime_checkable
class BlueprintApplier(Protocol):
    def apply(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False) -> Summary:
        """Create the agents (parents first, as root through each parent), define the services and give the first task: a plain task, a first
        request for a service (``task.service``) or none. A ``BlueprintError`` on any validation error, before anything is written (with
        ``require_sources``, a criterion without a source or a plan without the user's words is one); if a hire, a service definition or the
        delegation fails midway, the top-level agents created are retired again, the workspace directories this call made are removed when empty,
        and the error is raised."""
        ...


@runtime_checkable
class ExtensionApplying(Protocol):
    def apply(
        self, bp: Mapping[str, object], *, plan_id: str | None, require_sources: bool = False, allowed_roots: Sequence[str | Path] | None = None,
    ) -> str:
        """Apply the extension ``bp`` to the current organization (design 5.5) and return the reply: limits first (the hiring rules then admit the
        additions), then the agents and services it adds, the charter lines and budgets it changes, then the services and agents it retires. Validated
        again against the files as they are now (``BlueprintError``, nothing written, on an error); with a ``plan_id`` (``None`` skips this, for the
        user's own file at the terminal) it must be the id ``PlanIdentity`` gives the extension now, else it is refused as stale. A failure while
        writing takes back everything written before it; a failure while retiring leaves what was applied and says so. The owner of a service that
        got a new verifier is told only after a full apply."""
        ...


@runtime_checkable
class BlueprintExamples(Protocol):
    def example(self, kind: str = "research", base: Path | str = ".", service: bool = False) -> str:
        """The template text for ``kind`` (``EXAMPLE_KINDS``) with absolute paths under ``base``; ``service``: as a standing service. An ``OrgError``
        for another kind."""
        ...


@runtime_checkable
class WorkspaceProvisioner(Protocol):
    def ensure(self, path: Path) -> list[Path]:
        """``mkdir -p``; the directories that did not exist and were made, the deepest first (none when ``path`` exists)."""
        ...

    def remove_if_empty(self, path: Path) -> bool:
        """Remove the directory when it is empty; False (and nothing removed) when it cannot be removed."""
        ...
