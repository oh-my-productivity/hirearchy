"""Creating a new organization (bootstrap).

``init`` delegates to ``OrgInitializer`` (ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypeVar

from .wiring import open_runtime


class _Organization(Protocol):
    def __init__(self, root: str | Path) -> None: ...


Created = TypeVar("Created", bound=_Organization)


class BootstrapMixin:
    """Creating a new organization (bootstrap)."""

    @classmethod
    def init(cls: type[Created], root: str | Path, mission: str | None = None, config: dict[str, object] | None = None) -> Created:
        root = Path(root).expanduser().resolve()
        open_runtime(root).org_initializer.init(root, mission, config)  # the ports of the new organization: the org is built once its ORG.md exists
        return cls(root)
