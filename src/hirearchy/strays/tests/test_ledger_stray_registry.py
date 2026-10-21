"""``LedgerStrayRegistry``: what it asks of the ledger store and the tool naming, apart from the contract."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from hirearchy.access import ToolNaming
from hirearchy.kernel import JsonObject
from hirearchy.kernel.testing import MemoryLedgerStore
from hirearchy.strays import StrayRegistry
from hirearchy.strays._registry import LedgerStrayRegistry


class Naming(ToolNaming):
    """Names the write tool as it is told, and runs ``on_ask`` (to look at the ledger at that moment) when asked."""

    def __init__(self, write: str = "org_write", on_ask: Callable[[], None] = lambda: None) -> None:
        self.write = write
        self.on_ask = on_ask
        self.asked: list[str] = []

    def tool_names(self, addr: str) -> dict[str, str]:
        self.asked.append(addr)
        self.on_ask()
        return {"read": "read", "write": self.write}


class Ledgers(MemoryLedgerStore):
    """Remembers what was asked of the store."""

    def __init__(self) -> None:
        super().__init__()
        self.reads: list[str] = []
        self.writes: list[tuple[str, JsonObject]] = []

    def read(self, name: str) -> JsonObject:
        self.reads.append(name)
        return super().read(name)

    def write(self, name: str, data: JsonObject) -> None:
        self.writes.append((name, data))
        super().write(name, data)


def test_it_is_a_stray_registry() -> None:
    assert isinstance(LedgerStrayRegistry(Ledgers(), Naming()), StrayRegistry)


def test_a_record_reads_and_writes_the_strays_ledger_once() -> None:
    ledgers = Ledgers()
    LedgerStrayRegistry(ledgers, Naming()).record("dev", ["/a"])
    assert ledgers.reads == ["strays"] and ledgers.writes == [("strays", {"dev": {"paths": ["/a"], "told": False}})]


def test_a_record_after_the_notice_writes_nothing() -> None:
    ledgers = Ledgers()
    registry = LedgerStrayRegistry(ledgers, Naming())
    registry.record("dev", ["/a"])
    registry.take_notice("dev")
    ledgers.writes.clear()
    registry.record("dev", ["/b"])
    assert ledgers.writes == []


def test_a_notice_is_written_with_the_tool_name_of_that_agent() -> None:
    ledgers, naming = Ledgers(), Naming(write="write")
    registry = LedgerStrayRegistry(ledgers, naming)
    registry.record("dev", ["/a"])
    assert "`@hirearchy/write`" in registry.take_notice("dev") and naming.asked == ["dev"]


def test_nothing_to_tell_asks_for_no_tool_name_and_writes_nothing() -> None:
    ledgers, naming = Ledgers(), Naming()
    assert LedgerStrayRegistry(ledgers, naming).take_notice("dev") == ""
    assert naming.asked == [] and ledgers.writes == []


def test_the_agent_is_marked_told_before_the_name_of_the_tool_is_asked() -> None:
    ledgers = Ledgers()
    seen: list[object] = []
    naming = Naming(on_ask=lambda: seen.append(ledgers.read("strays")["dev"]))
    registry = LedgerStrayRegistry(ledgers, naming)
    registry.record("dev", ["/a"])
    registry.take_notice("dev")
    assert seen == [{"paths": ["/a"], "told": True}]


def test_an_agent_whose_tool_name_cannot_be_found_is_still_marked_told() -> None:
    class Missing(ToolNaming):
        def tool_names(self, addr: str) -> dict[str, str]:
            raise FileNotFoundError(addr)

    ledgers = Ledgers()
    registry = LedgerStrayRegistry(ledgers, Missing())
    registry.record("dev", ["/a"])
    with pytest.raises(FileNotFoundError):
        registry.take_notice("dev")
    assert ledgers.read("strays") == {"dev": {"paths": ["/a"], "told": True}}
