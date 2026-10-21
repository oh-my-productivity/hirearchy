"""``ToolCallRecorder``: the ``tool.call`` event of every call (ok, refused, unexpected), the argument summary without bodies, the tools added later, the order in
which the trace of a call is found, and the thread-local collection that the async ``progress`` tool does not reach (ARCHITECTURE.md 10.1, risk 12)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from hirearchy.kernel import OrgError
from hirearchy.kernel.testing import RecordedEvent
from hirearchy.mail.testing import MailHarness, memory_mailbox
from hirearchy.mcp_server._recorder import BatchCallTrace, ToolCallRecorder
from hirearchy.mcp_server.testing import MemoryBinding, NoTraces, agents_in
from hirearchy.telemetry.testing import MemoryEventSinks, StackTraceScope, json_argument_summarizer
from hirearchy.traces import TraceLookup

from ._support import call, fails

ROOT_DIR = Path("/memory/org")


class Traces(NoTraces):
    """The trace of message ``m1`` is ``T1``."""

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        return "T1" if msg_id == "m1" else None


def recorder(tmp_path: Path, binding: MemoryBinding | None = None, lookup: TraceLookup | None = None,
             mail: MailHarness | None = None) -> tuple[ToolCallRecorder, MemoryEventSinks, StackTraceScope]:
    sinks, scope = MemoryEventSinks(), StackTraceScope()
    binding = binding if binding is not None else MemoryBinding(ROOT_DIR, exists=True)
    agents, box = agents_in("ceo"), mail or memory_mailbox(tmp_path)
    from hirearchy.mcp_server._instructions import InstructionText

    trace = BatchCallTrace(InstructionText(binding), lambda: lookup or NoTraces(), lambda: agents, lambda: box.reader)
    return ToolCallRecorder(binding, sinks, scope, json_argument_summarizer(tmp_path), trace), sinks, scope


def events(sinks: MemoryEventSinks) -> list[RecordedEvent]:
    return sinks.events(ROOT_DIR)


def test_a_call_emits_its_event_with_actor_tool_duration_and_summary(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path)
    server = FastMCP("t")
    rec.instrument(server, "ceo")

    @server.tool()
    def delegate(to: str, goal: str, budget: int = 1) -> str:
        """Doc."""
        return "ok"

    assert call(server, "delegate", to="ceo/eng", goal="g" * 3000, budget=2) == "ok"
    (ev,) = events(sinks)
    assert (ev.kind, ev.actor, ev.proc) == ("tool.call", "ceo", "mcp")
    f = ev.fields
    assert f["tool"] == "delegate" and f["ok"] is True and f["error"] is None and f["error_type"] is None
    assert isinstance(f["ms"], float) and f["ms"] >= 0
    assert f["args"] == {"to": "ceo/eng", "budget": 2, "goal_chars": 3000}  # never a body


def test_a_refusal_is_recorded_and_still_raised_with_its_text(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path)
    server = FastMCP("t")
    rec.instrument(server, "ceo")

    @server.tool()
    def refuse() -> str:
        """Doc."""
        raise OrgError("you can only delegate to your direct reports")

    assert "you can only delegate to your direct reports" in fails(server, "refuse")
    (ev,) = events(sinks)
    assert ev.fields["ok"] is False and ev.fields["error_type"] == "OrgError" and ev.fields["error"] == "you can only delegate to your direct reports"


def test_an_unexpected_exception_is_recorded_by_class_and_an_empty_message_by_its_class_name(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path)
    server = FastMCP("t")
    rec.instrument(server, "ceo")

    @server.tool()
    def boom() -> str:
        """Doc."""
        return str(1 / 0)

    @server.tool()
    def silent() -> str:
        """Doc."""
        raise KeyError()

    fails(server, "boom")
    fails(server, "silent")
    first, second = events(sinks)
    assert first.fields["error_type"] == "ZeroDivisionError" and "division" in str(first.fields["error"])
    assert second.fields["error_type"] == "KeyError" and second.fields["error"] == "KeyError"


def test_an_error_text_is_clipped(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path)
    server = FastMCP("t")
    rec.instrument(server, "ceo")

    @server.tool()
    def long() -> str:
        """Doc."""
        raise OrgError("x" * 900)

    fails(server, "long")
    assert len(str(events(sinks)[0].fields["error"])) <= 500


def test_every_tool_registered_afterwards_is_recorded_with_its_own_name_and_the_name_it_was_given(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path)
    server = FastMCP("t")
    rec.instrument(server, "root")

    def read(path: str = ".") -> str:
        return path

    server.tool(name="org_read", description="d")(read)
    call(server, "org_read", path="a")
    assert events(sinks)[0].fields["tool"] == "org_read" and events(sinks)[0].fields["args"] == {"path": "a"}
    assert server._tool_manager.list_tools()[0].fn.__wrapped__ is read  # type: ignore[attr-defined]


def test_the_name_signature_and_docstring_of_a_tool_are_its_own(tmp_path: Path) -> None:
    rec, _, _ = recorder(tmp_path)
    server = FastMCP("t")
    rec.instrument(server, "ceo")

    @server.tool()
    def send(to: str, body: str, title: str = "") -> str:
        """Send a note."""
        return "sent"

    tool = server._tool_manager.list_tools()[0]
    assert tool.name == "send" and tool.description == "Send a note." and list(tool.parameters["properties"]) == ["to", "body", "title"]


def test_nothing_is_emitted_for_a_server_bound_to_no_path(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path, MemoryBinding(None))
    server = FastMCP("t")
    rec.instrument(server, "root")

    @server.tool()
    def ping() -> str:
        """Doc."""
        return "pong"

    assert call(server, "ping") == "pong" and sinks.sinks == {}


def test_a_sink_that_fails_does_not_change_the_result_of_the_call(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path)
    sinks.broken = True
    server = FastMCP("t")
    rec.instrument(server, "ceo")

    @server.tool()
    def ping() -> str:
        """Doc."""
        return "pong"

    assert call(server, "ping") == "pong"


def test_arguments_that_do_not_fit_the_signature_are_recorded_as_given(tmp_path: Path) -> None:
    rec, sinks, scope = recorder(tmp_path)

    def fn(a: int) -> str:
        return "x"

    wrapped = rec._recorded(fn, "fn", "ceo")  # noqa: SLF001
    with pytest.raises(TypeError):
        wrapped(1, 2, 3)  # type: ignore[call-arg]
    (ev,) = events(sinks)
    assert ev.fields["ok"] is False and ev.fields["args"] == {}


# --------------------------------------------------------------------------------------------- the trace of a call


def mailbox_with_batch(tmp_path: Path, *traces: str | None) -> MailHarness:
    box = memory_mailbox(tmp_path)
    box.agent("ceo")
    for n, trace in enumerate(traces):
        head = f"---\nsender: root\nto: ceo\ntype: task\nid: b{n}\ncreated: 2026-01-01T00:00:00+00:00\n" + (f"trace: {trace}\n" if trace else "")
        box.put(f"ceo/inflight/b{n}.md", head + "---\nbody\n")
    return box


def one_call(tmp_path: Path, me: str, arguments: dict[str, str], *, delivers: str | None = None, lookup: TraceLookup | None = None,
             mail: MailHarness | None = None, binding: MemoryBinding | None = None) -> str | None:
    rec, sinks, scope = recorder(tmp_path, binding, lookup, mail)
    server = FastMCP("t")
    rec.instrument(server, me)

    @server.tool()
    def act(task_id: str = "", reply_to: str = "", revises: str = "") -> str:
        """Doc."""
        if delivers:
            scope.note(delivers)
        return "ok"

    call(server, "act", **arguments)
    trace = events(sinks)[0].trace
    return trace


def test_the_trace_of_the_message_a_call_delivered_comes_first(tmp_path: Path) -> None:
    box = mailbox_with_batch(tmp_path, "B1")
    assert one_call(tmp_path, "ceo", {"task_id": "m1"}, delivers="D", lookup=Traces(), mail=box) == "D"


def test_then_the_trace_of_the_message_a_call_names(tmp_path: Path) -> None:
    box = mailbox_with_batch(tmp_path, "B1")
    for key in ("task_id", "reply_to", "revises"):
        assert one_call(tmp_path, "ceo", {key: "m1"}, lookup=Traces(), mail=box) == "T1"


def test_then_the_one_trace_of_the_callers_batch(tmp_path: Path) -> None:
    assert one_call(tmp_path, "ceo", {}, mail=mailbox_with_batch(tmp_path, "B1", "B1")) == "B1"
    assert one_call(tmp_path, "ceo", {"task_id": "unknown"}, lookup=Traces(), mail=mailbox_with_batch(tmp_path, "B1")) == "B1"


def test_a_batch_of_two_traces_has_none(tmp_path: Path) -> None:
    assert one_call(tmp_path, "ceo", {}, mail=mailbox_with_batch(tmp_path, "B1", "B2")) is None


def test_root_has_no_batch_to_fall_back_on(tmp_path: Path) -> None:
    assert one_call(tmp_path, "root", {}, mail=mailbox_with_batch(tmp_path, "B1")) is None


def test_before_the_organization_exists_the_trace_is_only_what_was_delivered(tmp_path: Path) -> None:
    binding = MemoryBinding(ROOT_DIR)  # no organization yet
    assert one_call(tmp_path, "root", {"task_id": "m1"}, lookup=Traces(), binding=binding) is None
    assert one_call(tmp_path, "root", {"task_id": "m1"}, delivers="D", lookup=Traces(), binding=binding) == "D"


def test_a_lookup_that_fails_leaves_the_event_without_a_trace(tmp_path: Path) -> None:
    class Broken(NoTraces):
        def trace_of(self, addr: str, msg_id: str | None) -> str | None:
            raise RuntimeError("no")

    assert one_call(tmp_path, "ceo", {"task_id": "m1"}, lookup=Broken(), mail=mailbox_with_batch(tmp_path, "B1")) is None


# --------------------------------------------------------------------------------------------- async tools and threads


def test_an_async_tool_is_recorded(tmp_path: Path) -> None:
    rec, sinks, _ = recorder(tmp_path)
    server = FastMCP("t")
    rec.instrument(server, "root")

    @server.tool()
    async def progress(wait_seconds: int = 0) -> str:
        """Doc."""
        return "done"

    assert call(server, "progress", wait_seconds=0) == "done"
    (ev,) = events(sinks)
    assert ev.fields["tool"] == "progress" and ev.fields["ok"] is True and ev.actor == "root"


def test_what_a_worker_thread_delivers_is_not_collected_by_the_call_that_awaits_it(tmp_path: Path) -> None:
    """Risk 12: the collection is per thread (the loop's), the ``progress`` tool works in a worker thread. Kept exactly as it was."""
    from hirearchy.telemetry.testing import thread_local_trace_scope

    sinks, scope = MemoryEventSinks(), thread_local_trace_scope(tmp_path)
    binding = MemoryBinding(ROOT_DIR, exists=True)
    from hirearchy.mcp_server._instructions import InstructionText

    box = memory_mailbox(tmp_path)
    trace = BatchCallTrace(InstructionText(binding), lambda: NoTraces(), lambda: agents_in("ceo"), lambda: box.reader)
    rec = ToolCallRecorder(binding, sinks, scope, json_argument_summarizer(tmp_path), trace)
    server = FastMCP("t")
    rec.instrument(server, "root")

    @server.tool()
    async def in_thread() -> str:
        """Doc."""
        import anyio

        await anyio.to_thread.run_sync(lambda: scope.note("FROM-WORKER"))
        return "ok"

    @server.tool()
    async def in_loop() -> str:
        """Doc."""
        scope.note("FROM-LOOP")
        return "ok"

    asyncio.run(server.call_tool("in_thread", {}))
    asyncio.run(server.call_tool("in_loop", {}))
    worker, loop = sinks.events(ROOT_DIR)
    assert worker.trace is None and loop.trace == "FROM-LOOP"
