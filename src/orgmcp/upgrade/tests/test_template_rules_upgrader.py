"""``TemplateRulesUpgrader``: which port it uses, with what, and in which order."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from orgmcp.kernel import OrgError
from orgmcp.snapshots import OrgSnapshotter
from orgmcp.templates import DocumentTemplates
from orgmcp.upgrade import RulesUpgrader
from orgmcp.upgrade._upgrader import TemplateRulesUpgrader

from ._cases import COMMIT

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-bootstrap", raises=NotImplementedError)

FRONT = "---\n# kept\npoll_seconds:   1\n---\n"
OLD = FRONT + "# Org\n\n## Mission\nStudy things.\n\n## How this organization works\nold rules\n"


class Journal:
    def __init__(self, text: str | None) -> None:
        self.text = text
        self.calls: list[str] = []


class Documents(Journal):
    def exists(self) -> bool:
        return self.text is not None

    def read_raw(self) -> str:
        self.calls.append("read")
        assert self.text is not None
        return self.text

    def write_raw(self, text: str) -> None:
        self.calls.append("write")
        self.text = text


class Snapshots(OrgSnapshotter):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def init_repository(self) -> None:
        raise AssertionError("an upgrade starts no repository")

    def commit(self, message: str) -> None:
        self.calls.append(f"commit {message}")


class Templates(DocumentTemplates):
    def __init__(self, rules: str = "NEW RULES") -> None:
        self.rules = rules
        self.missions: list[str | None] = []

    def org_rules(self, mission: str | None) -> str:
        self.missions.append(mission)
        return f"# Org\n\n## Mission\n{mission}\n\n{self.rules}\n\n\n"

    def charter_body(self, role: str, charter: str) -> str:
        raise AssertionError("not used")

    def task_body(self, goal: str, acceptance: str, inputs: Sequence[str]) -> str:
        raise AssertionError("not used")

    def result_body(self, summary: str, artifacts: Sequence[str], lessons: str = "") -> str:
        raise AssertionError("not used")


def make(text: str | None = OLD, rules: str = "NEW RULES") -> tuple[RulesUpgrader, Documents, Templates]:
    documents, templates = Documents(text), Templates(rules)
    return TemplateRulesUpgrader(documents, templates, Snapshots(documents.calls)), documents, templates


def test_the_rules_come_from_the_templates_with_the_mission_that_the_file_has() -> None:
    upgrader, documents, templates = make()
    upgrader.upgrade_rules()
    assert templates.missions == ["Study things."]
    assert documents.text == FRONT + "# Org\n\n## Mission\nStudy things.\n\nNEW RULES\n"  # frontmatter as written, one trailing newline


def test_it_reads_then_writes_then_commits() -> None:
    upgrader, documents, _ = make()
    upgrader.upgrade_rules()
    assert documents.calls == ["read", "write", f"commit {COMMIT}"]


def test_a_dry_run_only_reads() -> None:
    upgrader, documents, _ = make()
    result = upgrader.upgrade_rules(dry_run=True)
    assert documents.calls == ["read"] and documents.text == OLD
    assert result.changed and not result.written


def test_nothing_is_written_or_committed_when_the_rules_are_current() -> None:
    upgrader, documents, _ = make(rules="old rules")
    upgrader.upgrade_rules()
    assert documents.calls == ["read"]


def test_the_comparison_ignores_trailing_whitespace() -> None:
    current = FRONT + "# Org\n\n## Mission\nStudy things.\n\nNEW RULES\n\n\n\n"
    upgrader, documents, _ = make(current)
    assert upgrader.upgrade_rules().changed is False
    assert documents.calls == ["read"]


def test_the_diff_counts_added_and_removed_lines() -> None:
    upgrader, _, _ = make(rules="a\nb")
    result = upgrader.upgrade_rules(dry_run=True)
    assert (result.added, result.removed) == (2, 1)
    assert result.diff[-3:] == ["-old rules", "+a", "+b"]


def test_a_missing_mission_section_is_refused_before_anything_is_written() -> None:
    upgrader, documents, _ = make("---\na: 1\n---\nMy own rules.\n")
    with pytest.raises(OrgError, match="Mission"):
        upgrader.upgrade_rules()
    assert documents.calls == ["read"]
