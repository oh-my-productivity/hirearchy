"""Services (a standing task with a contract and a playbook) and reflection (lessons -> digest -> revise_playbook)."""

import asyncio

import pytest
import yaml
from testkit.services_world import (  # noqa: F401  (svc is a fixture)
    BRIEF, ENG, call, cli, contract_meta, define, deliver, fails, playbook_meta, request, svc, work,
)

from orgmcp import services
from orgmcp.core import ROOT
from orgmcp.server import build_server


# ------------------------------------------------------------------------------------ tools by role
def tool_names(org, addr):
    return {t.name for t in asyncio.run(build_server(org, addr).list_tools())}


CLIENT_TOOLS = {"services", "define_service", "request", "feedback"}


def test_tools_are_registered_by_role(org):
    assert not tool_names(org, ENG) & (CLIENT_TOOLS | {"revise_playbook"})  # a plain worker sees none
    assert CLIENT_TOOLS <= tool_names(org, "ceo") and "revise_playbook" not in tool_names(org, "ceo")
    assert CLIENT_TOOLS <= tool_names(org, ROOT) and "revise_playbook" not in tool_names(org, ROOT)
    define(org)
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    assert {"services", "revise_playbook"} <= tool_names(org, ENG) and not {"define_service", "request"} & tool_names(org, ENG)
    assert CLIENT_TOOLS | {"revise_playbook"} <= tool_names(org, "ceo")  # ceo is both a client and an owner
    org.hire(ROOT, "lone", "Lone worker", "Works alone.")
    define(org, owner="lone", name="lone-brief")
    assert tool_names(org, "lone") & (CLIENT_TOOLS | {"revise_playbook"}) == {"services", "revise_playbook"}


def test_the_services_tool_describes_what_you_can_request_and_offer(org):
    server = build_server(org, ROOT)
    assert "No services yet" in call(server, "services") and "define_service" in call(server, "services")
    define(org, playbook="Steps.")
    t1 = request(org, "ai")
    deliver(org, "ceo", t1, runs=3)
    org.feedback(ROOT, t1.id, "reject", "Bad.")
    org.revise_playbook("ceo", "weekly-brief", "Better steps.", "Case rejected for missing sources")
    out = call(server, "services")
    assert out.splitlines()[0] == "Services you can request (from your direct reports):"
    assert "- weekly-brief (offered by ceo; contract v1, playbook v2): A one-page brief" in out
    assert "inputs: topic* (what the brief is about), week (ISO week; default the current one)   (* required)" in out
    assert ("each request: 10 runs; acceptance criteria (ceo/services/weekly-brief/SERVICE.md):\n"
            "    1. At most 600 words\n    2. Every factual claim has a source URL\n  record:") in out
    assert "record: 1 request(s): 1 done, 0 failed, 0 open; 0 reworked; avg 3 runs; feedback 0 accept, 1 reject" in out
    assert '  playbook v2 (' in out and '"Case rejected for missing sources"' in out
    assert "Services you offer" not in out
    mine = call(build_server(org, "ceo"), "services")
    assert "Services you offer:" in mine and "playbook file: ceo/services/weekly-brief/PLAYBOOK.md" in mine
    assert "Services you can request" not in mine  # ceo's report offers nothing


# ----------------------------------------------------------------------------------------------- CLI
def test_cli_commands(org, capsys, tmp_path):
    criteria = tmp_path / "criteria.txt"
    criteria.write_text("At most 600 words\n- Every claim has a URL\n")
    playbook = tmp_path / "pb.md"
    playbook.write_text("## Steps\n1. Search.")
    cli(org, "define-service", "ceo", "weekly-brief", "--description", "A weekly brief.",
        "--input", "topic*:what it is about", "--input", "week:ISO week", "--acceptance", f"@{criteria}",
        "--acceptance", "Mention a risk", "--deliverable", "one file", "--format", "markdown", "--max-words", "600",
        "--path", str(tmp_path / "out"), "--budget", "8", "--playbook", f"@{playbook}", "--locked")
    meta, _ = contract_meta(org)
    assert meta["acceptance"] == ["At most 600 words", "Every claim has a URL", "Mention a risk"]
    assert meta["inputs"] == [{"name": "topic", "description": "what it is about", "required": True},
                              {"name": "week", "description": "ISO week", "required": False}]
    assert meta["deliverable"] == {"description": "one file", "format": "markdown", "max_words": 600, "path": str(tmp_path / "out")}
    assert meta["budget"] == 8 and meta["locked"] is True and playbook_meta(org)[0]["version"] == 1
    assert "defined service `weekly-brief`" in capsys.readouterr().out

    cli(org, "services")
    assert "weekly-brief (offered by ceo; contract v1, playbook v1)" in capsys.readouterr().out
    cli(org, "request", "weekly-brief", "--input", "topic=ai chips", "--input", "week=3", "--note", "Hurry")
    out = capsys.readouterr().out
    (task,) = org.outstanding(ROOT)
    assert task.id in out and task.budget == 8 and "- week: 3" in task.body and "Hurry" in task.body
    deliver(org, "ceo", task)
    cli(org, "feedback", task.id, "reject", "--note", "Too long")
    assert "feedback reject on" in capsys.readouterr().out
    assert [m.feedback for m in org.sent(ROOT) if m.type == "note"] == ["reject"]
    with pytest.raises(SystemExit):
        cli(org, "feedback", task.id, "reject")  # a rejection needs a note
    assert "needs a note" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli(org, "request", "weekly-brief", "--input", "no-equals-sign")
    assert "key=value" in capsys.readouterr().err
    cli(org, "retire-service", "ceo", "weekly-brief", "--reason", "done with it")
    assert "retired service" in capsys.readouterr().out and org.service_names("ceo") == []
    log = __import__("subprocess").run(["git", "log", "--format=%s"], cwd=org.root, capture_output=True, text=True).stdout
    assert "root: service weekly-brief of ceo" in log and "root: retired service" in log


