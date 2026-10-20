# mypy: ignore-errors
"""Construction, addressing helpers, ids and the runtime ledgers.

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

import json
from pathlib import Path

from ..kernel import child_addr as _child_addr, depth as _depth, norm as _norm, OrgError, parent as _parent, ROOT
from .wiring import open_runtime


class CoreMixin:
    """Construction, addressing helpers, ids and the runtime ledgers."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        if not (self.root / "ORG.md").is_file():
            raise OrgError(f"not an organization (no ORG.md): {self.root}")
        self.runtime = open_runtime(self.root)  # the ports of this organization (new in M2; nothing reads them yet)

    @staticmethod
    def norm(addr: str | None) -> str:
        return _norm(addr)

    def dir(self, addr: str) -> Path:
        a = self.norm(addr)
        return self.root if a == ROOT else self.root / a

    @classmethod
    def parent(cls, addr: str) -> str | None:
        return _parent(addr)

    @classmethod
    def depth(cls, addr: str) -> int:
        return _depth(addr)

    def child_addr(self, parent: str, name: str) -> str:
        return _child_addr(parent, name)

    def new_id(self, sender: str) -> str:
        return self.runtime.ids.message_id(sender)

    def ledger(self, name: str) -> dict:
        """Runtime-private bookkeeping (``.runtime/<name>.json``): the only state not derived from messages."""
        try:
            return json.loads((self.root / ".runtime" / f"{name}.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return {}

    def save_ledger(self, name: str, data: dict) -> None:
        self.runtime.ledgers.write(name, data)
