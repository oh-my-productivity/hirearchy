"""Construction, addressing helpers, ids and the runtime ledgers.

The bodies call the ports of ``self.runtime`` and the pure functions of the kernel (ARCHITECTURE.md 5.3 and 6.4): ``dir`` is the layout's, the ledgers are
the ``LedgerStore``'s. ``__init__`` is the one method that is not a delegation: it opens the runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..kernel import OrgError
from ..kernel import child_addr as _child_addr
from ..kernel import depth as _depth
from ..kernel import norm as _norm
from ..kernel import parent as _parent
from .runtime import OrgRuntime
from .wiring import open_runtime


class CoreMixin:
    """Construction, addressing helpers, ids and the runtime ledgers."""

    runtime: OrgRuntime

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        if not (self.root / "ORG.md").is_file():
            raise OrgError(f"not an organization (no ORG.md): {self.root}")
        self.runtime = open_runtime(self.root)  # the ports of this organization (new in M2; nothing reads them yet)

    @staticmethod
    def norm(addr: str | None) -> str:
        return _norm(addr)

    def dir(self, addr: str) -> Path:
        return self.runtime.paths.agent_dir(addr)

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

    def ledger(self, name: str) -> dict[str, Any]:  # Any: callers index into the nested JSON of a ledger, as before
        """Runtime-private bookkeeping (``.runtime/<name>.json``): the only state not derived from messages."""
        return self.runtime.ledgers.read(name)

    def save_ledger(self, name: str, data: dict[str, Any]) -> None:
        return self.runtime.ledgers.write(name, data)
