"""Organizations whose prompts the snapshots in ``snapshots/prompts/`` record (no test lives here).

The snapshots were recorded from the ``PromptsMixin`` as it was before C-prompts moved it: they pin the pieces of the run prompt that the golden suite
(``tests/golden``) does not reach - the root's whoami, the four ways a result links to the task it serves, a cut body, a redelivered batch, held
non-waking mail, siblings, an empty first run. Ids, instants and the temporary directory are replaced by placeholders (``normalize``)."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from orgmcp.app import Org
from orgmcp.kernel import Message

ROOT = "root"
ENG = "ceo/eng"
CRITERIA = "exactly 33 words; acrostic P-L-A-N-T"
SUB_CRITERIA = "exactly 33 words. First letters of the five lines spell PLANT."
SNAPSHOTS = Path(__file__).resolve().parent / "snapshots" / "prompts"

_ID = re.compile(r"\d{8}T\d{12}-[a-z0-9.-]+-[0-9a-f]{4}\b")
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00")


def normalize(text: str, org: Org) -> str:
    """Ids by order of first appearance (``<ID1>``...), instants as ``<TIME>``, the organization directory as ``<ORG>``."""
    for form in sorted({str(org.root), str(org.root.resolve()), str(org.root.parent), str(org.root.parent.resolve())}, key=len, reverse=True):
        text = text.replace(form, "<ORG>" if form in (str(org.root), str(org.root.resolve())) else "<TMP>")
    seen: dict[str, str] = {}

    def number(match: re.Match[str]) -> str:
        return seen.setdefault(match.group(0), f"<ID{len(seen) + 1}>")

    return _INSTANT.sub("<TIME>", _ID.sub(number, text))


def make(tmp_path: Path) -> Org:
    """root -> ceo (manager, can hire) -> eng, qa (workers)."""
    org = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05})
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=3)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    org.hire("ceo", "qa", "Quality assurance", "Check things.")
    return org


def drain(org: Org, addr: str) -> None:
    org.begin_run(addr)
    org.end_run(addr, ok=True)


def served(org: Org) -> tuple[Message, Message]:
    """root -> ceo task (handled in an earlier run) -> ceo delegated to eng; returns (the ceo's task, the delegation)."""
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write a blurb about plants.", CRITERIA, ["ceo/work/brief.md"], budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", SUB_CRITERIA, budget=4)
    return task, sub


def _answer(org: Org, sub: Message) -> str:
    result = org.report(ENG, sub.id, "done", "35 words, acrostic ok")
    received = org.find_received("ceo", result.id)
    assert received is not None
    return org.run_prompt("ceo", [received])


def root_whoami(org: Org) -> str:
    org.delegate(ROOT, "ceo", "Plan", "Make a plan.", "plan.md exists", budget=6)
    org.delegate(ROOT, "ceo", "Second", "Another.", "done", budget=2)
    return org.whoami(ROOT) + "\n=====\n" + org.state_summary(ROOT)


def empty_first_run(org: Org) -> str:
    return org.run_prompt("ceo/qa", [])


def link_to_the_open_task(org: Org) -> str:
    return _answer(org, served(org)[1])


def link_to_a_blocked_task(org: Org) -> str:
    task, sub = served(org)
    org.report("ceo", task.id, "blocked", "waiting for the draft")
    return _answer(org, sub)


def link_to_a_done_task(org: Org) -> str:
    task, sub = served(org)
    org.report("ceo", task.id, "done", "all good")
    return _answer(org, sub)


def link_to_a_failed_task(org: Org) -> str:
    task, sub = served(org)
    org.report("ceo", task.id, "failed", "gave up")
    return _answer(org, sub)


def no_link_when_ambiguous(org: Org) -> str:
    org.delegate(ROOT, "ceo", "First job", "g", "FIRST-CRITERION", budget=10)
    org.delegate(ROOT, "ceo", "Second job", "g", "SECOND-CRITERION", budget=10)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft", "g", SUB_CRITERIA, budget=1)
    return _answer(org, sub)


def a_blocked_task_shown_in_the_batch(org: Org) -> str:
    task, _ = served(org)
    org.report("ceo", task.id, "blocked", "waiting for the draft")
    return org.state_summary("ceo") + "\n=====\n" + org.state_summary("ceo", {task.id})


def a_long_task_is_cut(org: Org) -> str:
    big = org.delegate(ROOT, "ceo", "Huge", "goal", "HEAD\n" + "filler line\n" * 2500 + "TAIL-MARKER", budget=20)
    first = org.run_prompt("ceo", org.begin_run("ceo"))
    org.end_run("ceo", ok=True)
    return first + "\n=====\n" + org.run_prompt("ceo", []) + f"\n=====\n{big.id}"


def a_redelivered_batch(org: Org) -> str:
    org.delegate(ROOT, "ceo", "Plan", "Make a plan.", "plan.md exists", budget=6)
    batch = org.begin_run("ceo")
    org.report("ceo", batch[0].id, "done", "planned")
    org.end_run("ceo", ok=False)  # the run crashed after the report: the batch comes back
    return org.run_prompt("ceo", org.begin_run("ceo"))


def held_non_waking_mail(org: Org) -> str:
    org.send(ROOT, "ceo", "FYI, no hurry.", title="Held", wake=False)
    org.delegate(ROOT, "ceo", "Plan", "Make a plan.", "plan.md exists", budget=6)
    return org.run_prompt("ceo", org.begin_run("ceo"))


def siblings_and_reports(org: Org) -> str:
    org.delegate(ROOT, "ceo", "Plan", "Make a plan.", "plan.md exists", budget=8)
    org.delegate("ceo", ENG, "Build", "Build it.", "it builds", budget=2)
    return "\n=====\n".join(org.state_summary(a) for a in ("ceo", ENG, "ceo/qa"))


def a_workspace_and_inputs(org: Org) -> str:
    ws, inputs = org.root.parent / "ws", org.root.parent / "in"
    ws.mkdir()
    inputs.mkdir()
    org.hire(ROOT, "dev", "Developer", "Code.", tools=["read", "write"], workspace=str(ws), inputs=[str(inputs)])
    org.hire(ROOT, "ro", "Reader", "Read.", tools=["read"], inputs=[str(inputs)])
    org.hire(ROOT, "sh", "Shell", "Shell.", tools=["shell"], workspace=str(ws))
    return "\n=====\n".join(org.whoami(a) for a in ("dev", "ro", "sh"))


SCENARIOS: dict[str, Callable[[Org], str]] = {
    f.__name__: f for f in (
        root_whoami, empty_first_run, link_to_the_open_task, link_to_a_blocked_task, link_to_a_done_task, link_to_a_failed_task,
        no_link_when_ambiguous, a_blocked_task_shown_in_the_batch, a_long_task_is_cut, a_redelivered_batch, held_non_waking_mail,
        siblings_and_reports, a_workspace_and_inputs,
    )
}


def render(name: str, tmp_path: Path) -> str:
    org = make(tmp_path)
    return normalize(SCENARIOS[name](org), org)
