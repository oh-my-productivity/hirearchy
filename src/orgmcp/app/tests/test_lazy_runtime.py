"""The perf guard of ``Org(root)`` (ARCHITECTURE.md 6.2 and 10.1 risk 2): a runtime builds a port when it is first asked for it.

Wall time is noisy on a loaded machine, so the guard counts instead: how many ports a construction builds, how many providers it
registers, which ports a call path builds. A timing test with the budget "<= 1.2x main" exists too, but only runs on request
(``ORGMCP_RUN_PERF=1 pytest -m perf``).
"""

from __future__ import annotations

import dataclasses
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import pytest

from orgmcp.app import Org, wiring
from orgmcp.app._builder import Builder, DependencyCycle
from orgmcp.app.runtime import OrgRuntime
from orgmcp.kernel import Clock

FEW = 1  # what a construction may resolve before any attribute is used: at most the process resources


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return Org.init(tmp_path / "org", "mission").root


@pytest.fixture
def resolved(monkeypatch: pytest.MonkeyPatch) -> list[type]:
    """Every port that ``Builder.get`` is asked for (nested requests of providers included), in order."""
    asked: list[type] = []
    original = Builder.get

    def counting(self: Builder, port: type) -> object:
        asked.append(port)
        return original(self, port)

    monkeypatch.setattr(Builder, "get", counting)
    return asked


@pytest.mark.xfail(strict=True, reason="red: R-perf-runtime")
def test_constructing_an_org_resolves_no_port(root: Path, resolved: list[type]) -> None:
    Org(root)
    assert len(resolved) <= FEW


@pytest.mark.xfail(strict=True, reason="red: R-perf-runtime")
def test_opening_a_runtime_resolves_no_port(root: Path, resolved: list[type]) -> None:
    wiring.open_runtime(root)
    assert len(resolved) <= FEW


