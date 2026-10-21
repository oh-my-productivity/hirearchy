"""``FsTeamActivity``: the newest message or run in the files of a team, from the names and the modification times."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hirearchy.kernel import OrgPaths
from hirearchy.progress._activity import FsTeamActivity
from hirearchy.progress._ports import TeamActivity


T = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def put(root: Path, rel: str, text: str = "x") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def stamp(offset: float) -> str:
    return f"{T + timedelta(seconds=offset):%Y%m%dT%H%M%S%f}"


def test_it_is_a_team_activity(tmp_path: Path) -> None:
    assert isinstance(FsTeamActivity(OrgPaths(tmp_path)), TeamActivity)


def test_a_team_that_did_nothing_has_no_activity(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    assert FsTeamActivity(OrgPaths(tmp_path)).newest(["ceo", "ceo/eng"]) is None
    assert FsTeamActivity(OrgPaths(tmp_path)).newest([]) is None


def test_the_newest_name_of_the_four_mailboxes_of_any_agent_wins(tmp_path: Path) -> None:
    put(tmp_path, f"ceo/inbox/{stamp(10)}-root-aaaa.md")
    put(tmp_path, f"ceo/read/{stamp(30)}-root-bbbb.md")
    put(tmp_path, f"ceo/sent/{stamp(20)}-ceo-cccc.md")
    put(tmp_path, f"ceo/eng/inflight/{stamp(40)}-ceo-dddd.md")
    put(tmp_path, f"ceo/eng/outbox/{stamp(90)}-ceo-eeee.md")  # not a mailbox
    assert FsTeamActivity(OrgPaths(tmp_path)).newest(["ceo", "ceo/eng"]) == T + timedelta(seconds=40)
    assert FsTeamActivity(OrgPaths(tmp_path)).newest(["ceo"]) == T + timedelta(seconds=30)


def test_hidden_files_and_names_that_are_no_time_do_not_count(tmp_path: Path) -> None:
    put(tmp_path, f"ceo/inbox/.tmp-{stamp(50)}-x.md")
    put(tmp_path, "ceo/inbox/notes.md")
    put(tmp_path, f"ceo/read/{stamp(5)}-root-aaaa.md")
    assert FsTeamActivity(OrgPaths(tmp_path)).newest(["ceo"]) == T + timedelta(seconds=5)


def test_the_last_write_of_a_run_log_counts_as_activity(tmp_path: Path) -> None:
    log = put(tmp_path, f"ceo/runs/{stamp(100)}.log")
    os.utime(log, (T.timestamp() + 160, T.timestamp() + 160))
    hidden = put(tmp_path, "ceo/runs/.pending.log")
    os.utime(hidden, (T.timestamp() + 900, T.timestamp() + 900))
    put(tmp_path, "ceo/runs/notes.txt")
    put(tmp_path, f"ceo/read/{stamp(20)}-root-aaaa.md")
    assert FsTeamActivity(OrgPaths(tmp_path)).newest(["ceo"]) == T + timedelta(seconds=160)
