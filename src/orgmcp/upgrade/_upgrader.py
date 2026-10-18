"""Rewriting the rules in ORG.md."""

from __future__ import annotations

from ..settings import OrgDocumentStore
from ..snapshots import OrgSnapshotter
from ..templates import DocumentTemplates
from .api import RulesUpgrader, Upgrade


class TemplateRulesUpgrader(RulesUpgrader):
    """Reads and writes ORG.md through the document store, takes the rules from the templates, snapshots a change."""

    def __init__(self, documents: OrgDocumentStore, templates: DocumentTemplates, snapshotter: OrgSnapshotter) -> None:
        self._documents = documents
        self._templates = templates
        self._snapshotter = snapshotter

    def upgrade_rules(self, dry_run: bool = False) -> Upgrade:
        raise NotImplementedError
