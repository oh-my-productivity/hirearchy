"""The documents of an organization: ORG.md, charters, task and result bodies."""

from __future__ import annotations

from collections.abc import Sequence

from .api import DocumentTemplates


class StaticDocumentTemplates(DocumentTemplates):
    """Renders the documents from fixed text (RED skeleton)."""

    def org_rules(self, mission: str | None) -> str:
        raise NotImplementedError

    def charter_body(self, role: str, charter: str) -> str:
        raise NotImplementedError

    def task_body(self, goal: str, acceptance: str, inputs: Sequence[str]) -> str:
        raise NotImplementedError

    def result_body(self, summary: str, artifacts: Sequence[str], lessons: str = "") -> str:
        raise NotImplementedError