@pytest.mark.xfail(strict=True, reason="red: R-perf-runtime")
def test_opening_a_runtime_registers_no_provider_after_the_first(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wiring.open_runtime(root)  # the providers of the process are collected once
    registered: list[type] = []
    original = Builder.provide
    monkeypatch.setattr(Builder, "provide", lambda self, port, factory: (registered.append(port), original(self, port, factory))[1])
    for _ in range(3):
        Org(root)
    assert registered == []


@pytest.mark.xfail(strict=True, reason="red: R-perf-runtime")
def test_a_call_path_builds_only_the_ports_it_uses(root: Path, resolved: list[type]) -> None:
    org = Org(root)
    org.messages("ceo", "inbox")
    assert len(set(resolved)) <= 20 < len(wiring.runtime_ports()) // 5


def test_a_port_is_built_once_per_runtime(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    assert runtime.clock is runtime.clock and runtime.mailbox is runtime.mailbox and runtime.events is runtime.events


def test_the_providers_of_one_port_see_the_same_collaborators(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    assert runtime.ids is not None and runtime.mailbox is not None
    assert wiring.open_runtime(root).clock is not runtime.clock  # per runtime, not per process
    assert wiring.open_runtime(root).resources is runtime.resources  # per process


def test_an_override_wins_whenever_the_port_is_first_asked_for(root: Path) -> None:
    class Fixed(Clock):
        def now(self):  # type: ignore[no-untyped-def]
            raise AssertionError("unused")

    fixed = Fixed()
    runtime = wiring.open_runtime(root, {Clock: fixed})
    assert runtime.ids is not None  # builds a port that depends on the clock first
    assert runtime.clock is fixed


def test_an_unknown_attribute_is_still_an_attribute_error(root: Path) -> None:
    with pytest.raises(AttributeError):
        wiring.open_runtime(root).not_a_port  # type: ignore[attr-defined]  # noqa: B018


def test_replace_keeps_the_ports_that_were_not_replaced(root: Path) -> None:
    """The dashboard decorates a runtime with ``dataclasses.replace``: the other ports are the very objects of the original."""
    runtime = wiring.open_runtime(root)
    clock = runtime.clock
    fixed_events = object()
    other = dataclasses.replace(runtime, events=fixed_events)
    assert other.events is fixed_events and other.clock is clock and other.mailbox is runtime.mailbox


class Widget(Protocol):
    def spin(self) -> int: ...


class Gadget(Protocol):
    def widget(self) -> Widget: ...


class _Widget(Widget):
    def spin(self) -> int:
        return 1


@dataclasses.dataclass(frozen=True)
class _LaterPart:  # a part that a later step adds: no edit of runtime.py or wiring.py
    widget: Widget
    gadget: Gadget


@dataclasses.dataclass(frozen=True, init=False)
class _Bigger(OrgRuntime, _LaterPart):
    pass


@pytest.mark.xfail(strict=True, reason="red: R-perf-runtime")
def test_a_part_added_later_is_resolved_like_the_others(tmp_path: Path) -> None:
    builder = Builder(tmp_path)

    class _Gadget(Gadget):
        def __init__(self, widget: Widget) -> None:
            self._widget = widget

        def widget(self) -> Widget:
            return self._widget

    builder.provide(Widget, lambda b: _Widget())
    builder.provide(Gadget, lambda b: _Gadget(b.get(Widget)))
    bigger = _Bigger.lazy(builder)
    assert bigger.root == tmp_path
    assert bigger.gadget.widget() is bigger.widget and bigger.widget.spin() == 1


@pytest.mark.xfail(strict=True, reason="red: R-perf-runtime")
def test_a_dependency_cycle_is_reported_when_the_port_is_asked_for(tmp_path: Path) -> None:
    builder = Builder(tmp_path)
    builder.provide(Widget, lambda b: b.get(Gadget).widget())  # type: ignore[return-value]
    builder.provide(Gadget, lambda b: b.get(Widget))  # type: ignore[arg-type,return-value]
    bigger = _Bigger.lazy(builder)  # building the runtime is fine
    with pytest.raises(DependencyCycle, match="Widget -> Gadget -> Widget"):
        bigger.widget


# ------------------------------------------------------------------------------------------------------------ the emit hot path


class _CountingLayout:
    def __init__(self, root: Path) -> None:
        self._root = root
        self.reads = 0

    @property
    def root(self) -> Path:
        self.reads += 1
        return self._root


@pytest.mark.xfail(strict=True, reason="red: R-perf-runtime")
def test_the_document_stamp_does_not_rebuild_the_path_per_call(tmp_path: Path) -> None:
    from orgmcp.settings._stamp import FsOrgDocumentStamp

    (tmp_path / "ORG.md").write_text("x", encoding="utf-8")
    layout = _CountingLayout(tmp_path)
    stamps = FsOrgDocumentStamp(layout)  # type: ignore[arg-type]
    layout.reads = 0
    for _ in range(3):
        stamps.stamp()
    assert layout.reads == 0


def test_an_edit_of_org_md_is_still_seen_per_event(root: Path) -> None:
    org = Org(root)
    org.emit("first")
    text = (root / "ORG.md").read_text(encoding="utf-8")
    (root / "ORG.md").write_text(text.replace("events: true", "events: false"), encoding="utf-8")
    before = sum(p.stat().st_size for p in (root / ".runtime" / "events").rglob("*.jsonl"))
    org.emit("second")
    assert sum(p.stat().st_size for p in (root / ".runtime" / "events").rglob("*.jsonl")) == before


# ----------------------------------------------------------------------------------------------------------------- timing (opt-in)


def _best(fn: Callable[[], object], rounds: int = 7, n: int = 2000) -> float:
    best = float("inf")
    for _ in range(rounds):
        started = time.perf_counter()
        for _ in range(n):
            fn()
        best = min(best, (time.perf_counter() - started) / n)
    return best


@pytest.mark.perf
@pytest.mark.skipif(not os.environ.get("ORGMCP_RUN_PERF"), reason="timing test: ORGMCP_RUN_PERF=1 pytest -m perf")
def test_org_construction_costs_what_main_cost(root: Path) -> None:
    """Main's ``Org.__init__`` was a path resolution and one ``is_file``; the budget is 1.2x of that (measured in this process, interleaved,
    best of 7, so that a loaded machine moves both sides)."""

    def main_equivalent() -> object:
        resolved = Path(root).expanduser().resolve()
        return (resolved / "ORG.md").is_file()

    ratio = min(_best(lambda: Org(root)) / _best(main_equivalent) for _ in range(3))
    assert ratio <= 1.2, f"Org(root) is {ratio:.2f}x the work of main's constructor"
