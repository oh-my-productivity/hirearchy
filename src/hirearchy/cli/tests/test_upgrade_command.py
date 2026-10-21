# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.cli_world import main
from testkit.reach.hirearchy.core import Org


MISSION = "Study octopuses.\n\n## Findings so far\nThey have three hearts."


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


def test_cli(tmp_path, capsys):
    org = old_org(tmp_path)
    main(["--root", str(org.root), "upgrade-rules", "--dry-run"])
    out = capsys.readouterr()
    assert "would rewrite" in out.out and "org:" not in out.err  # read-only: no 'org:' announcement
    assert "9. Reviews" not in (org.root / "ORG.md").read_text()
    main(["--root", str(org.root), "upgrade-rules"])
    out = capsys.readouterr()
    assert "rewrote the rules" in out.out and f"org: {org.root}" in out.err
    assert "9. Reviews" in (org.root / "ORG.md").read_text()
    main(["--root", str(org.root), "upgrade-rules"])
    assert "already up to date" in capsys.readouterr().out
