"""Creating a new organization (bootstrap).

``init`` delegates to ``OrgInitializer``, through ``wire_bootstrap.initialize_org`` (the organization has no runtime before its ORG.md exists;
ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypeVar

from .wire_bootstrap import initialize_org


class _Organization(Protocol):
    def __init__(self, root: str | Path) -> None: ...


Created = TypeVar("Created", bound=_Organization)


class BootstrapMixin:
    """Creating a new organization (bootstrap)."""

    @classmethod
    def init(cls: type[Created], root: str | Path, mission: str | None = None, config: dict[str, object] | None = None) -> Created:
        return cls(initialize_org(root, mission, config))
