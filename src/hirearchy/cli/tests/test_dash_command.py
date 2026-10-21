"""``dash``: the organization is named by the global ``--root`` or by the one after the command; on a terminal it runs the dashboard (Textual is imported only then);
``--once`` and a missing terminal print the snapshot (characterization over the real command line)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from testkit.cli_world import main
from hirearchy.kernel import ROOT

from ._org import Org, facade


@pytest.fixture
def org(tmp_path: Path) -> Org:
    org = facade().init(tmp_path / "org", "A mission.")
    org.hire(ROOT, "ceo", "Chief", "Run it.")
    return org


def test_the_root_may_follow_the_command(org: Org, capsys: pytest.CaptureFixture[str]) -> None:
    main(["dash", "--root", str(org.root), "--once"])
    after = capsys.readouterr().out
    main(["--root", str(org.root), "dash", "--once"])
    assert after == capsys.readouterr().out and "ceo" in after


def test_the_root_after_the_command_wins_over_the_global_one(org: Org, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    other = facade().init(tmp_path / "other", "Another.")
    main(["--root", str(other.root), "dash", "--root", str(org.root), "--once"])
    assert "ceo" in capsys.readouterr().out


def test_the_dashboard_of_a_directory_that_is_no_organization_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit:
        main(["dash", "--root", str(tmp_path / "nowhere"), "--once"])
    assert exit.value.code == 1 and "not an organization" in capsys.readouterr().err


def test_on_a_terminal_the_dashboard_runs_with_the_root_and_the_interval(org: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    calls: list[tuple[Path, float]] = []
    launcher = SimpleNamespace(run_dashboard=lambda root, interval=2.0: calls.append((root, interval)))  # (the launcher of the composition root)

    class Tty(io.StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", Tty())
    monkeypatch.setattr("sys.stdout", Tty())
    monkeypatch.setattr("hirearchy.app.wire_dashboard.dashboard_launcher", lambda screens=None: launcher)
    main(["--root", str(org.root), "dash", "--interval", "7"])
    assert calls == [(org.root, 7.0)]


def test_no_other_command_imports_textual_or_the_mcp_framework(org: Org) -> None:
    code = textwrap.dedent(f"""
        import sys
        from hirearchy import main
        for argv in (["status"], ["dash", "--once"], ["obs", "now"], ["health"], ["check"], ["progress"], ["services"]):
            main(["--root", {str(org.root)!r}, *argv])
        bad = [m for m in ("textual", "mcp.server.fastmcp", "hirearchy.dashboard") if m in sys.modules]
        print("LOADED", bad)
    """)
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines()[-1] == "LOADED []", done.stdout[-500:]
