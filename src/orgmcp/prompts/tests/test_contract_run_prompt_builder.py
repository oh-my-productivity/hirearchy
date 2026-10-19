"""Contract of ``RunPromptBuilder``: the whole prompt of a run, over agents, mailboxes and settings on disk and in memory.

The prompt is the contract (the golden suite pins its bytes for whole organizations): here the order of its parts and what each part is made of."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.prompts import RunPromptBuilder
from orgmcp.prompts.testing import IMPLEMENTATIONS, PromptsWorld

from ._support import implementations

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")

ORG_MD = "---\nmemory_max_words: 12\n---\nThe rules of this organization.\n"
HEADINGS = ["# orgmcp run: you are", "# Your charter (", "# Your memory (", "# Your state", "# New messages for this run", "---\nHandle every new message"]


@pytest.fixture(params=implementations(IMPLEMENTATIONS[RunPromptBuilder]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> PromptsWorld:
    made = cast(Callable[[Path], PromptsWorld], request.param)(tmp_path)
    assert isinstance(made.prompt, RunPromptBuilder)
    made.config(ORG_MD)
    made.agent("ceo", {"role": "Chief", "can_hire": True}, "# Role: Chief\n\nRun the company.")
    made.budget("ceo", 5)
    return made


def prompt(w: PromptsWorld, addr: str = "ceo") -> str:
    return w.prompt.run_prompt(addr, w.mail.messages(addr, "inbox"))


def test_an_agent_that_does_not_exist_is_refused(w: PromptsWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: nobody"):
        w.prompt.run_prompt("nobody", [])


def test_the_parts_come_in_order(w: PromptsWorld) -> None:
    text = prompt(w)
    positions = [text.index(h) for h in HEADINGS]
    assert positions == sorted(positions) and positions[0] == 0


def test_a_first_run_with_no_mail(w: PromptsWorld) -> None:
    text = w.prompt.run_prompt("ceo", [])
    assert text.startswith("# orgmcp run: you are `ceo`\n\nThe rules of this organization.\n\n# Your charter (ceo/AGENT.md, owned by your parent)\n")
    assert "# Your charter (ceo/AGENT.md, owned by your parent)\n# Role: Chief\n\nRun the company.\n\n# Your memory (ceo/MEMORY.md)\n(empty: this may be your first run)\n\n# Your state\n" in text
    assert "\n# New messages for this run (0)\n(none)\n---\nHandle every new message above with the orgmcp tools, following the protocol.\n" in text


def test_the_state_is_the_summary_of_the_agent_followed_by_the_paths_line(w: PromptsWorld) -> None:
    text = w.prompt.run_prompt("ceo", [])
    state = w.summary.state_summary("ceo")
    assert f"\n# Your state\n{state}\n- Paths: every path (read, write, artifacts) is relative to the org root. Yours start with `ceo/`.\n" in text


def test_a_task_of_the_batch_is_shown_once_in_full_and_the_state_points_at_it(w: PromptsWorld) -> None:
    task = w.send("root", "ceo", "task", "Plan", "## Goal\nWrite the plan.\n\n## Acceptance criteria\nplan.md exists")
    text = prompt(w)
    assert text.count("plan.md exists") == 1
    assert f'  - {task.id} "Plan" from root\n    (full text: see the new messages below)\n' in text
    assert f"# New messages for this run (1)\n### task {task.id}\n" in text


def test_the_memory_is_shown_trimmed(w: PromptsWorld) -> None:
    w.memory("ceo", "\n\nLast run: read the repo.\n\n")
    assert "# Your memory (ceo/MEMORY.md)\nLast run: read the repo.\n\n# Your state\n" in w.prompt.run_prompt("ceo", [])


def test_a_memory_over_the_cap_asks_to_be_condensed(w: PromptsWorld) -> None:
    w.memory("ceo", " ".join(f"w{i}" for i in range(13)))
    text = w.prompt.run_prompt("ceo", [])
    assert ("\n\n**Your memory is 13 words, over the 12-word limit, and writes that keep it over the limit are refused. This run, condense it: "
            "rewrite ceo/MEMORY.md (not append) with only what your next run needs; move detail into files under your work/ directory.**\n\n# Your state") in text


def test_a_memory_at_the_cap_is_left_alone(w: PromptsWorld) -> None:
    w.memory("ceo", " ".join(f"w{i}" for i in range(12)))
    assert "condense" not in w.prompt.run_prompt("ceo", [])


def test_a_result_is_followed_by_the_task_it_answers(w: PromptsWorld) -> None:
    w.agent("ceo/eng", {"role": "Engineer"}, "Build.")
    sub = w.send("ceo", "ceo/eng", "task", "Draft", "## Goal\nDraft it.\n\n## Acceptance criteria\n33 words")
    result = w.send("ceo/eng", "ceo", "result", "Draft", "## Summary\nDone.", reply_to=sub.id, status="done")
    text = w.prompt.run_prompt("ceo", [result])
    assert f"[The task you delegated to ceo/eng that this result answers ({sub.id}). Judge the result against these criteria, verbatim:]\n> ## Goal\n" in text
    assert text.index("status: done") < text.index("> 33 words")


def test_the_stray_notice_is_told_once_between_the_state_and_the_messages(w: PromptsWorld) -> None:
    w.strays.notices["ceo"] = "# Notice from the runtime\nYou wrote files in the workspace."
    first = w.prompt.run_prompt("ceo", [])
    assert "- Paths: every path (read, write, artifacts) is relative to the org root. Yours start with `ceo/`.\n\n# Notice from the runtime\nYou wrote files in the workspace.\n\n# New messages" in first
    assert "Notice from the runtime" not in w.prompt.run_prompt("ceo", [])


def test_an_agent_without_services_is_not_asked_for_the_sections(w: PromptsWorld) -> None:
    w.sections.text["ceo"] = "\n# Playbook\nnever shown\n"
    w.prompt.run_prompt("ceo", [])
    assert w.sections.asked == [] and w.services.asked == ["ceo"]


def test_a_service_owner_gets_the_sections_after_the_notice(w: PromptsWorld) -> None:
    w.services.offered["ceo"] = ["weekly-brief"]
    w.sections.text["ceo"] = "\n# Playbook for weekly-brief\nDo it.\n"
    w.strays.notices["ceo"] = "NOTICE"
    batch = w.mail.messages("ceo", "inbox")
    text = w.prompt.run_prompt("ceo", batch)
    assert "\nNOTICE\n\n# Playbook for weekly-brief\nDo it.\n\n# New messages for this run (0)" in text
    assert w.sections.asked == [("ceo", batch)]


def test_the_closing_lines_name_the_write_tool_the_agent_has(w: PromptsWorld) -> None:
    assert w.prompt.run_prompt("ceo", []).endswith(
        'Before you stop, update your memory with `@orgmcp/write`(path="ceo/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`). '
        "Do not wait for replies; end the run when done.\n"
    )


def test_an_agent_with_the_built_in_write_calls_the_orgmcp_tool_org_write(w: PromptsWorld) -> None:
    w.agent("dev", {"role": "Dev", "tools": ["write"], "workspace": str(w.root / "ws")}, "Code.")
    text = w.prompt.run_prompt("dev", [])
    assert 'update your memory with `@orgmcp/org_write`(path="dev/MEMORY.md", ...)' in text
