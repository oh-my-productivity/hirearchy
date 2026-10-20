"""Providers of the ``bootstrap`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..bootstrap import OrgInitializer
from ..bootstrap._initializer import FsOrgInitializer
from ..settings import OrgDocumentStore
from ..snapshots import IgnoreList, OrgSnapshotter
from ..templates import DocumentTemplates
from ._builder import Builder
from .wiring import open_runtime


def register(b: Builder) -> None:
    b.provide(
        OrgInitializer,
        lambda b: FsOrgInitializer(b.get(OrgDocumentStore), b.get(DocumentTemplates), b.get(OrgSnapshotter), b.get(IgnoreList)),
    )


def initialize_org(root: str | Path, mission: str | None = None, config: Mapping[str, object] | None = None) -> Path:
    """Make ``root`` an organization and return its resolved directory (``Org.init`` builds the facade around it).

    The initializer is a port of the runtime of the new organization, which can only be opened once its directory is known: the one place that
    opens a runtime for a root that is not an organization yet."""
    resolved = Path(root).expanduser().resolve()
    open_runtime(resolved).org_initializer.init(resolved, mission, config)
    return resolved
