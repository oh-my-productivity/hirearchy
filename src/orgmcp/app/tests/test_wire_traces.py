"""``wire_traces``: the runtime has the two trace ports, built from the mailboxes and the agent directory of the runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory
from orgmcp.app import wiring
from orgmcp.kernel import Message
from orgmcp.traces import TraceLookup, TraceStamper
from orgmcp.traces._lookup import MailboxTraceLookup
from orgmcp.traces._stamper import RuleTraceStamper

RED = pytest.mark.xfail(strict=True, reason="red: B-traces")


class FixedLookup(TraceLookup):
    """A lookup that knows one context."""

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        return None

    def open_task_traces(self, addr: str) -> list[str | None]:
        return []

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        return "FIXED", "batch", []


@RED
def test_the_runtime_has_the_trace_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.trace_lookup, MailboxTraceLookup) and isinstance(runtime.trace_lookup, TraceLookup)  # type: ignore[attr-defined]
    assert isinstance(runtime.trace_stamper, RuleTraceStamper) and isinstance(runtime.trace_stamper, TraceStamper)  # type: ignore[attr-defined]


@RED
def test_building_the_trace_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.trace_lookup.trace_of("ceo", "x") is None  # type: ignore[attr-defined]
    assert list(tmp_path.iterdir()) == []


@RED
def test_the_lookup_reads_the_mailboxes_and_the_directory_of_the_runtime(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    (tmp_path / "ceo" / "AGENT.md").write_text("---\nrole: Chief\n---\n# Role: Chief\n\nRun it.\n", encoding="utf-8")
    task = Message(sender="root", to="ceo", type="task", body="b", title="t", id="20260101T000000000001-root-aaaa", trace="T1")
    (tmp_path / "ceo" / "inbox" / f"{task.id}.md").write_text(task.to_text(), encoding="utf-8")
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.trace_lookup.trace_of("ceo", task.id) == "T1"  # type: ignore[attr-defined]
    assert runtime.trace_lookup.open_task_traces("ceo") == ["T1"]  # type: ignore[attr-defined]
    assert runtime.trace_lookup.open_task_traces("nobody") == []  # type: ignore[attr-defined]


@RED
def test_the_stamper_stamps_with_the_lookup_of_the_runtime(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path, {TraceLookup: FixedLookup()})
    msg = Message(sender="ceo", to="root", type="note", body="b", id="20260101T000000000002-ceo-aaaa")
    assert runtime.trace_stamper.stamp(msg) == ("batch", []) and msg.trace == "FIXED"  # type: ignore[attr-defined]


@RED
def test_the_lookup_asks_the_directory_of_the_runtime(tmp_path: Path) -> None:
    class Nobody(AgentDirectory):
        def exists(self, addr: str) -> bool:
            return False

        def require(self, addr: str) -> str:
            return addr

        def children(self, addr: str) -> list[str]:
            return []

        def agents(self) -> list[str]:
            return []

        def subtree(self, addr: str) -> list[str]:
            return [addr]

    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    (tmp_path / "ceo" / "AGENT.md").write_text("---\nrole: Chief\n---\n# Role: Chief\n\nRun it.\n", encoding="utf-8")
    task = Message(sender="root", to="ceo", type="task", body="b", title="t", id="20260101T000000000001-root-aaaa", trace="T1")
    (tmp_path / "ceo" / "inbox" / f"{task.id}.md").write_text(task.to_text(), encoding="utf-8")
    runtime = wiring.open_runtime(tmp_path, {AgentDirectory: Nobody()})
    assert runtime.trace_lookup.open_task_traces("ceo") == []  # type: ignore[attr-defined]


@RED
def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    fake = FixedLookup()
    runtime = wiring.open_runtime(tmp_path, {TraceLookup: fake})
    assert runtime.trace_lookup is fake and runtime.trace_stamper is not fake  # type: ignore[attr-defined]


@RED
def test_every_runtime_has_its_own_trace_ports(tmp_path: Path) -> None:
    first, second = wiring.open_runtime(tmp_path), wiring.open_runtime(tmp_path)
    assert first.trace_lookup is not second.trace_lookup and first.trace_stamper is not second.trace_stamper  # type: ignore[attr-defined]
