"""Agent addresses: the vocabulary of names and the arithmetic on them (pure, no file access)."""

from __future__ import annotations

import re

ROOT = "root"
RUNTIME = "runtime"
BOXES = ("inbox", "inflight", "read", "sent")
RUNTIME_NAMES = {*BOXES, "runs", "services", ".paused", ".kiro", ".runtime", ".retired", ".git", ".gitignore"}
RESERVED = RUNTIME_NAMES | {"work", "root", "runtime", "agent", "memory", "org"}

NAME_RE = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")


def norm(addr: str | None) -> str:
    """The canonical form of an address: surrounding blanks and slashes removed, ``""`` and ``root`` are the root."""
    raise NotImplementedError("red: K1")


def parent(addr: str | None) -> str | None:
    """The address of the parent; ``None`` for the root."""
    raise NotImplementedError("red: K1")


def depth(addr: str | None) -> int:
    """0 for the root, 1 for its direct reports, ..."""
    raise NotImplementedError("red: K1")


def child_addr(parent: str | None, name: str) -> str:
    """The address of the child ``name`` of ``parent``."""
    raise NotImplementedError("red: K1")
