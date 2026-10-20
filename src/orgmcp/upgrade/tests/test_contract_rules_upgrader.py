"""Contract of ``RulesUpgrader``: the real upgrader over an ORG.md in memory and over an ORG.md on disk with the real git.
The expected bytes and reports were captured from ``upgrade_rules`` of ``main``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.upgrade import RulesUpgrader, Upgrade, UpgradeView
from orgmcp.upgrade.testing import IMPLEMENTATIONS, UpgradeHarness

from ._cases import COMMIT, expected



def frontmatter(text: str | None) -> str:
    return (text or "").split("\n---\n", 1)[0]


@pytest.fixture(params=IMPLEMENTATIONS[RulesUpgrader], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> UpgradeHarness:
    made = cast(Callable[[Path], UpgradeHarness], request.param)(tmp_path)
    assert isinstance(made.upgrader, RulesUpgrader)
    return made


@pytest.fixture
def old(h: UpgradeHarness) -> UpgradeHarness:
    """ORG.md of an earlier version: rules without the budget-return and review paragraphs, a commented frontmatter."""
    h.put(expected("old_org_md.md"))
    return h


def test_a_current_org_md_is_left_alone(h: UpgradeHarness) -> None:
    h.put(expected("new_org_md.md"))
    result = h.upgrader.upgrade_rules()
    assert result == Upgrade(changed=False, added=0, removed=0, diff=[], written=False)
    assert result.text() == expected("up_to_date_text.txt")
    assert h.stored() == expected("new_org_md.md")
    assert h.commits() == []


def test_a_dry_run_reports_and_writes_nothing(old: UpgradeHarness) -> None:
    result = old.upgrader.upgrade_rules(dry_run=True)
    assert (result.changed, result.written, result.added, result.removed) == (True, False, 35, 0)
    assert result.text() == expected("dry_run_text.txt")
    assert result.text(5) == expected("dry_run_text_5.txt")
    assert old.stored() == expected("old_org_md.md")
    assert old.commits() == []


def test_the_upgrade_rewrites_the_body_and_keeps_the_frontmatter_and_the_mission(old: UpgradeHarness) -> None:
    result = old.upgrader.upgrade_rules()
    assert (result.changed, result.written, result.added, result.removed) == (True, True, 35, 0)
    assert result.text() == expected("written_text.txt")
    assert old.stored() == expected("new_org_md.md")
    assert frontmatter(old.stored()) == frontmatter(expected("old_org_md.md"))
    assert "# my comment" in (old.stored() or "")


def test_a_changed_org_md_is_committed_once(old: UpgradeHarness) -> None:
    old.upgrader.upgrade_rules()
    assert old.commits() == [COMMIT]
    again = old.upgrader.upgrade_rules()
    assert again.changed is False and again.text() == expected("up_to_date_text.txt")
    assert old.commits() == [COMMIT]


def test_an_org_md_without_frontmatter_stays_without(h: UpgradeHarness) -> None:
    body = expected("old_org_md.md").split("\n---\n", 1)[1]
    h.put(body)
    h.upgrader.upgrade_rules()
    assert h.stored() == expected("new_org_md.md").split("\n---\n", 1)[1]


def test_without_a_mission_section_it_refuses_and_changes_nothing(h: UpgradeHarness) -> None:
    mine = "---\npoll_seconds: 1\n---\nMy own rules.\n"
    h.put(mine)
    with pytest.raises(OrgError, match="no '## Mission' section"):
        h.upgrader.upgrade_rules()
    with pytest.raises(OrgError, match="edit ORG.md by hand"):
        h.upgrader.upgrade_rules(dry_run=True)
    assert h.stored() == mine
    assert h.commits() == []


def test_the_report_is_a_view(h: UpgradeHarness) -> None:
    h.put(expected("new_org_md.md"))
    assert isinstance(h.upgrader.upgrade_rules(), UpgradeView)
