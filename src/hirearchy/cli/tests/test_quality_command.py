"""``hirearchy quality [service] [--json]``: the text of the quality view, one service of it, or its data as JSON (0b 9.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hirearchy.cli._commands_views import QualityCommand
from hirearchy.kernel import ROOT, OrgError
from hirearchy.progress.testing import FixedQualityReport
from hirearchy.reflection import ServiceRecord

from ._support import Fixture, go

BRIEF = ServiceRecord("ceo", "weekly-brief", ROOT, "human", contract=1, budget=10)
OTHER = ServiceRecord("ops", "daily-digest", ROOT, "human", contract=1, budget=6)
ROOT_RECORD = ServiceRecord("", "", ROOT, "human")


def command(f: Fixture, report: FixedQualityReport) -> QualityCommand:
    return QualityCommand(f.session, lambda: report, f.out)


def test_quality_prints_the_report_text(tmp_path: Path) -> None:
    f, report = Fixture(tmp_path), FixedQualityReport([BRIEF, OTHER, ROOT_RECORD])
    go(command(f, report), "quality")
    assert f.session.calls == [("open", False)] and report.calls == [("quality_text", None)]
    assert f.out.stdout.startswith("Quality of the work you asked for (") and f.out.stdout.endswith("Blocked tasks moved past without a verdict: none.\n")
    assert "weekly-brief (offered by ceo;" in f.out.stdout and "daily-digest (offered by ops;" in f.out.stdout


def test_quality_service_prints_one_block(tmp_path: Path) -> None:
    f, report = Fixture(tmp_path), FixedQualityReport([BRIEF, OTHER, ROOT_RECORD])
    go(command(f, report), "quality", "weekly-brief")
    assert report.calls == [("quality_text", "weekly-brief")]
    assert "weekly-brief (offered by ceo;" in f.out.stdout and "daily-digest" not in f.out.stdout and "One-off tasks" not in f.out.stdout


def test_quality_json_is_sorted_indented_ascii_with_a_newline(tmp_path: Path) -> None:
    f, report = Fixture(tmp_path), FixedQualityReport([ServiceRecord("ceo", "caf\u00e9", ROOT, "human", contract=1, budget=10), ROOT_RECORD])
    go(command(f, report), "quality", "--json")
    assert report.calls == [("quality_data", None)]
    out = f.out.stdout
    assert out == json.dumps(json.loads(out), indent=2, sort_keys=True) + "\n"
    assert "caf\\u00e9" in out and out.isascii() and out.startswith('{\n  "moved_past": [],')
    go(command(f, report), "quality", "caf\u00e9", "--json")
    assert report.calls[-1] == ("quality_data", "caf\u00e9")


def test_an_unknown_service_exits_as_other_cli_errors(org, capsys) -> None:  # type: ignore[no-untyped-def]
    from testkit.cli_world import main

    with pytest.raises(SystemExit) as info:
        main(["--root", str(org.root), "quality", "nope"])
    assert info.value.code == 1
    assert capsys.readouterr().err.startswith("error: no service named `nope`: the services are none. Call quality() without a service for everything.")


def test_no_organization_is_the_clis_error(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    from testkit.cli_world import main

    with pytest.raises(SystemExit) as info:
        main(["--root", str(tmp_path / "nowhere"), "quality"])
    assert info.value.code == 1 and capsys.readouterr().err.startswith("error: ")


def test_a_report_that_fails_is_the_error_of_the_command(tmp_path: Path) -> None:
    f = Fixture(tmp_path)
    with pytest.raises(OrgError, match="no service named `x`"):
        go(command(f, FixedQualityReport()), "quality", "x")
