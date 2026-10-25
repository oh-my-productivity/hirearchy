"""``quality``: root's tool for how the work went (0b 9.1): root only, after ``progress``, read in a worker thread, the service stripped."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from hirearchy.kernel import ROOT, JsonObject
from hirearchy.mcp_server._instructions import InstructionText
from hirearchy.mcp_server._tools_quality import QualityTools
from hirearchy.mcp_server.testing import MemoryBinding
from hirearchy.progress import QualityReport
from hirearchy.progress.testing import FixedQualityReport
from hirearchy.reflection import ServiceRecord

from ._support import call, described, fails, serve

HERE = Path("/memory/org")


def tools(report: QualityReport, *, exists: bool = True) -> QualityTools:
    return QualityTools(InstructionText(MemoryBinding(HERE, exists=exists)), lambda: report)


def test_quality_prints_the_text_of_the_report() -> None:
    report = FixedQualityReport()
    assert call(serve(tools(report), ROOT), "quality").startswith("Quality of the work you asked for (")
    assert report.calls == [("quality_text", None)]


def test_root_gets_quality_after_progress(org) -> None:  # type: ignore[no-untyped-def]
    from testkit.mcp_server_world import build_server

    names = [t.name for t in asyncio.run(build_server(org, ROOT).list_tools())]
    assert "quality" in names and names.index("quality") == names.index("progress") + 1


def test_agents_never_get_the_quality_tool(org) -> None:  # type: ignore[no-untyped-def]
    from testkit.mcp_server_world import build_server

    for who in ("ceo", "ceo/eng"):
        assert "quality" not in [t.name for t in asyncio.run(build_server(org, who).list_tools())]


class ThreadReport(QualityReport):
    """A report that remembers which thread it was read in."""

    def __init__(self) -> None:
        self.threads: list[threading.Thread] = []

    def quality_text(self, service: str | None = None) -> str:
        self.threads.append(threading.current_thread())
        return "THE VIEW"

    def quality_data(self, service: str | None = None) -> JsonObject:
        return {}


def test_quality_runs_in_a_worker_thread() -> None:
    report = ThreadReport()
    server = serve(tools(report), ROOT)
    tool = server._tool_manager.list_tools()[0]
    assert asyncio.iscoroutinefunction(tool.fn)
    assert call(server, "quality") == "THE VIEW"
    assert report.threads and report.threads[0] is not threading.main_thread()


def test_setup_mode_returns_the_setup_state() -> None:
    report = FixedQualityReport()
    out = call(serve(tools(report, exists=False), ROOT), "quality")
    assert out.startswith("Setup: no organization exists at /memory/org yet.") and report.calls == []


def test_service_is_stripped_and_empty_means_everything() -> None:
    report = FixedQualityReport([ServiceRecord("lead", "weekly-brief", ROOT, "human")])
    server = serve(tools(report), ROOT)
    call(server, "quality", service="  weekly-brief ")
    call(server, "quality", service="")
    call(server, "quality", service="   ")
    call(server, "quality", service=None)
    assert [c[1] for c in report.calls] == ["weekly-brief", None, None, None]


def test_an_unknown_service_is_the_refusal_of_the_tool() -> None:
    server = serve(tools(FixedQualityReport()), ROOT)
    assert "no service named `nope`" in fails(server, "quality", service="nope")


def test_the_docstring_is_9_1s() -> None:
    text = " ".join(described(serve(tools(FixedQualityReport()), ROOT))["quality"].split())  # the description keeps the docstring's line breaks and indentation
    assert text.startswith("How the work you asked for has gone, from the files: per service, and for your one-off tasks, the cases;")
    for needle in (
        "escapes (the team reported done, then the user rejected it) with the verifier that signed them off and the cause a rule typed;", "deliveries without a verdict (never counted as accepts)",
        "the user's against the runs you approved, with top-ups, your own relayed reworks (your own spend) and runs not charged shown apart",
        "blocked tasks moved past without a verdict and the runs held behind them; two alarms (repeat, cost; tunable defaults) and the timeline of bar changes. "
        "Read-only, root only: agents never see it, and you never pass these counts to an agent. service: one service's block (default: everything). "
        "Use it when the user asks how a service or the org is doing, and say what it shows in plain words.",
    ):
        assert needle in text, needle
