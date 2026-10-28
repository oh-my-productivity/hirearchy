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
    bp["task"]["acceptance"] = [c["text"] for c in bp["task"]["acceptance"]]  # plain strings, and none of the user's words
    del bp["needs"]["elicitation"]
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    (tmp_path / "bp.yaml").write_text(yaml.safe_dump(bp, sort_keys=False), encoding="utf-8")
    main(["plan", str(tmp_path / "bp.yaml"), "--allow-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "  1. Covers exactly Obsidian, Logseq, Joplin, Trilium and AnyType, and no other app.\n     my wording: your words for it were not recorded\n" in out
    assert "- task.acceptance[1]: criterion 1 does not say where it comes from: give from: <the user's exact words in needs.elicitation> or default: true." in out
    assert "- needs.elicitation: this plan records none of the user's words, so no criterion can show where it comes from." in out
    assert "Reply 'approve' or tell me what to change." in out  # warnings, not errors: the human applies their own file


def test_the_same_plan_keeps_warnings_at_the_terminal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Guard (design 10.1 step 3): over MCP a plan without sources is a draft; at the terminal the human applies their own file, so it stays a plan
    with warnings and applies."""
    import testkit
    import testkit.reach.yaml as yaml
    from testkit.cli_world import main
    from testkit.reach.hirearchy.core import Org

    bp = yaml.safe_load((testkit.REPO / "examples" / "blueprint-research.yaml").read_text())
    bp["task"]["acceptance"] = [c["text"] for c in bp["task"]["acceptance"]]
    del bp["needs"]["elicitation"]
    (tmp_path / "deliverables").mkdir()
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    (tmp_path / "bp.yaml").write_text(yaml.safe_dump(bp, sort_keys=False), encoding="utf-8")
    org = Org.init(tmp_path / "org", "terminal", {"poll_seconds": 0.05})
    main(["--root", str(org.root), "plan", str(tmp_path / "bp.yaml"), "--allow-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Warnings (" in out and "Errors (" not in out and "DRAFT" not in out and "criterion 1 does not say where it comes from" in out
    main(["--root", str(org.root), "apply", str(tmp_path / "bp.yaml"), "--allow-root", str(tmp_path)])
    assert "created 4 agents" in capsys.readouterr().out


# ------------------------------------------------------------------------------------------- an extension file (design 5.5: no new flag)


def extension_org(tmp_path: Path) -> object:
    from testkit.reach.hirearchy.core import ROOT, Org

    org = Org.init(tmp_path / "org", "terminal", {"poll_seconds": 0.05})
    org.hire(ROOT, "lead", "Lead", "Directs.", tools=["read"], can_hire=True, max_children=2)
    return org


def extension_file(tmp_path: Path, **sections: object) -> Path:
    import testkit.reach.yaml as yaml

    path = tmp_path / "change.yaml"
    path.write_text(yaml.safe_dump({"reason": "the user asked", "extend": sections}, sort_keys=False), encoding="utf-8")
    return path


def test_plan_of_an_extension_file_shows_the_change_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from testkit.cli_world import main

    org = extension_org(tmp_path)
    main(["--root", str(org.root), "plan", str(extension_file(tmp_path, limits=[{"agent": "lead", "max_children": 4}])), "--allow-root", str(tmp_path)])  # type: ignore[attr-defined]
    out = capsys.readouterr().out
    assert out.startswith("PLAN FOR YOU (a change to your organization)\nWhy: the user asked\n")
    assert "- lead: may have up to 4 direct reports (was 2), so it may add 4 worker(s) without asking you" in out
    assert "Nothing changes until you approve. Reply 'approve', or tell me what to change." in out and "Limit lead: max_children 2 -> 4" in out
    with pytest.raises(SystemExit) as refused:  # errors: the plan is printed as a draft and the exit is 1
        main(["--root", str(org.root), "plan", str(extension_file(tmp_path, limits=[{"agent": "ghost", "max_children": 4}])), "--allow-root", str(tmp_path)])  # type: ignore[attr-defined]
    assert refused.value.code == 1 and "DRAFT - NOT READY" in capsys.readouterr().out


def test_plan_of_an_extension_file_before_the_organization_exists_has_nothing_to_extend(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from testkit.cli_world import main

    with pytest.raises(SystemExit) as refused:
        main(["--root", str(tmp_path / "none"), "plan", str(extension_file(tmp_path, limits=[{"agent": "lead", "max_children": 4}]))])
    out = capsys.readouterr().out
    assert refused.value.code == 1 and "there is no organization yet, so there is nothing to extend" in out


def test_apply_of_an_extension_file_applies_it_without_a_plan_id(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from testkit.cli_world import main

    org = extension_org(tmp_path)
    path = extension_file(tmp_path, limits=[{"agent": "lead", "max_children": 4}], add_charter_lines=[{"agent": "lead", "line": "Cite the source."}])
    main(["--root", str(org.root), "apply", str(path), "--allow-root", str(tmp_path)])  # type: ignore[attr-defined]
    out = capsys.readouterr().out
    assert out.startswith("applied the change ") and "changed limits: lead" in out and out.rstrip().endswith("Nothing runs because of it.")
    meta, body = org.charter("lead")  # type: ignore[attr-defined]
    assert meta["max_children"] == 4 and "- Cite the source. [change " in body and "Your hiring limits were set by the user's change: up to 4" in body


def test_provenance_stays_warnings_at_the_terminal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Guard (design 10.1 step 3): an extension whose new service gives plain-string criteria and records no words is a plan with warnings at the terminal
    (over MCP it is a draft), and applies."""
    from testkit.cli_world import main

    org = extension_org(tmp_path)
    path = extension_file(tmp_path, add_services=[{
        "owner": "lead", "name": "weekly", "description": "A weekly note", "acceptance": ["Every row has a date."], "deliverable": {"description": "a note", "format": "markdown"},
    }])
    main(["--root", str(org.root), "plan", str(path), "--allow-root", str(tmp_path)])  # type: ignore[attr-defined]
    out = capsys.readouterr().out
    assert "my wording: your words for it were not recorded" in out and "Warnings (" in out and "Errors (" not in out and "DRAFT" not in out
    main(["--root", str(org.root), "apply", str(path), "--allow-root", str(tmp_path)])  # type: ignore[attr-defined]
    assert "defined 1 service(s): weekly of lead" in capsys.readouterr().out and org.service_names("lead") == ["weekly"]  # type: ignore[attr-defined]


def test_apply_hands_an_extension_to_the_extension_applier_and_a_full_blueprint_to_the_other(tmp_path: Path) -> None:
    from hirearchy.blueprint import ExtensionApplying

    class Applier(ExtensionApplying):
        def __init__(self) -> None:
            self.asked: list[tuple[object, str | None, object]] = []

        def apply(self, bp, *, plan_id, require_sources=False, allowed_roots=None):  # type: ignore[no-untyped-def]
            self.asked.append((dict(bp), plan_id, allowed_roots))
            return "applied the change x"

    f, bp, extensions = Fixture(tmp_path), new_blueprints(), Applier()
    bp.extension = {"reason": "r", "extend": {"limits": []}}
    command = ApplyCommand(f.session, lambda: bp, lambda: bp, f.out, lambda: extensions)
    go(command, "apply", "bp.yaml", "--allow-root", "/a")
    assert f.out.stdout == "applied the change x\n" and extensions.asked == [({"reason": "r", "extend": {"limits": []}}, None, ["/a"])]
    assert bp.names() == ["load"]  # the full applier was not asked
