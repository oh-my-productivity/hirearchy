"""The public surface of ``access``: what each agent was granted (workspace, inputs, tools, model).

``AccessScopes`` answers where an agent may read and write, ``AuthorityPolicy`` keeps a grant from reaching further than the grantor's
own (tools, workspace, inputs; the right to hire and a report's ``max_children``), ``ToolNaming`` says under which names an agent has the
read and write tools of the organization, and ``ModelResolver`` which model a run uses. The pure function ``unconfined_read`` is the
legacy-charter predicate for callers that hold only a charter's frontmatter, ``children_limit`` the one reading of a ``max_children``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from ._rules import CHILDREN_LIMIT_ERROR, children_limit, unconfined_read

__all__ = [
    "CHILDREN_LIMIT_ERROR",
    "AccessScopes",
    "AuthorityPolicy",
    "ModelResolver",
    "ToolNaming",
    "children_limit",
    "unconfined_read",
]


@runtime_checkable
class AccessScopes(Protocol):
    def workspace_of(self, addr: str) -> Path | None:
        """The agent's workspace (read-write for its built-in tools) as a resolved path, if its charter has one."""
        ...

    def inputs_of(self, addr: str) -> list[Path]:
        """The agent's read-only inputs (charter ``inputs``, a string or a list) as resolved paths."""
        ...

    def readable_roots(self, addr: str) -> list[Path]:
        """Directories outside the org that ``read`` shows to ``addr`` by absolute path: its inputs, and the workspace of every agent
        in its subtree (so a manager can verify what its team made)."""
        ...

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        """Legacy charter: no workspace and no ``inputs`` key. Its built-in ``read`` is not confined (as before)."""
        ...


@runtime_checkable
class AuthorityPolicy(Protocol):
    def check_authority(self, actor: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str] | None = None) -> None:
        """Authority only narrows down the tree: a parent cannot grant what it does not have; ``OrgError`` otherwise."""
        ...

    def check_inputs(self, inputs: object) -> list[str]:
        """Inputs are absolute paths outside the organization directory (kiro reads them; the org owns its own)."""
        ...

    def check_grant(self, actor: str, *, grants_hire: bool, max_children: int | None) -> None:
        """A non-root grantor cannot give a report the right to hire (``grants_hire``: the report gets ``can_hire: true`` it did not have)
        nor a ``max_children`` above its own (``max_children``: the value being set, ``None`` when it is not changed). Root has no bound.
        ``OrgError`` otherwise."""
        ...


@runtime_checkable
class ToolNaming(Protocol):
    def tool_names(self, addr: str) -> dict[str, str]:
        """``read`` / ``write`` -> ``org_read`` / ``org_write`` when the charter holds the built-in of that name (it would shadow the
        organization's tool), else the plain name. Root keeps the plain names."""
        ...


@runtime_checkable
class ModelResolver(Protocol):
    def default_model(self) -> str:
        """The org-wide model: the settings' ``default_model``, else ``DEFAULT_MODEL``."""
        ...

    def model_for(self, addr: str) -> str:
        """The model a run of ``addr`` uses: its charter's ``model``, else the org's ``default_model``, else ``DEFAULT_MODEL``."""
        ...
