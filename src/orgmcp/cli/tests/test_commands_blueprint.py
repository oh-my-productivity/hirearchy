"""``plan`` and ``apply`` over a fake loader, validator, renderer and applier."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.blueprint import Issue
from orgmcp.cli._commands_blueprint import ApplyCommand, PlanCommand
from orgmcp.kernel import OrgError

from ._fakes import FakeBlueprints, new_blueprints
from ._support import Fixture, go

pytestmark = pytest.mark.xfail(strict=True, reason="red: D-cli")

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
