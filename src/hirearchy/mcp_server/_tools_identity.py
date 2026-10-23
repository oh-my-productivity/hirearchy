"""Who you are and what is waiting for you: ``whoami`` and ``inbox``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..access import ModelFloorAudit
from ..daemon import SchedulerStatus
from ..kernel import ROOT, OrgError, Provider
from ..mail import BatchStore, MailboxReader
from ..prompts import Whoami
from ..reflection import DeliverableChecks, deliverables_note
from ._ports import InstalledSkill, SetupMode, ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


STALE_SKILL = ("Note: the installed skill at {path} is out of date: run `hirearchy install-skill --force` "
               "(tell the user; this session may follow the old text until it is restarted).")


def with_stale_skill_note(text: str, skill: InstalledSkill) -> str:
    """``text``, and when the installed assistant skill is out of date a closing note naming it (only root is shown this)."""
    path = skill.stale()
    return text if path is None else f"{text}\n\n{STALE_SKILL.format(path=path)}"


def with_deliverables_note(text: str, checks: DeliverableChecks) -> str:
    """``text``, and when files of a deliverable folder are not what the team delivered as checked a closing note naming them (only root is shown
    this). A folder, a catalog or a mailbox that cannot be read leaves the note out: it is advice, never a reason for the call to fail."""
    try:
        note = deliverables_note(checks.findings(ROOT))
    except (OrgError, OSError):
        return text
    return f"{text}\n\n{note}" if note else text


def with_floor_note(text: str, floor: ModelFloorAudit) -> str:
    """``text``, and when some agent runs on a model outside the allowed set a closing line naming each one and the fix (only root is shown this)."""
    note = floor.note()
    return f"{text}\n\n{note}" if note else text


class IdentityTools(ToolGroup):
    def __init__(
        self, setup: SetupMode, whoami: Provider[Whoami], scheduler: Provider[SchedulerStatus], batches: Provider[BatchStore],
        mail: Provider[MailboxReader], skill: InstalledSkill, deliverables: Provider[DeliverableChecks], floor: Provider[ModelFloorAudit],
    ) -> None:
        self._setup = setup
        self._whoami = whoami
        self._scheduler = scheduler
        self._batches = batches
        self._mail = mail
        self._skill = skill
        self._deliverables = deliverables
        self._floor = floor

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def whoami() -> str:
            """Your address, role, budget, direct reports, open tasks, outstanding delegations and charter."""
            if me == ROOT and self._setup.active():
                return with_stale_skill_note(self._setup.state(), self._skill)
            text = self._whoami().whoami(me)
            if me != ROOT:
                return text
            shown = with_deliverables_note(f"{text}\n\n{self._scheduler().describe()}", self._deliverables())
            return with_stale_skill_note(with_floor_note(shown, self._floor()), self._skill)

        @mcp.tool()
        def inbox() -> str:
            """The messages for this run. For root (the human) this lists unread messages and marks them read."""
            if me == ROOT:
                batches = self._batches()
                batch = batches.begin(ROOT)
                batches.end(ROOT, ok=True)
            else:
                mail = self._mail()
                batch = mail.messages(me, "inflight") or mail.messages(me, "inbox")
            return "\n".join(m.render() for m in batch) or "(no new messages)"
