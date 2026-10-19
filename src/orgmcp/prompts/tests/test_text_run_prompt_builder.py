"""``TextRunPromptBuilder``: the template of the run prompt and the order in which its parts are made (the roles are fakes here)."""

from __future__ import annotations

import pytest

from orgmcp.access.testing import StaticAccess
from orgmcp.kernel import Message, OrgError
from orgmcp.prompts._run import TextRunPromptBuilder
from orgmcp.prompts.testing import FixedBriefing, FixedNotices, FixedRenderer, FixedStateSummary

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")


def message(n: int) -> Message:
    return Message(sender="root", to="ceo", type="note", title="t", body="b", id=f"20260101T0000000000{n:02d}-root-aaaa")


class Parts:
    def __init__(self, notices: str = "") -> None:
        self.access = StaticAccess()
        self.access.put_agent("ceo", {"role": "Chief"})
        self.access.put_agent("dev", {"role": "Dev", "tools": ["write"], "workspace": "/ws"})
        self.briefing, self.summary = FixedBriefing("BRIEFING"), FixedStateSummary("STATE")
        self.renderer, self.notices = FixedRenderer(), FixedNotices(notices)
        self.builder = TextRunPromptBuilder(self.access.agents, self.briefing, self.summary, self.renderer, self.access, self.notices)


def test_the_template() -> None:
    p = Parts()
    batch = [message(1), message(2)]
    assert p.builder.run_prompt("ceo", batch) == f"""# orgmcp run: you are `ceo`

BRIEFING

# Your state
STATE
- Paths: every path (read, write, artifacts) is relative to the org root. Yours start with `ceo/`.

# New messages for this run (2)
RENDERED {batch[0].id}
RENDERED {batch[1].id}
---
Handle every new message above with the orgmcp tools, following the protocol.
Messages may be redelivered after a crash: if your state shows one was already handled, skip it.
Before you stop, update your memory with `@orgmcp/write`(path="ceo/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`). Do not wait for replies; end the run when done.
"""


def test_an_empty_batch_says_none() -> None:
    assert "# New messages for this run (0)\n(none)\n---\n" in Parts().builder.run_prompt("ceo", [])


def test_the_notices_sit_between_the_paths_line_and_the_new_messages() -> None:
    text = Parts("\nNOTICE\n").builder.run_prompt("ceo", [])
    assert "Yours start with `ceo/`.\n\nNOTICE\n\n# New messages" in text


def test_the_state_is_asked_with_the_ids_of_the_tasks_of_the_batch_only() -> None:
    p = Parts()
    task = Message(sender="root", to="ceo", type="task", title="t", body="b", id="20260101T000000000003-root-aaaa")
    p.builder.run_prompt("ceo", [message(1), task])
    assert p.summary.asked == [("ceo", {task.id})]


def test_every_part_is_asked_about_the_agent_and_the_messages_are_rendered_in_its_context() -> None:
    p = Parts()
    batch = [message(1)]
    p.builder.run_prompt("ceo", batch)
    assert p.briefing.asked == ["ceo"] and p.notices.asked == [("ceo", batch)] and p.renderer.asked == [("ceo", batch[0])]


def test_the_orgmcp_write_tool_has_the_name_the_agent_has() -> None:
    assert "update your memory with `@orgmcp/org_write`(path=\"dev/MEMORY.md\", ...)" in Parts().builder.run_prompt("dev", [])


def test_an_unknown_agent_is_refused_before_any_part_is_made() -> None:
    p = Parts()
    with pytest.raises(OrgError, match="no such agent: nobody"):
        p.builder.run_prompt("nobody", [])
    assert p.briefing.asked == [] and p.summary.asked == [] and p.notices.asked == []


def test_the_stray_notice_is_taken_after_the_messages_are_rendered_and_before_the_state_is_made() -> None:
    """The notice is told once: a message that cannot be rendered does not use it up, and a state that cannot be made comes after it (as it always did)."""
    p = Parts()
    order: list[str] = []
    p.renderer.on_ask = lambda: order.append("render")
    p.notices.on_ask = lambda: order.append("notices")
    p.summary.on_ask = lambda: order.append("state")
    p.builder.run_prompt("ceo", [message(1)])
    assert order == ["render", "notices", "state"]
