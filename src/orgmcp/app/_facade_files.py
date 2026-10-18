# mypy: ignore-errors
"""Guarded reading and writing of org files (orgfiles).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..kernel import (
    inside as _inside,
    join_frontmatter,
    OrgError,
    ROOT,
    RUNTIME_NAMES,
    split_frontmatter,
    visible as _visible,
    word_count,
)
from ._compat import atomic_write


def _short(value: object, limit: int = 80) -> str:
    text = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=10_000).strip()
    if text.endswith("\n..."):
        text = text[:-4].strip()
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def charter_change_note(addr: str, old: dict, written: dict, merged: dict) -> str:
    """What a charter rewrite did to the frontmatter: keys kept from the old one, keys changed (old -> new), added."""
    kept = [k for k in old if k not in written]
    changed = [f"{k}: {_short(old[k])} -> {_short(written[k])}" for k in old if k in written and old[k] != written[k]]
    added = [f"{k}: {_short(written[k])}" for k in written if k not in old]
    parts = [f"charter frontmatter of `{addr}`:"]
    parts.append(f"kept from the old frontmatter (not in your text): {', '.join(kept)}." if kept else "nothing kept from the old frontmatter (your text set every key).")
    if changed:
        parts.append("changed (old -> new): " + "; ".join(changed) + ".")
    if added:
        parts.append("added: " + "; ".join(added) + ".")
    if not changed and not added:
        parts.append("no key changed.")
    parts.append("A key you leave out is kept; to remove one, set it explicitly (e.g. `tools: []`).")
    return " ".join(parts)


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


def _case_twin(parent: Path, name: str) -> str | None:
    """The existing entry of ``parent`` that equals ``name`` except for case, if there is one."""
    try:
        names = os.listdir(parent)
    except OSError:
        return None
    if name in names:
        return None
    key = _fold(name)
    return next((n for n in names if _fold(n) == key), None)


class FilesMixin:
    """Guarded reading and writing of org files (orgfiles)."""

    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        """Relative paths are relative to the org root. Absolute paths must be inside the organization or, for an agent,
        inside its workspace or inputs or the workspace of an agent in its subtree. Root reads the organization only."""
        p = (self.root / path.lstrip("/")).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        if _inside(p, self.root):
            return p
        who = self.norm(actor) if actor else ROOT
        if who != ROOT and any(_inside(p, b) for b in self.readable_roots(who)):
            return p
        if who == ROOT:
            raise OrgError("you can only read inside the organization")
        raise OrgError(
            "you can only read inside the organization (paths relative to the org root), or by absolute path inside "
            "your workspace, your read-only inputs, or the workspace of an agent in your team"
        )

    def read(self, path: str, actor: str | None = None) -> str:
        p = self.resolve_read(path or ".", self.require(actor) if actor else None)
        if p.is_dir():
            entries = [f"{c.name}/" if c.is_dir() else c.name for c in _visible(p.iterdir())]
            return "\n".join(entries) or "(empty directory)"
        if not p.is_file():
            raise OrgError(f"not found: {path} (relative paths are relative to the org root)")
        text = p.read_text(encoding="utf-8", errors="replace")
        modified = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        shown = p.relative_to(self.root) if _inside(p, self.root) else p
        head = f"[{shown}: {word_count(text)} words, {text.count(chr(10))} lines, modified {modified:%H:%M:%S} UTC]\n"
        limit = 100_000
        return head + (text if len(text) <= limit else text[:limit] + f"\n... (truncated, {len(text)} chars total)")

    def resolve_write(self, actor: str, path: str) -> Path:
        """Paths are relative to the org root (like every path in the org) and must be inside your directory."""
        actor = self.require(actor)
        base = self.dir(actor).resolve()
        p = Path(path).expanduser()
        p = (p if p.is_absolute() else self.root / p).resolve()
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
            twin = _case_twin(cur, part)
            if twin:
                raise OrgError(f"`{part}` differs only by letter case from the existing `{twin}`; use the exact name `{twin}`")
            cur = cur / part
        if any(_fold(part) == "agent.md" for part in rel):
            if len(rel) == 1:
                raise OrgError("your charter is owned by your parent")
            reports = {c.rsplit("/", 1)[-1] for c in self.children(actor)}
            if rel != (rel[0], "AGENT.md") or rel[0] not in reports:
                raise OrgError(
                    "AGENT.md can only be written for an existing direct report; "
                    "create agents with hire (it enforces hiring rights, limits and authority)"
                )
        if first == "ORG.md" and actor != ROOT:
            raise OrgError("ORG.md is owned by root")
        if (base / first / "AGENT.md").is_file() and p != base / first / "AGENT.md":
            raise OrgError("inside a direct report's directory you may only edit its charter (AGENT.md)")
        return p

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        return self.write_noted(actor, path, content, append)[0]

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        """:meth:`write`, plus a note for the writer (non-empty only for a charter rewrite: what was kept/changed).

        A parent rewriting a report's charter does not strip its frontmatter: every key of the old frontmatter that
        the new text does not set is kept (a key the new text sets, even to an empty value, wins). The authority
        checks run on the merged frontmatter.
        """
        actor = self.require(actor)
        p = self.resolve_write(actor, path)
        note = ""
        if p.name == "AGENT.md" and actor != ROOT:  # a parent editing a report's charter
            meta, body = split_frontmatter(content)
            if not meta.get("role"):
                raise OrgError("a charter needs YAML frontmatter with at least `role:`")
            if not append and p.is_file():
                old, _ = split_frontmatter(p.read_text(encoding="utf-8"))
                merged = {**meta, **{k: v for k, v in old.items() if k not in meta}}
                note = charter_change_note(p.parent.relative_to(self.root).as_posix(), old, meta, merged)
                if len(merged) != len(meta):
                    content = join_frontmatter(merged, body)
                meta = merged
            mine, _ = self.charter(actor)
            if "read" in (meta.get("tools") or []) and self.unconfined_read(meta) and not self.unconfined_read(mine):
                raise OrgError(
                    "a charter with `read` and no workspace needs an `inputs:` list (it may be empty), otherwise its "
                    "built-in read is not confined to the workspace and inputs you have yourself"
                )
            self._check_authority(actor, list(meta.get("tools") or []), meta.get("workspace"), self._check_inputs(meta.get("inputs")))
        if append and p.exists():
            content = p.read_text(encoding="utf-8") + content
        if p == self.dir(actor) / "MEMORY.md":
            cap, words = int(self.config["memory_max_words"]), len(content.split())
            if words > cap:
                raise OrgError(
                    f"MEMORY.md would be {words} words; the limit is {cap}. Do not append: condense it. "
                    "Rewrite the whole file (append=false) keeping only what your next run needs, "
                    "and move detail into files under your work/ directory."
                )
        if p.name == "AGENT.md":  # a report's charter: the registry of the agents writes it
            self.runtime.agent_registry.rewrite_charter(p.parent.relative_to(self.root).as_posix(), content)
        else:
            atomic_write(p, content)
        return p, note
