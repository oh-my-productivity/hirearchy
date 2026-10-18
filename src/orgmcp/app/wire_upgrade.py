"""Providers of the ``upgrade`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..settings import OrgDocumentStore
from ..snapshots import OrgSnapshotter
from ..templates import DocumentTemplates
from ..upgrade import RulesUpgrader
from ..upgrade._upgrader import TemplateRulesUpgrader
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(RulesUpgrader, lambda b: TemplateRulesUpgrader(b.get(OrgDocumentStore), b.get(DocumentTemplates), b.get(OrgSnapshotter)))
