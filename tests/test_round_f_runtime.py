"""Round F (runtime): charter rewrites keep the frontmatter, feedback is not a waiver, lessons on blocked reports,
the digest shows the latest lessons first, and a budget grant says what the recipient can do with it."""

import asyncio

import pytest

from orgmcp import templates
from orgmcp.core import ROOT
from orgmcp.server import build_server

ENG = "ceo/eng"


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


# ------------------------------------------------------------------------------------------ 2. review advice
def test_low_quality_advice_points_at_the_body_not_the_whole_charter():
    text = templates.REVIEW_ACTIONS["low_quality"].format(a=ENG)
    assert "BODY of `ceo/eng`'s charter" in text and "kept automatically" in text
    assert "revises=<task id>" in text and "`revise_playbook`" in text and "tighten" not in text
    assert "frontmatter" in templates.REVIEW_ACTIONS["expensive"]


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


def test_the_send_reply_carries_the_grant_hint(org):
    root = build_server(org, ROOT)
    out = call(root, "send", to="ceo", body="runs for you", budget=1)
    assert "with 1 run(s) of budget" in out
    assert "`ceo` now has 1 run(s) and 0 outstanding delegation(s): with 1 run(s) and 0 outstanding delegation(s) it cannot delegate anything" in out
    assert "grant at least 1 more (a budget of 2)" in out
    out = call(root, "send", to="ceo", body="runs for you", budget=4)
    assert "now has 5 run(s)" in out and "hand down at most 4 run(s)" in out
    assert "now has" not in call(root, "send", to="ceo", body="just a note")


def test_a_manager_granting_to_its_report_also_gets_the_hint(org):
    org.hire("ceo", "lead2", "Lead", "x", can_hire=True)
    org.send(ROOT, "ceo", "runs", budget=6)
    out = call(build_server(org, "ceo"), "send", to="ceo/lead2", body="go", budget=2)
    assert "`ceo/lead2` now has 2 run(s) and 0 outstanding delegation(s); with one more delegation it can hand down at most 1 run(s)." in out
    assert "now has" not in call(build_server(org, "ceo/lead2"), "send", to="ceo", body="back", budget=1)  # to the parent: no hint
