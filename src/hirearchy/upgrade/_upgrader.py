"""Rewriting the rules in ORG.md."""

from __future__ import annotations

import difflib

from ..settings import OrgDocumentStore
from ..snapshots import OrgSnapshotter
from ..templates import DocumentTemplates
from ._report import Upgrade
from ._rules import extract_mission, split_raw
from .api import RulesUpgrader

COMMIT_MESSAGE = "root: upgrade ORG.md rules to the current template"


class TemplateRulesUpgrader(RulesUpgrader):
    """Reads and writes ORG.md through the document store, takes the rules from the templates, snapshots a change."""

    def __init__(self, documents: OrgDocumentStore, templates: DocumentTemplates, snapshotter: OrgSnapshotter) -> None:
        self._documents = documents
        self._templates = templates
        self._snapshotter = snapshotter

    def upgrade_rules(self, dry_run: bool = False) -> Upgrade:
        text = self._documents.read_raw()
        front, body = split_raw(text)
        new_body = self._templates.org_rules(extract_mission(body)).rstrip() + "\n"
        old_lines, new_lines = body.rstrip().splitlines(), new_body.rstrip().splitlines()
        diff = [ln for ln in difflib.unified_diff(old_lines, new_lines, "ORG.md (current)", "ORG.md (new)", lineterm="", n=1)][2:]
        added = sum(1 for ln in diff if ln.startswith("+"))
        removed = sum(1 for ln in diff if ln.startswith("-"))
        changed = body.rstrip() != new_body.rstrip()
        if changed and not dry_run:
            self._documents.write_raw(front + new_body)
            self._snapshotter.commit(COMMIT_MESSAGE)
        return Upgrade(changed, added, removed, diff, written=changed and not dry_run)
