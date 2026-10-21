# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import subprocess

import pytest
from testkit.reach.hirearchy.core import Org, OrgError

from hirearchy.templates.testing import static_document_templates
from hirearchy.upgrade._rules import extract_mission

document_templates = static_document_templates()

MISSION = "Study octopuses.\n\n## Findings so far\nThey have three hearts."


def upgrade_rules(org, dry_run=False):
    return org.runtime.rules_upgrader.upgrade_rules(dry_run)


def old_org(tmp_path):
    """An organization whose ORG.md has the rules of an earlier version (no budget return, no rule 9) and a commented frontmatter."""
    org = Org.init(tmp_path / "org", MISSION, {"poll_seconds": 0.05, "default_model": "m1"})
    path = org.root / "ORG.md"
    text = path.read_text()
    front, body = text.split("\n---\n", 1)
    body = body.replace("  Budget comes back up:", "  REMOVED:").split("  REMOVED:")[0].rstrip() + "\n"
    body = body.split("9. Reviews and fact-checks")[0].rstrip() + "\n"
    path.write_text(front.replace("poll_seconds", "# my comment\npoll_seconds") + "\n---\n" + body)
    return org


def test_fresh_org_is_up_to_date(tmp_path):
    org = Org.init(tmp_path / "org", MISSION)
    before = (org.root / "ORG.md").read_bytes()
    result = upgrade_rules(org)
    assert not result.changed and "already up to date" in result.text()
    assert (org.root / "ORG.md").read_bytes() == before


def test_extract_mission_keeps_headings_inside_the_mission():
    assert extract_mission(document_templates.org_rules(MISSION)) == MISSION


def test_upgrade_rewrites_only_the_body(tmp_path):
    org = old_org(tmp_path)
    front_before = (org.root / "ORG.md").read_text().split("\n---\n", 1)[0]
    result = upgrade_rules(org)
    text = (org.root / "ORG.md").read_text()
    assert result.changed and result.written and result.added > 0
    assert text.split("\n---\n", 1)[0] == front_before and "# my comment" in text  # frontmatter byte for byte
    assert "9. Reviews and fact-checks" in text and "Budget comes back up" in text
    assert extract_mission(org.rules()) == MISSION
    assert org.config["default_model"] == "m1" and org.config["poll_seconds"] == 0.05
    assert upgrade_rules(org).changed is False  # idempotent
    log = subprocess.run(["git", "log", "--oneline"], cwd=org.root, capture_output=True, text=True).stdout
    assert "upgrade ORG.md rules" in log


def test_dry_run_writes_nothing(tmp_path):
    org = old_org(tmp_path)
    before = (org.root / "ORG.md").read_bytes()
    result = upgrade_rules(org, dry_run=True)
    assert result.changed and not result.written and "would rewrite" in result.text()
    assert (org.root / "ORG.md").read_bytes() == before


def test_without_a_mission_section_it_refuses(tmp_path):
    org = Org.init(tmp_path / "org", "m")
    path = org.root / "ORG.md"
    front = path.read_text().split("\n---\n", 1)[0]
    path.write_text(front + "\n---\nMy own rules.\n")
    with pytest.raises(OrgError, match="Mission"):
        upgrade_rules(org)
    assert path.read_text().endswith("My own rules.\n")
