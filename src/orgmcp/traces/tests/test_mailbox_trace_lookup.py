"""``MailboxTraceLookup``: what it asks of its two collaborators, apart from the contract (``test_contract_trace_lookup``)."""

from __future__ import annotations

from pathlib import Path

from orgmcp.kernel import Message
from orgmcp.mail import MailboxReader
from orgmcp.traces import TraceLookup
from orgmcp.traces._lookup import MailboxTraceLookup
from orgmcp.traces._ports import AgentPresence

from orgmcp.traces.testing import TraceHarness, memory_traces

from ._support import put

class Presence(AgentPresence):
    """Says who exists, and remembers whom it was asked about."""

    def __init__(self, *agents: str) -> None:
        self.agents = set(agents)
        self.asked: list[str] = []

    def exists(self, addr: str) -> bool:
        self.asked.append(addr)
        return addr in self.agents


class CountingReader(MailboxReader):
    """The in-memory mailboxes that count what is read."""

    def __init__(self, inner: MailboxReader) -> None:
        self._inner = inner
        self.calls: list[tuple[str, str]] = []

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        self.calls.append(("messages", addr + ":" + ",".join(boxes)))
        return self._inner.messages(addr, *boxes)

    def received(self, addr: str) -> list[Message]:
        self.calls.append(("received", addr))
        return self._inner.received(addr)

    def sent(self, addr: str) -> list[Message]:
        self.calls.append(("sent", addr))
        return self._inner.sent(addr)

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        self.calls.append(("find_received", addr))
        return self._inner.find_received(addr, msg_id)

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        self.calls.append(("find_anywhere", f"{addr}:{msg_id}"))
        return self._inner.find_anywhere(addr, msg_id)

    def unread(self, addr: str) -> int:
        return self._inner.unread(addr)

    def has_inflight(self, addr: str) -> bool:
        return self._inner.has_inflight(addr)


def over(tmp_path: Path, *agents: str) -> tuple[MailboxTraceLookup, CountingReader, Presence, TraceHarness]:
    h = memory_traces(tmp_path)
    reader, presence = CountingReader(h.mail.reader), Presence(*agents)
    return MailboxTraceLookup(reader, presence), reader, presence, h


def test_it_is_a_trace_lookup(tmp_path: Path) -> None:
    lookup, _, _, _ = over(tmp_path)
    assert isinstance(lookup, TraceLookup)


def test_trace_of_is_one_lookup_by_name_in_the_mailbox_and_asks_nobody_whether_the_agent_exists(tmp_path: Path) -> None:
    lookup, reader, presence, h = over(tmp_path)
    msg_id = put(h, "ceo", "sent", 1, trace="T1")
    assert lookup.trace_of("ceo", msg_id) == "T1"
    assert reader.calls == [("find_anywhere", f"ceo:{msg_id}")] and presence.asked == []


def test_an_empty_id_is_answered_without_reading_anything(tmp_path: Path) -> None:
    lookup, reader, _, _ = over(tmp_path)
    assert lookup.trace_of("ceo", None) is None and lookup.trace_of("ceo", "") is None
    assert reader.calls == []


def test_open_task_traces_ask_the_directory_first_and_read_nothing_for_a_stranger(tmp_path: Path) -> None:
    lookup, reader, presence, h = over(tmp_path)
    put(h, "ceo", "inbox", 1, trace="T1")
    assert lookup.open_task_traces("ceo") == [] and presence.asked == ["ceo"] and reader.calls == []


def test_open_task_traces_of_an_agent_read_its_sent_and_received_boxes(tmp_path: Path) -> None:
    lookup, reader, presence, h = over(tmp_path, "ceo")
    put(h, "ceo", "inbox", 1, trace="T1")
    assert lookup.open_task_traces("ceo") == ["T1"]
    assert sorted(reader.calls) == [("received", "ceo"), ("sent", "ceo")]


def test_root_and_the_runtime_are_not_asked_about(tmp_path: Path) -> None:
    lookup, reader, presence, _ = over(tmp_path, "root", "runtime")
    assert lookup.open_task_traces("root") == [] and lookup.open_task_traces("runtime") == []
    assert lookup.context_trace("root") == (None, "ambiguous", []) and lookup.context_trace("runtime") == (None, "ambiguous", [])
    assert presence.asked == [] and reader.calls == []


def test_the_batch_is_the_inflight_box_and_only_for_an_agent_that_exists(tmp_path: Path) -> None:
    lookup, reader, _, h = over(tmp_path, "ceo")
    put(h, "ceo", "inflight", 1, trace="T1", kind="note")
    put(h, "ghost", "inflight", 2, trace="T2", kind="note")
    assert lookup.context_trace("ceo") == ("T1", "batch", [])
    assert lookup.context_trace("ghost") == (None, "ambiguous", [])
    assert ("messages", "ceo:inflight") in reader.calls and not any("ghost" in arg for _, arg in reader.calls)


def test_the_address_is_normalized_before_the_directory_is_asked(tmp_path: Path) -> None:
    lookup, _, presence, h = over(tmp_path, "ceo/eng")
    put(h, "ceo/eng", "inbox", 1, trace="T1")
    assert lookup.open_task_traces(" /ceo/eng/ ") == ["T1"] and presence.asked == ["ceo/eng"]
