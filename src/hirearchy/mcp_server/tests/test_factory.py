"""``GroupedServerFactory``: the identity is checked, the instructions and the recorder come first, the groups are registered in order, and the groups of the human's seat
only for root."""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from hirearchy.kernel import ROOT, OrgError
from hirearchy.mail.testing import memory_mailbox
from hirearchy.mcp_server._factory import GroupedServerFactory
from hirearchy.mcp_server._instructions import INSTRUCTIONS, InstructionText
from hirearchy.mcp_server._recorder import BatchCallTrace, ToolCallRecorder
from hirearchy.mcp_server.testing import MemoryBinding, NoTraces, RecordingGroup, agents_in
from hirearchy.telemetry.testing import MemoryEventSinks, StackTraceScope, json_argument_summarizer

from ._support import call, names

HERE = Path("/memory/org")


def make(tmp_path: Path, binding: MemoryBinding, registered: list[tuple[str, str]]) -> tuple[GroupedServerFactory, MemoryEventSinks]:
    sinks, agents, text, mail = MemoryEventSinks(), agents_in("ceo", "ceo/eng"), InstructionText(binding), memory_mailbox(tmp_path)
    trace = BatchCallTrace(text, lambda: NoTraces(), lambda: agents, lambda: mail.reader)
    recorder = ToolCallRecorder(binding, sinks, StackTraceScope(), json_argument_summarizer(tmp_path), trace)
    groups = [RecordingGroup("a", registered), RecordingGroup("b", registered)]
    return GroupedServerFactory(binding, lambda: agents, text, recorder, groups, [RecordingGroup("root", registered)]), sinks


def test_an_agent_gets_the_common_groups_in_order_and_the_short_instructions(tmp_path: Path) -> None:
    registered: list[tuple[str, str]] = []
    server = make(tmp_path, MemoryBinding(HERE, exists=True), registered)[0].build("ceo/eng")
    assert isinstance(server, FastMCP) and server.name == "hirearchy" and server.instructions == INSTRUCTIONS
    assert registered == [("a", "ceo/eng"), ("b", "ceo/eng")] and names(server) == ["ping_a", "ping_b"]


def test_root_also_gets_the_groups_of_the_humans_seat_after_the_common_ones(tmp_path: Path) -> None:
    registered: list[tuple[str, str]] = []
    server = make(tmp_path, MemoryBinding(HERE, exists=True), registered)[0].build(ROOT)
    assert isinstance(server, FastMCP) and "The organization is at /memory/org." in (server.instructions or "")
    assert names(server) == ["ping_a", "ping_b", "ping_root"]


def test_the_identity_is_the_one_the_directory_knows(tmp_path: Path) -> None:
    registered: list[tuple[str, str]] = []
    make(tmp_path, MemoryBinding(HERE, exists=True), registered)[0].build("/ceo/")
    assert registered[0] == ("a", "ceo")
    with pytest.raises(OrgError, match="no such agent: nobody"):
        make(tmp_path, MemoryBinding(HERE, exists=True), registered)[0].build("nobody")


def test_root_may_start_before_the_organization_exists(tmp_path: Path) -> None:
    registered: list[tuple[str, str]] = []
    server = make(tmp_path, MemoryBinding(HERE), registered)[0].build(" root ")
    assert registered[0] == ("a", ROOT) and "No organization exists at /memory/org yet" in (server.instructions or "")


def test_an_agent_never_starts_without_its_organization(tmp_path: Path) -> None:
    binding = MemoryBinding(HERE)
    with pytest.raises(OrgError) as info:
        make(tmp_path, binding, [])[0].build("ceo")
    assert str(info.value) == binding.missing_message()


def test_the_tools_of_every_group_are_recorded_because_the_recorder_comes_before_them(tmp_path: Path) -> None:
    factory, sinks = make(tmp_path, MemoryBinding(HERE, exists=True), [])
    server = factory.build("ceo")
    assert isinstance(server, FastMCP)
    assert call(server, "ping_a") == "a"
    (ev,) = sinks.events(HERE)
    assert ev.fields["tool"] == "ping_a" and ev.actor == "ceo"
