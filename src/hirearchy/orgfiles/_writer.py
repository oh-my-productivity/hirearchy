"""``GuardedOrgFileWriter``: writes the files of an agent's own directory, and the charters of its direct reports."""

from __future__ import annotations

from collections.abc import Container, Iterable
from pathlib import Path
from typing import cast

from ..access import AccessScopes, AuthorityPolicy, children_limit
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..kernel import ROOT, OrgError, OrgLayout, join_frontmatter, split_frontmatter
from ..settings import OrgSettings
from ._charter_merge import CharterMerge
from ._guard import WriteGuard
from .api import OrgFileStore, OrgFileWriter


class GuardedOrgFileWriter(OrgFileWriter):
    def __init__(
        self,
        layout: OrgLayout,
        store: OrgFileStore,
        guard: WriteGuard,
        merger: CharterMerge,
        agents: AgentDirectory,
        charters: CharterReader,
        registry: AgentRegistry,
        scopes: AccessScopes,
        authority: AuthorityPolicy,
        settings: OrgSettings,
    ) -> None:
        self._layout = layout
        self._store = store
        self._guard = guard
        self._merger = merger
        self._agents = agents
        self._charters = charters
        self._registry = registry
        self._scopes = scopes
        self._authority = authority
        self._settings = settings

    def resolve_write(self, actor: str, path: str) -> Path:
        """Paths are relative to the org root (like every path in the org) and must be inside your directory."""
        return self._guard.resolve(actor, path)

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        return self.write_noted(actor, path, content, append)[0]

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        """:meth:`write`, plus a note for the writer (non-empty only for a charter rewrite: what was kept/changed).

        A parent rewriting a report's charter does not strip its frontmatter: every key of the old frontmatter that
        the new text does not set is kept (a key the new text sets, even to an empty value, wins). The authority
        checks run on the merged frontmatter. A parent that is not root cannot grant ``can_hire`` the report did not have, nor change the
        report's ``max_children`` to a value above its own: only a change is bounded (a body-only edit keeps whatever the charter held),
        and an append never changes the frontmatter.
        """
        actor = self._agents.require(actor)
        p = self.resolve_write(actor, path)
        note = ""
        if p.name == "AGENT.md" and actor != ROOT:  # a parent editing a report's charter
            meta, body = split_frontmatter(content)
            if not meta.get("role"):
                raise OrgError("a charter needs YAML frontmatter with at least `role:`")
            old: dict[str, object] | None = None  # the frontmatter the file has now, None when there is no file yet
            if self._store.kind(p) == "file":
                old, _ = split_frontmatter(self._store.read_text(p))
            if not append and old is not None:
                merged, note = self._merger.merge(p.parent.relative_to(self._layout.root).as_posix(), old, meta)
                if len(merged) != len(meta):
                    content = join_frontmatter(merged, body)
                meta = merged
            mine, _ = self._charters.charter(actor)
            if (
                "read" in cast("Container[str]", meta.get("tools") or [])
                and self._scopes.unconfined_read(meta)
                and not self._scopes.unconfined_read(mine)
            ):
                raise OrgError(
                    "a charter with `read` and no workspace needs an `inputs:` list (it may be empty), otherwise its "
                    "built-in read is not confined to the workspace and inputs you have yourself"
                )
            self._authority.check_authority(
                actor, list(cast("Iterable[str]", meta.get("tools") or [])), cast("str | None", meta.get("workspace")),
                self._authority.check_inputs(meta.get("inputs")),
            )
            new = old if append and old is not None else meta  # an append leaves the old frontmatter as it is
            grants_hire = bool(new.get("can_hire")) and not bool((old or {}).get("can_hire"))
            changed = "max_children" in new and (old is None or new["max_children"] != old.get("max_children"))
            self._authority.check_grant(
                actor, grants_hire=grants_hire, max_children=children_limit(new["max_children"]) if changed else None
            )
        if append and self._store.kind(p) != "missing":
            content = self._store.read_text(p) + content
        if p == self._layout.agent_dir(actor) / "MEMORY.md":
            cap, words = int(cast("int | str", self._settings.config()["memory_max_words"])), len(content.split())
            if words > cap:
                raise OrgError(
                    f"MEMORY.md would be {words} words; the limit is {cap}. Do not append: condense it. "
                    "Rewrite the whole file (append=false) keeping only what your next run needs, "
                    "and move detail into files under your work/ directory."
                )
        if p.name == "AGENT.md":  # a report's charter: the registry of the agents writes it
            self._registry.rewrite_charter(p.parent.relative_to(self._layout.root).as_posix(), content)
        else:
            self._store.write_text(p, content)
        return p, note
