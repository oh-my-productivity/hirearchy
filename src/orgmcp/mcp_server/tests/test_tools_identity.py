"""``IdentityTools``: whoami (with the scheduler line for root, the setup state before an organization exists) and inbox (root consumes its mail, an agent reads its batch)."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.kernel import ROOT, OrgError
from orgmcp.mail.testing import MailHarness, memory_mailbox
from orgmcp.mcp_server._instructions import InstructionText
from orgmcp.mcp_server._tools_identity import IdentityTools
from orgmcp.mcp_server.testing import MemoryBinding
from orgmcp.prompts.testing import FixedWhoami

from ._support import call, fails, names, serve


def tools(tmp_path: Path, exists: bool = True, state: SchedulerState = SchedulerState("stopped")) -> tuple[IdentityTools, FixedWhoami, MailHarness]:
    who, box = FixedWhoami("WHO"), memory_mailbox(tmp_path)

    def gone() -> NoReturn:
        raise OrgError("no organization at /o yet: call create_org(mission=...) first")

    if not exists:
        return IdentityTools(InstructionText(MemoryBinding(Path("/o"))), gone, gone, gone, gone), who, box
    return IdentityTools(InstructionText(MemoryBinding(Path("/o"), exists=True)), lambda: who, lambda: FakeSchedulerStatus(state),
                         lambda: box.batches, lambda: box.reader), who, box


def message(n: int, to: str, sender: str = "root", folder: str = "inbox") -> tuple[str, str]:
    return (f"{to}/{folder}/m{n}.md",
            f"---\nsender: {sender}\nto: {to}\ntype: note\nid: m{n}\ncreated: 2026-01-01T00:00:00+00:00\n---\nbody {n}\n")


def test_the_tools_and_their_order(tmp_path: Path) -> None:
    assert names(serve(tools(tmp_path)[0], "ceo")) == ["whoami", "inbox"]


def test_an_agent_is_told_who_it_is_without_the_scheduler(tmp_path: Path) -> None:
    group, who, _ = tools(tmp_path)
    assert call(serve(group, "ceo"), "whoami") == "WHO" and who.asked == ["ceo"]


def test_root_is_also_told_whether_the_scheduler_runs(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, state=SchedulerState("running", 77, "2026-01-01 00:00:00Z"))
    assert call(serve(group, ROOT), "whoami") == "WHO\n\nscheduler: running (pid 77, since 2026-01-01 00:00:00Z)"


def test_before_the_organization_exists_root_gets_the_setup_state_and_an_agent_the_refusal(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, exists=False)
    assert call(serve(group, ROOT), "whoami").startswith("Setup: no organization exists at /o yet.")
    assert "call create_org" in fails(serve(group, "ceo"), "whoami")
    assert "call create_org" in fails(serve(group, ROOT), "inbox")


def test_an_agent_reads_its_batch_or_else_its_inbox(tmp_path: Path) -> None:
    group, _, box = tools(tmp_path)
    box.agent("ceo")
    assert call(serve(group, "ceo"), "inbox") == "(no new messages)"
    box.put(*message(1, "ceo"))
    assert "body 1" in call(serve(group, "ceo"), "inbox")
    box.put(*message(2, "ceo", folder="inflight"))
    out = call(serve(group, "ceo"), "inbox")
    assert "body 2" in out and "body 1" not in out  # the batch in flight wins
    assert box.listing("ceo/inbox") == ["m1.md"]  # reading does not consume an agent's mail


def test_root_reading_its_inbox_consumes_it(tmp_path: Path) -> None:
    group, _, box = tools(tmp_path)
    box.put("inbox/m1.md", message(1, "root", sender="ceo")[1])
    assert "body 1" in call(serve(group, ROOT), "inbox")
    assert call(serve(group, ROOT), "inbox") == "(no new messages)"
    assert not box.listing("inbox")
