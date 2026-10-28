"""Agent addresses: the vocabulary of names and the arithmetic on them (pure, no file access)."""

from __future__ import annotations

import re

ROOT = "root"
RUNTIME = "runtime"
BOXES = ("inbox", "inflight", "read", "sent")
RUNTIME_NAMES = {*BOXES, "runs", "services", ".paused", ".kiro", ".runtime", ".retired", ".git", ".gitignore", "RETIRED.md"}
RESERVED = RUNTIME_NAMES | {"work", "root", "runtime", "agent", "memory", "org"}
# Always use NAME_RE.fullmatch: a "$" anchor would accept a trailing newline ("ops\n"), so \Z is used as well.
NAME_RE = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")


def norm(addr: str | None) -> str:
    """The canonical form of an address: surrounding blanks and slashes removed, ``""`` and ``root`` are the root."""
    a = (addr or "").strip().strip("/")
    return ROOT if a in ("", ROOT) else a


def parent(addr: str | None) -> str | None:
    """The address of the parent; ``None`` for the root."""
    a = norm(addr)
    if a == ROOT:
        return None
    return a.rsplit("/", 1)[0] if "/" in a else ROOT


def depth(addr: str | None) -> int:
    """0 for the root, 1 for its direct reports, ..."""
    a = norm(addr)
    return 0 if a == ROOT else a.count("/") + 1


def child_addr(parent: str | None, name: str) -> str:
    """The address of the child ``name`` of ``parent``."""
    return name if norm(parent) == ROOT else f"{norm(parent)}/{name}"
