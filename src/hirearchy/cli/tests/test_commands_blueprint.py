"""``plan`` and ``apply`` over a fake loader, validator, renderer and applier."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint import Issue
from hirearchy.cli._commands_blueprint import ApplyCommand, PlanCommand
from hirearchy.kernel import OrgError

from ._fakes import FakeBlueprints, new_blueprints
from ._support import Fixture, go


WARNING = Issue("warning", "needs.review", "review not decided")
ERROR = Issue("error", "agents[lead]", "unknown template")


def plan_world(tmp_path: Path, issues: list[Issue], exists: bool = True) -> tuple[Fixture, FakeBlueprints, PlanCommand]:
    f, bp = Fixture(tmp_path, exists), new_blueprints(issues)
    return f, bp, PlanCommand(f.session, lambda: bp, lambda: bp, lambda: bp, f.out)


def test_plan_prints_the_plan_of_a_blueprint_that_has_only_warnings(tmp_path: Path) -> None:
    f, bp, command = plan_world(tmp_path, [WARNING])
    go(command, "plan", "bp.yaml", "--allow-root", "/a", "--allow-root", "/b")
    assert f.session.calls == [("present", None)]  # (it changes nothing: no announcement)
    assert bp.last("load") == ((Path("bp.yaml"),), {})
    assert bp.last("validate")[1] == {"org_exists": True, "allowed_roots": ["/a", "/b"]}
    assert bp.last("render_plan")[1] == {"allowed_roots": ["/a", "/b"]}
    assert f.out.stdout == "# Plan for approval\nwarning: needs.review: review not decided\n"


def test_plan_with_errors_prints_the_plan_and_exits_1(tmp_path: Path) -> None:
    f, bp, command = plan_world(tmp_path, [ERROR, WARNING])
    with pytest.raises(SystemExit) as exit:
        go(command, "plan", "bp.yaml")
    assert exit.value.code == 1
    assert "error: agents[lead]: unknown template" in f.out.stdout


def test_plan_before_the_organization_exists_validates_against_the_defaults(tmp_path: Path) -> None:
    f, bp, command = plan_world(tmp_path, [], exists=False)
    go(command, "plan", "bp.yaml")
    assert bp.last("validate")[1] == {"org_exists": False, "allowed_roots": None}


def test_plan_of_a_missing_file_is_the_error_of_the_loader(tmp_path: Path) -> None:
    f, bp, command = plan_world(tmp_path, [])
    bp.refuse = OrgError("blueprint not found")
    with pytest.raises(OrgError):
        go(command, "plan", "nope.yaml")
    assert f.out.stdout == ""


def test_apply_announces_first_then_applies_what_it_loaded(tmp_path: Path) -> None:
    f, bp = Fixture(tmp_path), new_blueprints()
    go(ApplyCommand(f.session, lambda: bp, lambda: bp, f.out), "apply", "bp.yaml", "--allow-root", "/a")
    assert f.session.calls == [("open", True)]
    assert bp.names() == ["load", "apply"] and bp.last("apply") == (({"mission": "bp.yaml"},), {"allowed_roots": ["/a"]})
    assert f.out.stdout.splitlines()[0] == "created 2 agents: lead, lead/writer"
    assert f.out.stdout.splitlines()[1] == "task t-1 -> lead (budget 10)"


def test_apply_without_allowed_roots_passes_none(tmp_path: Path) -> None:
    f, bp = Fixture(tmp_path), new_blueprints()
    go(ApplyCommand(f.session, lambda: bp, lambda: bp, f.out), "apply", "bp.yaml")
    assert bp.last("apply")[1] == {"allowed_roots": None}


def test_plan_shows_the_my_wording_line_and_both_warnings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Design 10.1 step 4: at the terminal a plan whose criteria are plain strings and record none of the user's words says so, and warns."""
    import testkit
    import testkit.reach.yaml as yaml
    from testkit.cli_world import main

    bp = yaml.safe_load((testkit.REPO / "examples" / "blueprint-research.yaml").read_text())
    (tmp_path / "deliverables").mkdir()
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    (tmp_path / "bp.yaml").write_text(yaml.safe_dump(bp, sort_keys=False), encoding="utf-8")
    main(["plan", str(tmp_path / "bp.yaml"), "--allow-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "  1. Covers exactly Obsidian, Logseq, Joplin, Trilium and AnyType, and no other app.\n     my wording: your words for it were not recorded\n" in out
    assert "- task.acceptance[1]: criterion 1 does not say where it comes from: give from: <the user's exact words in needs.elicitation> or default: true." in out
    assert "- needs.elicitation: this plan records none of the user's words, so no criterion can show where it comes from." in out
    assert "Reply 'approve' or tell me what to change." in out  # warnings, not errors: the human applies their own file
