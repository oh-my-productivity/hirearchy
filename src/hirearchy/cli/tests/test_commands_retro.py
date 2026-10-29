"""``hirearchy retro [--since] [--json]``: the brief at the terminal."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.cli._commands_retro import RetroCommand
from hirearchy.retro import Brief, brief_json, render_brief
from hirearchy.retro.testing import FixedRetroBriefs

from ._support import Fixture, go

BRIEF = Brief("B1", datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc), None, "since the organization started", 3, 3)


def test_hirearchy_retro_prints_the_brief(tmp_path: Path) -> None:
    f, fixed = Fixture(tmp_path), FixedRetroBriefs(BRIEF)
    go(RetroCommand(f.session, lambda: fixed, f.out), "retro")
    assert f.session.calls == [("open", False)] and f.out.stdout == render_brief(BRIEF) + "\n" and fixed.calls == [None]  # read-only: nothing is announced


def test_json_prints_brief_json(tmp_path: Path) -> None:
    f, fixed = Fixture(tmp_path), FixedRetroBriefs(BRIEF)
    go(RetroCommand(f.session, lambda: fixed, f.out), "retro", "--json", "--since", "2026-11-01")
    assert json.loads(f.out.stdout) == brief_json(BRIEF) and fixed.calls == [datetime(2026, 11, 1).astimezone()]


def test_a_bad_since_exits_2_with_the_refusal(tmp_path: Path) -> None:
    f, fixed = Fixture(tmp_path), FixedRetroBriefs(BRIEF)
    with pytest.raises(SystemExit) as info:
        go(RetroCommand(f.session, lambda: fixed, f.out), "retro", "--since", "soon")
    assert info.value.code == 2 and fixed.calls == []
    assert f.out.stderr == "refused: since must be a date (2026-11-02), a datetime with offset or a message id: soon. Nothing was read.\n"
