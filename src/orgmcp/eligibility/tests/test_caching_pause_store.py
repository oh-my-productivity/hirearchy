"""``CachingPauseStore``: the dashboard's decorator (it replaces ``LenientOrg.paused``): a flag file is read again only when its mtime changed."""

from __future__ import annotations

from orgmcp.eligibility import PauseStore
from orgmcp.eligibility._caching import CachingPauseStore
from orgmcp.eligibility._ports import DirectoryProbe
from orgmcp.eligibility.testing import MemoryPauseStore
from orgmcp.kernel.testing import ListEventSink


class ScriptedProbe(DirectoryProbe):
    """The mtime of each flag file is what the test says (-1: no such file); every question is kept."""

    def __init__(self) -> None:
        self.times: dict[str, int] = {}
        self.asked: list[tuple[str, str]] = []

    def mtime(self, addr: str, name: str) -> int:
        self.asked.append((addr, name))
        return self.times.get(addr, -1)


class CountingStore(PauseStore):
    """A store that counts how often it was asked, over a fake."""

    def __init__(self) -> None:
        self.inner = MemoryPauseStore(ListEventSink())
        self.reads = 0

    def paused(self, addr: str) -> str | None:
        self.reads += 1
        return self.inner.paused(addr)

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        self.inner.pause(addr, reason, by)

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        self.inner.resume(addr, reason, by)


def build() -> tuple[CachingPauseStore, CountingStore, ScriptedProbe]:
    inner, probe = CountingStore(), ScriptedProbe()
    return CachingPauseStore(inner, probe), inner, probe


def test_without_a_flag_file_the_store_behind_is_not_asked() -> None:
    store, inner, probe = build()
    inner.inner.flags["ceo"] = "failures"  # the probe says there is no file, and the decorator believes it
    assert store.paused("ceo") is None and inner.reads == 0


def test_the_probe_is_asked_about_the_flag_file_of_the_normalized_address() -> None:
    store, _, probe = build()
    store.paused(" /ceo/eng/ ")
    assert probe.asked == [("ceo/eng", ".paused")]


def test_root_is_asked_as_root() -> None:
    store, _, probe = build()
    store.paused("")
    assert probe.asked == [("root", ".paused")]


def test_a_flag_file_is_read_once_while_its_mtime_stays() -> None:
    store, inner, probe = build()
    inner.inner.flags["ceo"] = "failures"
    probe.times["ceo"] = 100
    assert [store.paused("ceo") for _ in range(3)] == ["failures"] * 3
    assert inner.reads == 1


def test_a_flag_file_is_read_again_when_its_mtime_changed() -> None:
    store, inner, probe = build()
    inner.inner.flags["ceo"] = "failures"
    probe.times["ceo"] = 100
    store.paused("ceo")
    inner.inner.flags["ceo"] = "budget"
    probe.times["ceo"] = 101
    assert store.paused("ceo") == "budget" and inner.reads == 2


def test_a_flag_that_went_away_is_no_pause_any_more() -> None:
    store, inner, probe = build()
    inner.inner.flags["ceo"] = "failures"
    probe.times["ceo"] = 100
    store.paused("ceo")
    del probe.times["ceo"]
    assert store.paused("ceo") is None


def test_the_file_of_one_agent_does_not_answer_for_another() -> None:
    store, inner, probe = build()
    inner.inner.flags.update({"ceo": "failures", "cto": "budget"})
    probe.times.update({"ceo": 100, "cto": 100})
    assert (store.paused("ceo"), store.paused("cto")) == ("failures", "budget")


def test_pausing_and_resuming_go_to_the_store_behind() -> None:
    store, inner, _ = build()
    store.pause("ceo", "budget", by="runtime")
    assert inner.inner.flags == {"ceo": "budget"}
    store.resume("ceo", "back", by="runtime")
    assert inner.inner.flags == {}
