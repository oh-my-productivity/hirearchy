"""Round F (runtime): charter rewrites keep the frontmatter, feedback is not a waiver, lessons on blocked reports,
the digest shows the latest lessons first, and a budget grant says what the recipient can do with it."""

import asyncio
import time

import pytest
import yaml

from orgmcp import services, templates
from orgmcp.core import ROOT, Org, OrgError, atomic_write
from orgmcp.server import build_server

ENG = "ceo/eng"


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


@pytest.fixture
def team(tmp_path):
    """root -> lead (manager; read+shell, inputs notes/) -> rev (read, confined to notes/, model set)."""
    for d in ("notes", "elsewhere"):
        (tmp_path / d).mkdir()
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read", "shell"], inputs=[str(tmp_path / "notes")])
    o.hire("lead", "rev", "Reviewer", "Review.", model="claude-sonnet-4.6", tools=["read"], inputs=[str(tmp_path / "notes")])
    return o


def charter_text(role, body="New body.", **extra):
    meta = {"role": role, **extra}
    return "---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n" + body + "\n"


# ------------------------------------------------------------------------------------------ 1. charter merge
def test_a_rewrite_with_only_role_keeps_tools_inputs_model_and_the_rest(team, tmp_path):
    before, _ = team.charter("lead/rev")
    assert before["tools"] == ["read"] and before["model"] == "claude-sonnet-4.6"
    team.write("lead", "lead/rev/AGENT.md", "---\nrole: Sharper reviewer\n---\n# Role\nNew body.\n")
    after, body = team.charter("lead/rev")
    assert after["role"] == "Sharper reviewer" and "New body." in body
    for key in ("model", "tools", "inputs", "can_hire", "max_children", "hired_by", "created"):
        assert after[key] == before[key], key
    assert after["inputs"] == [str(tmp_path / "notes")]


def test_a_key_set_explicitly_wins_even_when_empty(team):
    team.write("lead", "lead/rev/AGENT.md", charter_text("Reviewer", tools=[], model="claude-haiku-4.5"))
    after, _ = team.charter("lead/rev")
    assert after["tools"] == [] and after["model"] == "claude-haiku-4.5"
    assert after["inputs"]  # not set in the new text: kept


def test_authority_is_checked_on_the_merged_frontmatter(team, tmp_path):
    # kept `read` + new inputs outside the manager's own authority
    # inputs outside the manager's own authority are refused when set explicitly
    with pytest.raises(OrgError, match="inputs must be inside"):
        team.write("lead", "lead/rev/AGENT.md", charter_text("Reviewer", inputs=[str(tmp_path / "elsewhere")]))
    # a legacy charter (read, no workspace, no `inputs` key) merges to an unconfined read: refused for a confined manager
    atomic_write(team.dir("lead/rev") / "AGENT.md", "---\nrole: R\ntools: [read]\n---\nx\n")
    with pytest.raises(OrgError, match="needs an `inputs:` list"):
        team.write("lead", "lead/rev/AGENT.md", "---\nrole: R2\n---\nnew\n")
    assert "R2" not in (team.dir("lead/rev") / "AGENT.md").read_text()


def test_a_tool_the_manager_lacks_is_still_refused_when_set_explicitly(team):
    with pytest.raises(OrgError):
        team.write("lead", "lead/rev/AGENT.md", charter_text("Reviewer", tools=["read", "write"]))
    assert team.charter("lead/rev")[0]["tools"] == ["read"]  # nothing was written


def test_the_write_reply_lists_kept_and_changed_keys(team):
    server = build_server(team, "lead")
    out = call(server, "write", path="lead/rev/AGENT.md", content=charter_text("Sharper", tools=["read"], max_children=2))
    assert "wrote lead/rev/AGENT.md" in out
    assert "kept from the old frontmatter (not in your text):" in out
    for key in ("model", "inputs", "can_hire", "hired_by", "created"):
        assert key in out.split("kept from the old frontmatter")[1].split("changed")[0]
    assert "role: Reviewer -> Sharper" in out and "max_children: 5 -> 2" in out
    assert "tools" not in out.split("kept from the old frontmatter")[1].split(".")[0]  # set explicitly, unchanged
    out = call(server, "write", path="lead/rev/AGENT.md", content=charter_text("Sharper", tools=[]))
    assert "tools: [read] -> []" in out


def test_other_writes_have_no_note(team):
    server = build_server(team, "lead")
    assert call(server, "write", path="lead/MEMORY.md", content="m") == "wrote lead/MEMORY.md (organization file)"


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


def work(org, addr, runs=1):
    batch = org.begin_run(addr)
    for _ in range(runs):
        org.start_run_log(addr)
        time.sleep(0.002)
    return batch


