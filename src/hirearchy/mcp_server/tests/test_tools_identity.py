"""``IdentityTools``: whoami (with the scheduler line for root, the setup state before an organization exists) and inbox (root consumes its mail, an agent reads its batch)."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

from hirearchy.access.testing import FixedModelFloorAudit
from hirearchy.daemon import SchedulerState
from hirearchy.daemon.testing import FakeSchedulerStatus
from hirearchy.kernel import ROOT, OrgError
from hirearchy.mail.testing import MailHarness, memory_mailbox
from hirearchy.mcp_server._instructions import InstructionText
from hirearchy.mcp_server._tools_identity import STALE_SKILL, IdentityTools
from hirearchy.mcp_server.testing import FixedInstalledSkill, MemoryBinding
from hirearchy.prompts.testing import FixedWhoami
from hirearchy.reflection import DeliverableChecks, DeliverableFinding, deliverables_note
from hirearchy.reflection.testing import FixedDeliverableChecks

from ._support import call, fails, names, serve


STALE = Path("/h/.kiro/skills/hirearchy/SKILL.md")
FINDING = DeliverableFinding(folder="/tmp/deliverables", services=("weekly-memo",), name="memo.md", kind="unknown")
DELIVERABLES = deliverables_note([FINDING])
NOTE = "Model floor: below the allowed models (claude-sonnet-5.5, claude-opus-5.5): ceo/eng on claude-haiku-4.5. Fix: set model: claude-sonnet-5.5 in each one's AGENT.md."


def tools(
    tmp_path: Path, exists: bool = True, state: SchedulerState = SchedulerState("stopped"), stale: Path | None = None, floor: str = "",
    findings: tuple[DeliverableFinding, ...] = (),
) -> tuple[IdentityTools, FixedWhoami, MailHarness]:
    who, box = FixedWhoami("WHO"), memory_mailbox(tmp_path)

    def gone() -> NoReturn:
        raise OrgError("no organization at /o yet: call create_org(mission=...) first")

    if not exists:
        return IdentityTools(InstructionText(MemoryBinding(Path("/o"))), gone, gone, gone, gone, FixedInstalledSkill(stale), gone, gone), who, box
    return IdentityTools(InstructionText(MemoryBinding(Path("/o"), exists=True)), lambda: who, lambda: FakeSchedulerStatus(state),
                         lambda: box.batches, lambda: box.reader, FixedInstalledSkill(stale), lambda: FixedDeliverableChecks({ROOT: findings}),
                         lambda: FixedModelFloorAudit(note=floor)), who, box


class FailingChecks(DeliverableChecks):
    def __init__(self, error: Exception) -> None:
        self._error = error

    def findings(self, actor: str, service: str | None = None, *, settled: bool = False) -> list[DeliverableFinding]:
        raise self._error


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


def test_root_is_told_when_the_installed_skill_is_out_of_date(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, state=SchedulerState("running", 77, "2026-01-01 00:00:00Z"), stale=STALE)
    out = call(serve(group, ROOT), "whoami")
    assert out == "WHO\n\nscheduler: running (pid 77, since 2026-01-01 00:00:00Z)\n\n" + STALE_SKILL.format(path=STALE)
    assert out.endswith(f"Note: the installed skill at {STALE} is out of date: run `hirearchy install-skill --force` "
                        "(tell the user; this session may follow the old text until it is restarted).")


def test_root_is_told_which_agents_run_below_the_model_floor(tmp_path: Path) -> None:
    running = SchedulerState("running", 77, "2026-01-01 00:00:00Z")
    group, _, _ = tools(tmp_path, state=running, floor=NOTE)
    assert call(serve(group, ROOT), "whoami") == "WHO\n\nscheduler: running (pid 77, since 2026-01-01 00:00:00Z)\n\n" + NOTE
    group, _, _ = tools(tmp_path, state=running, stale=STALE, floor=NOTE)
    out = call(serve(group, ROOT), "whoami")
    assert out.endswith("\n\n" + NOTE + "\n\n" + STALE_SKILL.format(path=STALE))  # the floor before the skill
    assert "Model floor" not in call(serve(tools(tmp_path)[0], ROOT), "whoami")


def test_root_whoami_appends_the_note_before_the_stale_skill_note(tmp_path: Path) -> None:
    running = SchedulerState("running", 77, "2026-01-01 00:00:00Z")
    scheduler = "scheduler: running (pid 77, since 2026-01-01 00:00:00Z)"
    group, _, _ = tools(tmp_path, state=running, findings=(FINDING,))
    assert call(serve(group, ROOT), "whoami") == f"WHO\n\n{scheduler}\n\n{DELIVERABLES}"
    group, _, _ = tools(tmp_path, state=running, stale=STALE, floor=NOTE, findings=(FINDING,))
    out = call(serve(group, ROOT), "whoami")  # the order of root's text: who, the scheduler, the deliverables, the floor, the stale skill
    assert out == f"WHO\n\n{scheduler}\n\n{DELIVERABLES}\n\n{NOTE}\n\n" + STALE_SKILL.format(path=STALE)
    assert "Deliverable" not in call(serve(tools(tmp_path)[0], ROOT), "whoami")  # no finding, no note


def test_a_failing_findings_read_drops_the_note_from_whoami(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, state=SchedulerState("stopped"), stale=STALE)
    group._deliverables = lambda: FailingChecks(OrgError("a contract cannot be read"))
    assert call(serve(group, ROOT), "whoami") == "WHO\n\nscheduler: stopped\n\n" + STALE_SKILL.format(path=STALE)
    group._deliverables = lambda: FailingChecks(OSError(5, "I/O error"))
    assert "Deliverable" not in call(serve(group, ROOT), "whoami")


def test_an_agent_is_never_shown_the_deliverable_note(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, findings=(FINDING,))
    assert call(serve(group, "ceo"), "whoami") == "WHO"


def test_setup_mode_shows_no_deliverable_note(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, exists=False)  # the provider would raise: it is not asked
    assert "Deliverable" not in call(serve(group, ROOT), "whoami")


def test_an_agent_is_never_shown_the_floor_note(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, floor=NOTE)
    assert call(serve(group, "ceo"), "whoami") == "WHO"


def test_setup_mode_shows_no_floor_note(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, exists=False)  # the floor provider would raise: it is not asked
    assert "Model floor" not in call(serve(group, ROOT), "whoami")


def test_root_is_told_nothing_when_no_skill_is_out_of_date(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path)
    assert "installed skill" not in call(serve(group, ROOT), "whoami")


def test_an_agent_never_sees_the_stale_skill_note(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, stale=STALE)
    assert call(serve(group, "ceo"), "whoami") == "WHO"


def test_the_setup_state_also_carries_the_stale_skill_note(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, exists=False, stale=STALE)
    out = call(serve(group, ROOT), "whoami")
    assert out.startswith("Setup: no organization exists at /o yet.") and out.endswith("\n\n" + STALE_SKILL.format(path=STALE))
    assert "installed skill" not in call(serve(tools(tmp_path, exists=False)[0], ROOT), "whoami")


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
