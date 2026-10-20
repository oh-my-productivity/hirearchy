# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
import testkit
import testkit.legacy.yaml as yaml
from testkit.legacy.orgmcp.core import Org

from orgmcp.cli import main

ROOT_DIR = testkit.REPO
RESEARCH = ROOT_DIR / "examples" / "blueprint-research.yaml"
CRITERIA = [
    "At most 600 words as counted by read.",
    'Has exactly the sections "This week" and "Our assessment", in that order.',
    "Every sentence with a number, name, version, date or price cites the URL of the page that states it; the fact-checker fetched that page.",
]


def service(**over) -> dict:
    sv = {
        "name": "weekly-brief",
        "description": "A one-page, sourced brief on the past week's news about a topic.",
        "inputs": [{"name": "topic", "description": "what the brief is about", "required": True},
                   {"name": "week", "description": "ISO week", "required": False}],
        "acceptance": list(CRITERIA),
        "deliverable": {"description": "One markdown file", "format": "markdown", "max_words": 600},
        "budget": 22,
    }
    sv.update(over)
    return sv


@pytest.fixture
def svc_bp(tmp_path):
    """The research team offering one service: no needs.deliverable and no task (services only)."""
    (tmp_path / "deliverables").mkdir()
    bp = yaml.safe_load(RESEARCH.read_text())
    bp["needs"].pop("deliverable")
    bp.pop("task")
    bp["services"] = [service(deliverable={"description": "One markdown file", "format": "markdown", "max_words": 600,
                                           "path": str(tmp_path / "deliverables" / "briefs")})]
    return bp


@pytest.fixture
def empty_org(tmp_path):
    return Org.init(tmp_path / "org", "service blueprint tests", {"poll_seconds": 0.05})


# --------------------------------------------------------------------------------------------- CLI
def test_cli_plan_and_apply_with_services(svc_bp, tmp_path, empty_org, capsys):
    path = tmp_path / "svc.yaml"
    path.write_text(yaml.safe_dump(svc_bp, sort_keys=False))
    main(["--root", str(empty_org.root), "plan", str(path), "--allow-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Services (1), offered by lead" in out and "No first task" in out
    main(["--root", str(empty_org.root), "apply", str(path), "--allow-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "defined 1 service(s) of lead: weekly-brief" in out and "nothing runs yet" in out
    main(["--root", str(empty_org.root), "request", "weekly-brief", "--input", "topic=ai"])
    assert "-> lead (service weekly-brief, budget 22)" in capsys.readouterr().out
