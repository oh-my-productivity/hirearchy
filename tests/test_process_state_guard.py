"""The guard that makes a test which leaks process-global state (``Message.load``, the parse cache, the patch points of ``orgmcp.core``,
the process resources) fail by itself, and put the state back, instead of breaking a later test of ``orgmcp.app``."""

from __future__ import annotations

import pytest
from testkit import process_state
from testkit.process_state import ProcessState

from orgmcp import core
from orgmcp.app import _compat, wiring
from orgmcp.kernel import Message


def test_nothing_differs_from_itself() -> None:
    state = ProcessState.capture()
    assert ProcessState.capture().leaks_since(state) == []


@pytest.mark.parametrize("name", process_state.CORE_NAMES)
def test_a_replaced_core_attribute_is_named_and_restored(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    before = ProcessState.capture()
    monkeypatch.setattr(core, name, object())
    assert ProcessState.capture().leaks_since(before) == [f"core.{name}"]
    process_state.restore(before)
    assert ProcessState.capture().leaks_since(before) == [] and getattr(core, name) is before.values[f"core.{name}"]


def test_a_replaced_message_load_is_named_and_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    before = ProcessState.capture()
    monkeypatch.setattr(Message, "load", classmethod(lambda cls, path: None), raising=False)
    assert ProcessState.capture().leaks_since(before) == ["Message.load"]
    process_state.restore(before)
    assert vars(Message)["load"].__func__.__module__ == "orgmcp.app._compat"


def test_replaced_process_resources_are_named_and_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    before = ProcessState.capture()
    monkeypatch.setattr(wiring, "_process", wiring.new_process_resources())
    assert ProcessState.capture().leaks_since(before) == ["wiring._process", "resources.message_parser", "message_parser.cache"]
    process_state.restore(before)
    assert wiring.process_resources().message_parser.cache is core._PARSED


def test_the_adapters_switch_is_named_and_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    before = ProcessState.capture()
    monkeypatch.setattr(_compat, "ENABLED", False)
    assert ProcessState.capture().leaks_since(before) == ["_compat.ENABLED"]
    process_state.restore(before)
    assert _compat.ENABLED is True


def test_a_leaking_test_fails_by_itself_and_the_state_is_back() -> None:
    before = ProcessState.capture()
    original = core._PARSED
    core._PARSED = {}  # not through monkeypatch: nothing undoes it
    try:
        with pytest.raises(pytest.fail.Exception, match=r"some/test_x.py::test_leaks left process-global state replaced: core._PARSED"):
            process_state.verify(before, "some/test_x.py::test_leaks")
        assert core._PARSED is original is wiring.process_resources().message_parser.cache  # put back: the next test is not affected
    finally:
        core._PARSED = original
    process_state.verify(before, "clean")  # nothing left over: no failure
