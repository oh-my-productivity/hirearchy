# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

import pytest
from testkit.reach.hirearchy.core import ROOT
from testkit.mcp_server_world import build_server

ENG = "ceo/eng"
CRITERIA = "exactly 33 words; a non-author reviews the final text"


def drain(org, addr):
    org.begin_run(addr)
    org.end_run(addr, ok=True)


@pytest.fixture
def blocked(org):
    """root -> ceo task; ceo delegated to eng (serving it); eng reported done; ceo reported the root task blocked."""
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write it.", CRITERIA, budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", "exactly 33 words", budget=4)
    first = org.report("ceo", task.id, "blocked", "review judged a stale draft; no budget to rework")
    result = org.report(ENG, sub.id, "done", "33 words")
    return task, sub, first, result


def test_report_docstring_and_rules_state_the_new_rule(org):
    tools = asyncio.run(build_server(org, "ceo").list_tools())
    doc = next(t for t in tools if t.name == "report").description
    assert "final" in doc and "blocked" in doc and "supersedes" in doc and "once per blocked" in doc
    rules = org.rules()
    assert "`done` and `failed` are final" in rules and "`blocked` is not final" in rules
    assert "never changes a task's outcome" in rules and "unless you verified them" in rules


# ------------------------------------------------------------------------------------------ 3. feedback
SERVICE = dict(
    description="A brief.", acceptance=["At most 600 words"], budget=10,
    deliverable={"description": "one markdown file", "format": "markdown", "max_words": 600},
    inputs=[{"name": "topic", "description": "subject", "required": True}],
)


@pytest.fixture
def svc(org):
    org.define_service(ROOT, "ceo", "brief", **SERVICE)
    return org


def test_the_report_tool_docstring_says_lessons_are_required_for_blocked(svc):
    tools = {t.name: t for t in asyncio.run(build_server(svc, "ceo").list_tools())}
    assert "whatever the status - done, failed or blocked" in tools["report"].description


def test_lessons_asks_for_the_five_parts(org):
    doc = " ".join(next(t for t in asyncio.run(build_server(org, "ceo").list_tools()) if t.name == "report").description.split())
    for label in ("Expected:", "Happened:", "Caught at:", "Cause:", "Prevent:", "Near miss:"):
        assert label in doc
    assert "not a person" in doc and "1-3 lines" not in doc and "whatever the status - done, failed or blocked" in doc
