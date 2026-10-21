"""The write guard: which paths an agent may write, and the names it may not."""

from __future__ import annotations

import os
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..agents import AgentDirectory
from ..kernel import ROOT, RUNTIME_NAMES, OrgError, OrgLayout
from .api import OrgFileStore


def _fold(name: str) -> str:
    """Key under which two file names count as the same name on *some* filesystem.

    macOS (APFS/HFS+) and Windows ignore letter case (and Unicode form); Windows also ignores trailing dots and
    spaces. Protected names are compared through this key, so the write guard behaves identically on case-sensitive
    and case-insensitive filesystems: it never has to ask the filesystem which kind it is.
    """
    return unicodedata.normalize("NFKC", name).casefold().rstrip(" .")


_FOLDED_RUNTIME_NAMES = {_fold(n) for n in RUNTIME_NAMES}
# Files an agent may only write under their exact spelling (any other casing is a different name on Linux and the
# same file on macOS, so it is refused outright).
_EXACT_FILES = {_fold(n): n for n in ("AGENT.md", "MEMORY.md", "ORG.md")}


def case_twin(names: Iterable[str], name: str) -> str | None:
    """The entry of ``names`` that equals ``name`` except for case, if there is one (``None`` when ``name`` itself is among them)."""
    listed = list(names)
    if name in listed:
        return None
    key = _fold(name)
    return next((n for n in listed if _fold(n) == key), None)


def case_twin_in(parent: Path, name: str) -> str | None:
    """The existing entry of the directory ``parent`` that equals ``name`` except for case, if there is one (``None`` when ``parent`` cannot be
    listed). The old ``_case_twin`` of ``hirearchy.core``, which lists the directory itself."""
    try:
        names = os.listdir(parent)
    except OSError:
        return None
    return case_twin(names, name)


@runtime_checkable
class WriteGuard(Protocol):
    def resolve(self, actor: str, path: str) -> Path:
        """The path ``actor`` may write for ``path`` (relative to the org root); ``OrgError`` with the reason otherwise."""
        ...


class PathGuard(WriteGuard):
    def __init__(self, layout: OrgLayout, store: OrgFileStore, agents: AgentDirectory) -> None:
        self._layout = layout
        self._store = store
        self._agents = agents

    def _case_twin(self, parent: Path, name: str) -> str | None:
        """The existing entry of ``parent`` that equals ``name`` except for case, if there is one."""
        try:
            names = self._store.entries(parent)
        except OSError:
            return None
        return case_twin(names, name)

    def resolve(self, actor: str, path: str) -> Path:
        """Paths are relative to the org root (like every path in the org) and must be inside your directory."""
        actor = self._agents.require(actor)
        base = self._store.resolve(self._layout.agent_dir(actor))
        p = Path(path).expanduser()
        p = self._store.resolve(p if p.is_absolute() else self._layout.root / p)
        if p == base or base not in p.parents:
            prefix = "" if actor == ROOT else f"{actor}/"
            raise OrgError(
                f"you may only write inside your own directory. Paths are relative to the org root, so yours "
                f"start with `{prefix}`: e.g. `{prefix}MEMORY.md` or `{prefix}work/notes.md` (got `{path}`)"
            )
        rel = p.relative_to(base).parts
        first = rel[0]
        if _fold(first) == "services":
            raise OrgError(
                "services/ is managed by the runtime: the contract (SERVICE.md) is written by your parent with "
                "define_service, and you change your playbook (PLAYBOOK.md) with revise_playbook"
            )
        if _fold(first) in _FOLDED_RUNTIME_NAMES or first.startswith("."):
            raise OrgError(f"{first} is managed by the runtime; use send/delegate/report to communicate")
        exact = _EXACT_FILES.get(_fold(first))
        if exact and first != exact:
            raise OrgError(f"that name is reserved: it must be spelled exactly `{exact}`")
        cur = base
        for part in rel:  # a spelling that differs only by case from an existing entry would alias it on macOS
            twin = self._case_twin(cur, part)
            if twin:
                raise OrgError(f"`{part}` differs only by letter case from the existing `{twin}`; use the exact name `{twin}`")
            cur = cur / part
        if any(_fold(part) == "agent.md" for part in rel):
            if len(rel) == 1:
                raise OrgError("your charter is owned by your parent")
            reports = {c.rsplit("/", 1)[-1] for c in self._agents.children(actor)}
            if rel != (rel[0], "AGENT.md") or rel[0] not in reports:
                raise OrgError(
                    "AGENT.md can only be written for an existing direct report; "
                    "create agents with hire (it enforces hiring rights, limits and authority)"
                )
        if first == "ORG.md" and actor != ROOT:
            raise OrgError("ORG.md is owned by root")
        if self._store.kind(base / first / "AGENT.md") == "file" and p != base / first / "AGENT.md":
            raise OrgError("inside a direct report's directory you may only edit its charter (AGENT.md)")
        return p
