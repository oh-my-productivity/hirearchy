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
    services:                   # optional: standing tasks the top-level agent offers (see ``orgmcp.services``)
      - {name, owner, description, inputs: [{name, description, required}], acceptance: [...],
         deliverable: {description, format, max_words, path}, budget, playbook, locked}
    # with services, ``task`` is optional; it may be a first request: {service, inputs: {...}, title, note}

This part of the package turns text into a *checked* blueprint: ``RoleLibrary`` is the packaged role templates (``roles/*.md``),
``BlueprintLoader`` reads a blueprint from a path, a dict or YAML/JSON text and normalizes it, ``BlueprintValidator`` lists everything wrong with it
(errors block ``apply``, warnings are shown in the plan). The plan the user approves, its identity and the application of a blueprint come with
the second half of the package.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, OrgError

__all__ = [
    "Agent",
    "BlueprintError",
    "BlueprintLoader",
    "BlueprintValidator",
    "Issue",
    "IssueText",
    "Role",
    "RoleLibrary",
    "errors",
]


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
        self, bp: Mapping[str, object], *, org_exists: bool = False, allowed_roots: Sequence[str | Path] | None = None,
    ) -> list[Issue]:
        """All problems with a blueprint. Errors block ``apply``; warnings are shown in the plan.

        ``org_exists``: the organization exists, so its settings (``max_depth``, ``playbook_max_words``) apply and the names it already uses
        (agents, services) are taken; otherwise the defaults apply and nothing is taken. ``allowed_roots``: the directories agents' workspaces
        and the deliverable path may be in (default: home, the temp dir and the current directory, or ``$ORGMCP_WORKSPACE_ROOTS``)."""
        ...
