# mypy: ignore-errors
"""Phase 0b, end to end, over real organizations on disk: one-off verdicts through MCP, the CLI and ``Org``; the quality view through root's MCP tool and
the CLI; its JSON; the marks of an organization that is a git repository and of the same one without git; files that do not parse; and that
``quality`` and ``health`` write nothing.

No scheduler, no LLM, no network: the team's runs are the test's own calls (``begin_run``, ``report``, ``end_run``)."""

import asyncio
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from testkit.cli_world import main
from testkit.e2e_world import build_server
from testkit.quality_schema import problems

from hirearchy.core import ROOT, Org
from hirearchy.settings import DEFAULT_CONFIG

SERVICE = "weekly-brief"
PLAYBOOK = "# Weekly brief\n\n1. Ask the researcher for sources on the topic.\n2. Have the writer draft at most 600 words.\n"
NOT_UTF8_OR_YAML = "---\nkey: [unclosed\n---\nbody\n"
NO_HISTORY = "unknown (no org history: the organization is not a git repository, or git is missing)"


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


@pytest.fixture
def org(tmp_path):
    """root -> lead, which offers `weekly-brief` (two criteria, 10 runs per request, a playbook)."""
    o = Org.init(tmp_path / "org", "Mission.", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Run the reports.", can_hire=True, max_children=2)
    o.define_service(
        ROOT, "lead", SERVICE, description="A one-page brief.", inputs=[{"name": "topic", "description": "what it is about", "required": True}],
        acceptance=["At most 600 words", "Every factual claim has a source URL"], deliverable={"description": "one markdown file"}, budget=10, playbook=PLAYBOOK,
    )
    return o


def deliver(org: Org, task, owner: str = "lead", status: str = "done"):
    """The owner handles ``task`` in one run and reports on it."""
    org.begin_run(owner)
    org.start_run_log(owner)
    result = org.report(owner, task.id, status, "Delivered.", lessons="Worked.")
    org.end_run(owner, ok=True)
    return result


def verdicts(org: Org) -> list:
    return [m for m in org.sent(ROOT) if m.type == "note" and m.feedback]


def quality(org: Org, *args: str) -> str:
    return org.runtime.quality_report.quality_text(*args)


# ------------------------------------------------------------------------------------------------- one-off verdicts


def test_one_off_feedback_through_mcp_cli_and_org(org, capsys):
    """8.1-8.3: root rates a task it sent without a service. MCP and `Org` default to `relayed`, the CLI to `human`; the refusals; the reply step."""
    first = org.delegate(ROOT, "lead", "Plain task", "goal", "criteria", budget=5)
    second = org.delegate(ROOT, "lead", "Another task", "goal", "criteria", budget=5)
    third = org.delegate(ROOT, "lead", "A third task", "goal", "criteria", budget=5)
    for task in (first, second, third):
        deliver(org, task)
    server = build_server(org, ROOT)

    said = call(server, "feedback", task_id=first.id, verdict="reject", note="Not this.")  # the MCP default: the assistant's own reading
    assert "Recorded as relayed (your own reading): quality counts it as no verdict of the user." in said
    org.feedback(ROOT, second.id, "accept")  # `Org` too
    main(["--root", str(org.root), "feedback", third.id, "reject", "--note", "Still not."])  # the user's own seat
    out = capsys.readouterr().out
    assert "Recorded" not in out and "Next:" not in out  # the CLI prints the receipt only (PC-5)
    sources = {m.reply_to: m.source for m in verdicts(org)}
    assert sources == {first.id: "relayed", second.id: "relayed", third.id: "human"}

    assert "is a one-off task" in fails(server, "feedback", task_id=first.id, verdict="reject", note="x", criterion=["C1"])
    assert "is not a task you sent" in fails(server, "feedback", task_id="nope", verdict="accept")
    human = call(server, "feedback", task_id=third.id, verdict="reject", note="Redo it.", source="human")
    assert 'Next: if the user wants it redone, send it back with delegate(to="lead"' in human


# ------------------------------------------------------------------------------------------------- the view


def test_quality_through_mcp_root_and_the_cli_say_the_same(org, capsys):
    task = org.request(ROOT, SERVICE, {"topic": "ai"})
    deliver(org, task)
    one_off = org.delegate(ROOT, "lead", "Plain task", "goal", "criteria", budget=5)
    deliver(org, one_off)
    server = build_server(org, ROOT)
    text = call(server, "quality")
    main(["--root", str(org.root), "quality"])
    assert capsys.readouterr().out == text + "\n"
    assert text.startswith("Quality of the work you asked for (derived from the files, nothing stored; for you and the user, never for agents).")
    assert f"{SERVICE} (offered by lead; client: you, human; unit: case; contract v1, playbook v1; approved 10 runs per request)" in text
    assert "One-off tasks you gave (client: you, human; unit: case; approved budget: each task's own)" in text
    assert call(server, "quality", service=SERVICE).count("One-off tasks you gave") == 0
    assert "no service named `nope`" in fails(server, "quality", service="nope")
    assert "quality" not in [t.name for t in asyncio.run(build_server(org, "lead").list_tools())]  # agents never get it


def test_quality_json_carries_the_playbook_lines_only_there(org, capsys):
    task = org.request(ROOT, SERVICE, {"topic": "ai"})
    deliver(org, task)
    main(["--root", str(org.root), "quality", "--json"])
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert raw == json.dumps(data, indent=2, sort_keys=True) + "\n" and problems(data) == []
    (record,) = data["services"]
    playbook = next(m for m in record["timeline"] if m["kind"] == "playbook")
    assert playbook["agent_written"] is True and any("Ask the researcher for sources" in line["text"] for line in playbook["lines"])
    assert "Ask the researcher" not in quality(org)  # the text never carries a playbook line
    assert record["cases"][0]["id"] == task.id and record["first_deliveries"]["no_verdict"] == 1


def test_an_org_md_that_does_not_parse_renders_with_the_defaults(org):
    task = org.request(ROOT, SERVICE, {"topic": "ai"})
    deliver(org, task)
    (org.root / "ORG.md").write_text(NOT_UTF8_OR_YAML, encoding="utf-8")
    text = quality(org)
    lines = text.splitlines()
    assert lines[1].startswith("Thresholds: the defaults (tunable): alarms need 3 judged cases;")
    assert lines[2] == "ORG.md cannot be read (its settings block does not parse): the default thresholds are used."
    assert "  cases: 1 (done 1, failed 0, blocked 0, open 0 (stalled 0))" in lines  # every other count still renders


def org_md(**changes) -> str:
    """ORG.md written through the product's defaults (flat scalars), with ``changes`` over them."""
    return "---\n" + "".join(f"{key}: {json.dumps(value)}\n" for key, value in {**DEFAULT_CONFIG, **changes}.items()) + "---\nMission.\n"


def git(org: Org, *args: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", *args], cwd=org.root, check=True, capture_output=True, env=env)


def snapshot(org: Org, message: str) -> None:
    git(org, "add", "-A")
    git(org, "commit", "-q", "--allow-empty", "-m", message)


def test_a_git_org_shows_charter_model_and_effort_marks(org):
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    (org.root / "ORG.md").write_text(org_md(), encoding="utf-8")
    snapshot(org, "1: the org as hired")
    charter = (org.root / "lead" / "AGENT.md").read_text(encoding="utf-8")
    (org.root / "lead" / "AGENT.md").write_text(charter + "\nAlways cite the source.\n", encoding="utf-8")
    snapshot(org, "2: the lead's charter")
    (org.root / "ORG.md").write_text(org_md(default_model="claude-opus-5.5"), encoding="utf-8")
    snapshot(org, "3: the default model")
    (org.root / "ORG.md").write_text(org_md(default_model="claude-opus-5.5", effort="xhigh"), encoding="utf-8")
    snapshot(org, "4: the effort")
    text = quality(org)
    assert re.search(r"^    \d{4}-\d\d-\d\d \d\d:\d\d lead: charter edited \(commit [0-9a-f]{12}\)$", text, re.MULTILINE)
    assert re.search(r'^    \S+ \S+ ORG\.md: default model "[^"]+" -> "claude-opus-5\.5"$', text, re.MULTILINE)
    assert re.search(r'^    \S+ \S+ ORG\.md: effort "[^"]+" -> "xhigh"$', text, re.MULTILINE)
    assert "charter edits and model changes:" not in text  # marks are listed, so the line is absent
    data = json.loads(json.dumps(org.runtime.quality_report.quality_data()))
    kinds = [m["kind"] for m in data["services"][0]["timeline"]]
    assert kinds.count("charter") == 1 and kinds.count("model") == 2 and data["services"][0]["history"] == {"known": True, "truncated": False, "skipped": 0}


def test_the_same_org_without_git_reads_unknown(org):
    shutil.rmtree(org.root / ".git", ignore_errors=True)
    (org.root / "lead" / "AGENT.md").write_text((org.root / "lead" / "AGENT.md").read_text(encoding="utf-8") + "\nMore.\n", encoding="utf-8")
    text = quality(org)
    assert f"    charter edits and model changes: {NO_HISTORY}" in text
    assert "charter edited" not in text
    assert json.loads(json.dumps(org.runtime.quality_report.quality_data()))["services"][0]["history"]["known"] is False


def test_files_that_do_not_parse_never_make_quality_raise(org):
    """18.2 and plan 7.5: one git org, four snapshots (a good org; an AGENT.md that does not parse; that AGENT.md repaired with a new body; an ORG.md
    that does not parse, also the working file), then a working AGENT.md and a stored SERVICE.v1.md that do not parse."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    task = org.request(ROOT, SERVICE, {"topic": "ai"})
    deliver(org, task)
    plain = org.delegate(ROOT, "lead", "Plain task", "goal", "criteria", budget=5)
    org.feedback(ROOT, task.id, "accept", "Good.", source="human")
    org.define_service(ROOT, "lead", SERVICE, add_acceptance=["Names its sources"], words="Please name the sources.")  # an amendment: v1 is kept in history/
    (org.root / "ORG.md").write_text(org_md(), encoding="utf-8")
    agent = org.root / "lead" / "AGENT.md"
    good = agent.read_text(encoding="utf-8")
    snapshot(org, "1: good ORG.md and AGENT.md")
    agent.write_text(NOT_UTF8_OR_YAML, encoding="utf-8")
    snapshot(org, "2: an AGENT.md that does not parse")
    agent.write_text(good + "\nEdited body.\n", encoding="utf-8")
    snapshot(org, "3: repaired, body edited")
    (org.root / "ORG.md").write_text(NOT_UTF8_OR_YAML, encoding="utf-8")
    snapshot(org, "4: an ORG.md that does not parse")

    text = quality(org)
    lines = text.splitlines()
    assert lines[1].startswith("Thresholds: the defaults (tunable)") and lines[2].startswith("ORG.md cannot be read")
    assert "  cases: 1 (done 1, failed 0, blocked 0, open 0 (stalled 0))" in lines
    assert "charter edited" not in text  # both pairs of the bad AGENT.md version are not compared
    assert "    charter edits and model changes: none (2 version(s) not compared: larger than 64 KiB, unreadable or not parseable)" in lines

    agent.write_text(NOT_UTF8_OR_YAML, encoding="utf-8")  # the working charter does not parse either: the runs stay counted
    assert ": runs not counted" not in quality(org) and "  cases: 1 (done 1," in quality(org)

    stored = org.root / "lead" / "services" / SERVICE / "history" / "SERVICE.v1.md"
    assert stored.is_file()
    stored.write_text(NOT_UTF8_OR_YAML, encoding="utf-8")
    broken = quality(org)
    assert re.search(
        rf"^{SERVICE} \(offered by lead\): cannot be read \((the criteria|the stored contract versions): does not parse \(\w+\)\)\.$", broken, re.MULTILINE,
    )
    assert "One-off tasks you gave (client: you, human;" in broken and "Blocked tasks moved past without a verdict: none." in broken
    assert plain.id in broken  # the one-off block still renders its case


def tree(root: Path) -> dict:
    """Every file of the organization: path -> (bytes, mtime in nanoseconds)."""
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns) for p in sorted(root.rglob("*")) if p.is_file()}


def test_quality_and_health_write_nothing(org):
    """I2: `quality` and health only read. The calls are made on the runtime's ports, with no MCP or CLI layer, so no tool-call event is written."""
    task = org.request(ROOT, SERVICE, {"topic": "ai"})
    deliver(org, task)
    org.feedback(ROOT, task.id, "reject", "No: not right.", source="human")
    plain = org.delegate(ROOT, "lead", "Plain task", "goal", "criteria", budget=5)
    deliver(org, plain)
    before = tree(org.root)
    quality_report = org.runtime.quality_report
    quality_report.quality_text()
    quality_report.quality_data()
    quality_report.quality_text(SERVICE)
    report = org.runtime.health_analyzer.org_health(ROOT)
    org.runtime.health_renderer.render_text(report)
    assert tree(org.root) == before


# ------------------------------------------------------------------------------------------------- the view and health agree (I5)

REVIEWER = "lead/reviewer"


def signed_off(org: Org, task, signer: str, artifacts: list[str] | None = None):
    """The lead's team delivers ``task``: ``signer`` (the reviewer) passes it first unless the lead signs it off alone."""
    org.begin_run("lead")
    org.start_run_log("lead")
    if signer != "lead":
        check = org.delegate("lead", signer, "Check", "goal", "criteria", budget=2)
        deliver(org, check, owner=signer)
    result = org.report("lead", task.id, "done", "Delivered.", artifacts=artifacts, lessons="Worked.")
    org.end_run("lead", ok=True)
    return result


def reject(org: Org, task, words: str, *, criterion: list[str] | None = None) -> None:
    note = org.feedback(ROOT, task.id, "reject", words, source="human")
    if criterion:  # the user's confirmed link: the rejection is about this criterion
        org.feedback(ROOT, task.id, "reject", f"It is about {criterion[0]}.", source="human", criterion=criterion, confirms=note.id)


def test_the_views_counted_and_not_its_escapes_equal_healths_per_verifier(org):
    """I5, D7: the view's verifier lines and health read one cause typing and one attribution. One world with every cause and no hand edit (no
    deliverable folder): the reviewer signs four deliveries (a miss, an untyped rejection, a gap in the contract, an accept) and the lead two alone (a
    relayed rework the user rejected, and a rejection of a delivery that carries over a relayed rework's artifact)."""
    org.hire("lead", "reviewer", "Reviewer", "Check.")
    artifact = org.root / "lead" / "work" / "out.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("The memo.\n", encoding="utf-8")
    shared = ["lead/work/out.md"]

    def ask(topic: str, **more):
        return org.request(ROOT, SERVICE, {"topic": topic}, **more)

    # every new request comes before the first rejection: clause 2 holds a new request while a rejection has no answer (only reworks follow)
    miss, plain, gap, good = (ask(t) for t in ("miss", "plain", "gap", "good"))
    for task in (miss, plain, gap, good):
        signed_off(org, task, REVIEWER)
    first = ask("relayed")
    signed_off(org, first, "lead")
    base = ask("carry")
    signed_off(org, base, "lead", shared)

    reject(org, miss, "Too long.", criterion=["C1"])  # the user confirms C1, which the task carried: reviewer-miss
    reject(org, plain, "No: not right.")  # nothing a rule can read: untyped
    reject(org, gap, "Always lead with the date.")  # a lasting word: contract-gap
    org.feedback(ROOT, good.id, "accept", source="human")

    relayed = ask("relayed", revises=first.id)  # no source: the assistant's own reading
    signed_off(org, relayed, "lead")
    reject(org, relayed, "No: not it.")  # a relayed-error

    carried = ask("carry", revises=base.id)  # relayed
    signed_off(org, carried, "lead", shared)
    again = ask("carry", revises=carried.id, source="human", base="latest")  # the user's own rework, from the current version, delivers the same file
    signed_off(org, again, "lead", shared)
    reject(org, again, "No: not it.")  # relayed-carry-over

    (record,) = json.loads(json.dumps(org.runtime.quality_report.quality_data()))["services"]
    assert record["files_error"] == "" and record["deliveries"]["not_as_delivered"] == []  # no hand edit
    assert sorted(e["cause"] for e in record["escapes"]) == ["contract-gap", "relayed-carry-over", "relayed-error", "reviewer-miss", "untyped"]
    view = {v["addr"]: v for v in record["verifiers"]}
    assert set(view) == {REVIEWER}  # the lead is the owner: when it signs off alone it is no verifier, its escapes are in the escape lines
    health = {addr: org.runtime.health_analyzer.agent_health(addr) for addr in ("lead", REVIEWER)}
    reviewer = health[REVIEWER]
    assert view[REVIEWER]["escapes"] == {"counted": {"reviewer-miss": 1, "untyped": 1}, "not_its": {"contract-gap": 1}}
    assert view[REVIEWER]["judged"] == 4 and (reviewer.escapes, reviewer.not_its, reviewer.judged) == (2, {"contract-gap": 1}, 4)
    # the owner holds every delivery of its service, whoever signed it off: its numbers are those of all the escape lines
    lead = health["lead"]
    by_attribution = {kind: [e["cause"] for e in record["escapes"] if e["attribution"] == kind] for kind in ("counted", "not its")}
    assert sorted(by_attribution["counted"]) == ["reviewer-miss", "untyped"]
    assert lead.escapes == len(by_attribution["counted"]) and lead.judged == record["deliveries"]["judged"] == 6
    assert lead.not_its == {cause: by_attribution["not its"].count(cause) for cause in sorted(by_attribution["not its"])}
    assert lead.not_its == {"contract-gap": 1, "relayed-carry-over": 1, "relayed-error": 1}
    text = org.runtime.health_renderer.render_text(org.runtime.health_analyzer.org_health(ROOT), causes=True)
    assert "escapes 2 of 4 judged (+1 not its: 1 contract-gap)" in text  # the reviewer, as root reads it
    assert "(+3 not its: 1 contract-gap, 1 relayed-error, 1 relayed-carry-over)" in text  # the lead, who owns all six

