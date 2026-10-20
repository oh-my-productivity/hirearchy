"""Final word on a task: `blocked` can be re-reported (superseded), `done`/`failed` are final (D1), and
runtime-only/failed runs do not make an agent `expensive` (D3)."""

import asyncio

import pytest

from orgmcp.core import ROOT
from orgmcp.server import build_server

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
