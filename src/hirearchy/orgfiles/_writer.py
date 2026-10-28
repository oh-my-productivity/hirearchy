"""``GuardedOrgFileWriter``: writes the files of an agent's own directory, and the charters of its direct reports."""

from __future__ import annotations

from collections.abc import Container, Iterable, Mapping
from pathlib import Path
from typing import cast

from ..access import AccessScopes, AuthorityPolicy, children_limit
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..kernel import ROOT, JsonObject, OrgError, OrgLayout, join_frontmatter, split_frontmatter
from ..settings import OrgSettings, config_default_model, config_floor_problem, model_floor_problem
from ._charter_added import CHARTER_ADDED, added_keys
from ._charter_merge import CharterMerge
from ._guard import WriteGuard
from .api import OrgFileStore, OrgFileWriter


# CHARTER-PLAN (design 6.6, L20 of review 2): the frontmatter of a report's charter is the plan's, which the user approved.
CHARTER_PLAN = (
    'refused: {key} of {addr} is the plan\'s, which the user approved; a change goes through the user (propose_org(..., extend="current"), or the '
    'terminal). A charter edit may change its body (outside "## Added by your changes"), its role, and lower max_children. Nothing was written.'
)


def _lowered(old: object, new: object) -> bool:
    """``new`` is a ``max_children`` at or below ``old`` (both whole numbers; an absent limit is no value to stay under)."""
    return all(isinstance(n, int) and not isinstance(n, bool) for n in (old, new)) and cast(int, new) <= cast(int, old)


def _plan_key_changed(old: Mapping[str, object], new: Mapping[str, object]) -> str | None:
    """The first key, in sorted order, in which ``new`` differs from ``old`` beyond what a parent may change (``role``, and a ``max_children`` at or below the
    old one); an absent key equals ``None``. None when the frontmatter is the plan's."""
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key), new.get(key)
        if before == after or key == "role" or (key == "max_children" and _lowered(before, after)):
            continue
        return key
    return None


def _frontmatter_of(text: str) -> JsonObject:
    """The frontmatter of a text; ``{}`` when YAML cannot read it (nothing reads such a file as a charter or a settings block either)."""
    try:
        return split_frontmatter(text)[0]
    except Exception:  # noqa: BLE001 - YAML that does not parse: the file is no charter and no settings block, so there is nothing to check
        return {}


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

        The org-agent floor (docs/design/org-agent-model-floor.md 3): a charter rewrite that changes the model the agent runs on to one outside the
        allowed models is refused (a rewrite that leaves it as it was is not, even below the floor), and so is a write of the top-level ORG.md
        that widens the allowed models or sets an effort or a default model outside the floor.
        """
        actor = self._agents.require(actor)
        p = self.resolve_write(actor, path)
        note = ""
        planned: tuple[dict[str, object], dict[str, object]] | None = None  # (old, new) frontmatter of a report's charter, for CHARTER-PLAN
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
            wanted = children_limit(new["max_children"]) if changed else None
            before = (old or {}).get("max_children")
            if wanted is not None and isinstance(before, int) and not isinstance(before, bool) and wanted <= before:
                wanted = None  # lowering a report's limit is always allowed: only a raise is bounded by the writer's own
            self._authority.check_grant(actor, grants_hire=grants_hire, max_children=wanted)
            if old is not None:
                planned = (old, dict(new))
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
            addr = p.parent.relative_to(self._layout.root).as_posix()
            self._check_charter_model(addr, p, content)
            if planned is not None and (key := _plan_key_changed(*planned)) is not None:
                raise OrgError(CHARTER_PLAN.format(key=key, addr=addr))
            if actor != ROOT and self._store.kind(p) == "file" and added_keys(self._store.read_text(p)) != added_keys(content):
                raise OrgError(CHARTER_ADDED)  # (CHARTER-ADDED: the text that would be written, an append joined to the old text)
            self._registry.rewrite_charter(addr, content)
        else:
            self._check_org_md(p, content)
            self._store.write_text(p, content)
        return p, note

    def _config_or_empty(self) -> JsonObject:
        """The org's settings, ``{}`` when ORG.md cannot be parsed: the floor is then checked against the built-in set, effort and model, so root can still repair ORG.md and rewrite charters."""
        try:
            return self._settings.config()
        except Exception:  # noqa: BLE001 - YAML that does not parse (a hand edit slipped): the writes that would repair it must not fail on it
            return {}

    def _check_charter_model(self, addr: str, path: Path, content: str) -> None:
        """Refuse a charter text that changes the model the agent runs on (its ``model``, else the org's default) to one outside the allowed set."""
        cfg = self._config_or_empty()
        fallback = config_default_model(cfg)
        new = str(_frontmatter_of(content).get("model") or "").strip() or fallback
        if self._store.kind(path) == "file" and new == (str(_frontmatter_of(self._store.read_text(path)).get("model") or "").strip() or fallback):
            return  # the model is as it was: an agent from before the floor can still get a new body
        problem = model_floor_problem(cfg, new)
        if problem is not None:
            raise OrgError(f"charter of {addr}: {problem}")

    def _check_org_md(self, path: Path, content: str) -> None:
        """Refuse a write of the top-level ORG.md that widens the allowed models or sets an effort or a default model outside the floor."""
        if path != self._store.resolve(self._layout.root) / "ORG.md":
            return
        problem = config_floor_problem(_frontmatter_of(content), before=self._config_or_empty())
        if problem is not None:
            raise OrgError(f"ORG.md: {problem}")
