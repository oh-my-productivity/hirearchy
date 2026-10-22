"""``run`` over a real organization and the stub kiro-cli of the test fixture (it answers the readiness check and runs a V3 chat that starts and
finishes): one pass starts the run of the agent that has mail, waits for it and ends; the run leaves its log and its events; ``--until-done`` ends by itself when there is nothing to do; the two modes cannot be mixed."""

from __future__ import annotations

from pathlib import Path

import pytest

from testkit.cli_world import main
from hirearchy.kernel import ROOT

from ._events import read_events
from ._org import Org, facade


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = facade().init(tmp_path / "org", "A mission.", {"poll_seconds": 0.05})
    made.hire(ROOT, "ceo", "Chief", "Run it.", can_hire=True)
    made.delegate(ROOT, "ceo", "Ship it", "Ship the thing.", "It is shipped.", budget=5)
    return made


def test_one_pass_starts_the_run_waits_for_it_and_ends(org: Org, capsys: pytest.CaptureFixture[str]) -> None:
    main(["--root", str(org.root), "run", "--once"])
    assert capsys.readouterr().err == f"org: {org.root}\n"
    kinds = [e["kind"] for e in read_events(org.root) if str(e["kind"]).startswith(("scheduler.", "run."))]
    assert kinds[0] == "scheduler.start" and "run.start" in kinds and "run.end" in kinds and kinds[-1] == "scheduler.exit"
    assert list((org.root / "ceo" / "runs").glob("*.log"))
    (start,) = read_events(org.root, "scheduler.start")
    assert start["mode"] == "once"


def test_the_cap_on_runs_is_the_one_given(org: Org) -> None:
    main(["--root", str(org.root), "run", "--once", "--max-runs", "0"])
    assert read_events(org.root, "run.start") == []


def test_until_done_ends_when_nothing_is_left_and_says_why(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    quiet = facade().init(tmp_path / "quiet", "Nothing to do.")
    main(["--root", str(quiet.root), "run", "--until-done"])
    assert "scheduler exiting: finished: no open tasks" in capsys.readouterr().out


def test_until_done_and_once_are_different_modes(org: Org, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(org.root), "run", "--until-done", "--once"])
    err = capsys.readouterr().err
    assert exit.value.code == 1 and err.startswith(f"org: {org.root}\n") and "different modes" in err
    assert read_events(org.root, "scheduler.start") == []