# ------------------------------------------------------------------------------- the whole loop
def test_define_request_report_reject_reflect_revise_and_compare_versions(org):
    root = build_server(org, ROOT)

    out = call(root, "define_service", owner="ceo", name="weekly-brief", description=BRIEF["description"],
               acceptance=BRIEF["acceptance"], deliverable=BRIEF["deliverable"], budget=10, inputs=BRIEF["inputs"])
    assert "defined service `weekly-brief`" in out
    ceo = build_server(org, "ceo")  # the owner's run starts after the definition: it now has revise_playbook
    out = call(root, "request", service="weekly-brief", inputs={"topic": "ai"})
    assert "requested service `weekly-brief` from ceo" in out and "Call start() if the scheduler is not running." in out
    task = org.outstanding(ROOT)[0]

    # the owner's first run: no playbook yet
    prompt = org.run_prompt("ceo", work(org, "ceo", 2))
    assert "No playbook yet" in prompt and "# Reflect" not in prompt
    assert "pass `lessons`" in fails(ceo, "report", task_id=task.id, status="done", summary="Delivered.")
    out = call(ceo, "report", task_id=task.id, status="done", summary="Delivered.", lessons="Used 2 runs; no checks.")
    assert "reported done" in out and "This service has no playbook yet: write v1 now with revise_playbook" in out
    org.end_run("ceo", ok=True)
    assert "now v1" in call(ceo, "revise_playbook", service="weekly-brief", content="## Steps\n1. Search.",
                            reason="first draft")
    assert services.read_playbook(org, "ceo", "weekly-brief").version == 1

    # the client rejects the delivery
    out = call(root, "feedback", task_id=task.id, verdict="reject", note="Missing week-over-week changes.")
    assert "feedback reject recorded" in out
    assert "needs a note" in fails(root, "feedback", task_id=task.id, verdict="reject")

    # the next request: the prompt shows the rejection before the new message
    second = org.request(ROOT, "weekly-brief", {"topic": "chips"})
    prompt = org.run_prompt("ceo", work(org, "ceo", 1))
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "Evidence since v1:" in section and "Missing week-over-week changes." in section
    assert "Used 2 runs; no checks." in section
    out = call(ceo, "revise_playbook", service="weekly-brief",
               content="## Steps\n1. Search.\n2b. Compare with last week.", reason=f"case {task.id} rejected: no changes")
    assert "playbook of `weekly-brief` is now v2" in out
    out = call(ceo, "report", task_id=second.id, status="done", summary="Delivered again.", lessons="Step 2b worked.")
    assert "Lessons recorded. If they call for a playbook change now, use revise_playbook" in out
    org.end_run("ceo", ok=True)
    call(root, "feedback", task_id=second.id, verdict="accept")

    # stats show both versions
    listing = call(root, "services")
    assert "playbook v2" in listing and "2 request(s): 2 done, 0 failed, 0 open" in listing
    assert "feedback 1 accept, 1 reject" in listing
    per = services.stats_by_version(services.cases(org, "ceo", "weekly-brief"))
    # request 1 was delivered with no playbook (v1 was written after its report); request 2 was sent at v1 but
    # revised to v2 before it was worked on, so v2 is the version that delivered it
    assert sorted(per) == [0, 2] and [c.playbook for c in services.cases(org, "ceo", "weekly-brief")] == [0, 1]
    assert (per[0].reject, per[0].requests) == (1, 1) and (per[2].accept, per[2].requests) == (1, 1)
    # the evidence was consumed by the revision: nothing new until the next case finishes
    assert services.reflection_digest(org, "ceo", "weekly-brief") is not None  # case 2 finished after v2
    ids = [m.id for m in org.received(ROOT) if m.type == "result"]
    assert len(ids) == 2
    meta = yaml.safe_load((org.dir("ceo") / "services" / "weekly-brief" / "PLAYBOOK.md").read_text().split("---\n")[1])
    assert meta["version"] == 2 and meta["by"] == "ceo"


def test_a_locked_service_reports_without_the_revision_hint(org):
    define(org, locked=True)
    ceo = build_server(org, "ceo")
    task = request(org)
    work(org, "ceo")
    out = call(ceo, "report", task_id=task.id, status="done", summary="Delivered.", lessons="Fine.")
    assert out.startswith("reported done") and "revise_playbook" not in out
    assert "locked by root" in fails(ceo, "revise_playbook", service="weekly-brief", content="x", reason="r")
