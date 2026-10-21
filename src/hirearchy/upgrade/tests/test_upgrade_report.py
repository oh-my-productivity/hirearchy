"""``Upgrade``: the report of an upgrade, and the text the command prints."""

from __future__ import annotations

from hirearchy.upgrade import Upgrade, UpgradeView


def report(diff_lines: int, written: bool = False) -> Upgrade:
    return Upgrade(changed=True, added=diff_lines, removed=2, diff=[f"+line {n}" for n in range(diff_lines)], written=written)


def test_an_unchanged_report_says_so() -> None:
    assert Upgrade(False, 0, 0, [], False).text() == "ORG.md rules are already up to date; nothing to change."


def test_a_dry_run_would_rewrite_and_a_real_run_rewrote() -> None:
    assert report(1).text().splitlines()[0] == "would rewrite the rules in ORG.md: +1 -2 lines (frontmatter and mission unchanged)"
    assert report(1, written=True).text().splitlines()[0] == "rewrote the rules in ORG.md: +1 -2 lines (frontmatter and mission unchanged)"


def test_the_diff_is_cut_after_the_limit_with_the_number_of_lines_left() -> None:
    lines = report(90).text().splitlines()
    assert len(lines) == 1 + 80 + 1 and lines[-1] == "... 10 more diff lines"
    assert report(90).text(3).splitlines()[-1] == "... 87 more diff lines"
    assert report(80).text().splitlines()[-1] == "+line 79"


def test_the_report_is_a_view() -> None:
    assert isinstance(report(1), UpgradeView)
    assert UpgradeView in Upgrade.__mro__
