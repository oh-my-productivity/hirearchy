"""Providers of the ``bootstrap`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..bootstrap import OrgInitializer
from ..bootstrap._initializer import FsOrgInitializer
from ..settings import OrgDocumentStore
from ..snapshots import IgnoreList, OrgSnapshotter
from ..templates import DocumentTemplates
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(
        OrgInitializer,
        lambda b: FsOrgInitializer(b.get(OrgDocumentStore), b.get(DocumentTemplates), b.get(OrgSnapshotter), b.get(IgnoreList)),
    )
