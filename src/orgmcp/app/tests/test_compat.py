"""The patch-point adapters: what tests replace on ``orgmcp.core`` stays in force for code that lives in ``orgmcp.app``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orgmcp import core
from orgmcp.app import _compat, wiring
from orgmcp.kernel._system import FsAtomicWriter, SystemClock

FIXED = datetime(2031, 5, 6, 7, 8, 9, tzinfo=timezone.utc)


def test_utcnow_follows_a_replaced_core_utcnow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "utcnow", lambda: FIXED)
    assert _compat.utcnow() == FIXED
    assert _compat.PatchPointClock().now() == FIXED


def test_utcnow_is_the_real_clock_otherwise() -> None:
    before = datetime.now(timezone.utc)
    assert before <= _compat.utcnow() <= before + timedelta(seconds=5)


def test_the_patch_point_clock_keeps_the_other_clock_methods_of_the_system() -> None:
    clock = _compat.PatchPointClock()
    assert abs(clock.time() - datetime.now(timezone.utc).timestamp()) < 5 and clock.monotonic() >= 0
    clock.sleep(0)


def test_atomic_write_follows_a_replaced_core_atomic_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(core, "atomic_write", lambda path, text: calls.append((path, text)))
    target = tmp_path / "a.txt"
    _compat.atomic_write(target, "one")
    _compat.PatchPointAtomicWriter().write(target, "two")
    assert calls == [(target, "one"), (target, "two")] and not target.exists()


def test_atomic_write_is_core_atomic_write_otherwise(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "a.txt"
    _compat.PatchPointAtomicWriter().write(target, "text")
    assert target.read_text(encoding="utf-8") == "text" and not [p for p in target.parent.iterdir() if p.name.startswith(".tmp-")]


def test_a_runtime_uses_the_adapters_while_they_are_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "utcnow", lambda: FIXED)
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.clock, _compat.PatchPointClock) and runtime.clock.now() == FIXED
    assert runtime.ids.message_id("ceo").startswith("20310506T070809000000-ceo-")
    assert isinstance(runtime.atomic_writer, _compat.PatchPointAtomicWriter)


def test_a_runtime_uses_the_plain_system_adapters_once_they_are_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_compat, "ENABLED", False)
    monkeypatch.setattr(core, "utcnow", lambda: FIXED)
    runtime = wiring.open_runtime(tmp_path)
    assert type(runtime.clock) is SystemClock and runtime.clock.now() != FIXED
    assert type(runtime.atomic_writer) is FsAtomicWriter


def test_the_process_parser_is_plain_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_compat, "ENABLED", False)
    assert type(wiring.new_process_resources().message_parser).__name__ == "CachingMessageParser"