def deliver(org, task, status="done", lessons="ok"):
    work(org, "ceo")
    msg = org.report("ceo", task.id, status, "Delivered.", lessons=lessons)
    org.end_run("ceo", ok=True)
    return msg


def test_feedback_note_starts_with_the_fixed_header_and_then_the_clients_words(svc):
    task = svc.request(ROOT, "brief", {"topic": "ai"})
    deliver(svc, task)
    note = svc.feedback(ROOT, task.id, "accept", "deliver as is")
    first, _, rest = note.body.partition("\n\n")
    assert first == (
        "Client feedback for reflection only: it does not change this task's acceptance criteria or outcome; "
        "report `done` only if every criterion is met."
    )
    assert rest == "deliver as is"
    assert services.feedback_text(note) == "deliver as is"
    assert services.feedback_text(svc.feedback(ROOT, task.id, "accept")) == ""


def test_the_digest_quotes_the_clients_words_without_the_header(svc):
    task = svc.request(ROOT, "brief", {"topic": "ai"})
    deliver(svc, task)
    svc.feedback(ROOT, task.id, "reject", "Missed two items.")
    digest = services.reflection_digest(svc, "ceo", "brief")
    assert 'client feedback: reject "Missed two items."' in digest and "reflection only" not in digest


# ------------------------------------------------------------------------------------------ 4. blocked lessons
def test_a_blocked_report_on_a_service_request_requires_lessons(svc):
    task = svc.request(ROOT, "brief", {"topic": "ai"})
    work(svc, "ceo")
    with pytest.raises(OrgError, match="pass `lessons`.*blocked"):
        svc.report("ceo", task.id, "blocked", "Cannot read the notes.")
    res = svc.report("ceo", task.id, "blocked", "Cannot read the notes.", lessons="Reviewer had no inputs.")
    assert services.lessons_of(res) == "Reviewer had no inputs."
    plain = svc.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    assert svc.report("ceo", plain.id, "blocked", "Waiting.").status == "blocked"  # plain tasks: still optional


def test_the_report_tool_docstring_says_lessons_are_required_for_blocked(svc):
    tools = {t.name: t for t in asyncio.run(build_server(svc, "ceo").list_tools())}
    assert "whatever the status - done, failed or blocked" in tools["report"].description


# ------------------------------------------------------------------------------------------ 5. digest order
def test_the_digest_shows_the_latest_lessons_first_and_earlier_ones_after(svc):
    first = svc.request(ROOT, "brief", {"topic": "ai"})
    deliver(svc, first, lessons="Ran cleanly; no changes needed.")
    rework = svc.request(ROOT, "brief", {"topic": "ai"}, revises=first.id, budget=4)
    deliver(svc, rework, lessons="Two items were missed: add a pre-read step.")
    digest = services.reflection_digest(svc, "ceo", "brief")
    line = next(x for x in digest.splitlines() if x.startswith("- case "))
    assert line.index('lessons: "Two items were missed') < line.index('earlier: "Ran cleanly; no changes needed.')


# ------------------------------------------------------------------------------------------ 6. grant hint
def test_delegable_arithmetic(org):
    org.send(ROOT, "ceo", "runs", budget=3)
    assert org.delegable("ceo") == (3, 0, 2)
    org.delegate("ceo", ENG, "t", "g", "c", budget=1)
    assert org.delegable("ceo") == (2, 1, 0)
    org.send(ROOT, "ceo", "more", budget=1)
    assert org.delegable("ceo") == (3, 1, 1)
    assert org.delegable(ENG) == (1, 0, 0)  # floor at 0


def test_grant_hint_says_plainly_when_the_recipient_cannot_delegate(org):
    org.send(ROOT, "ceo", "runs", budget=3)
    org.delegate("ceo", ENG, "t", "g", "c", budget=1)
    hint = org.grant_hint("ceo")
    assert hint == (
        "`ceo` now has 2 run(s) and 1 outstanding delegation(s): with 2 run(s) and 1 outstanding delegation(s) it "
        "cannot delegate anything; it can only process results or work itself - grant at least 1 more "
        "(a budget of 3) to allow one delegation of 1 run."
    )
    org.send(ROOT, "ceo", "more", budget=1)
    assert org.grant_hint("ceo") == "`ceo` now has 3 run(s) and 1 outstanding delegation(s); with one more delegation it can hand down at most 1 run(s)."


def test_grant_hint_needs_a_recipient_that_can_hire(org):
    org.send("ceo", ENG, "x")  # no budget, no hint needed
    assert org.grant_hint(ENG) == ""


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
