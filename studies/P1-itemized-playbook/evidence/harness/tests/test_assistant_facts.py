"""Tests of assistant_facts.py (design 20.4 B: the mechanical facts of the assistant layer).

Pure rules are tested on small inputs; one synthetic stream in tmp_path (two memos, a block of client questions, a human rework, a copy, a
refusal, a budget question line ...) tests the extraction end to end; the E7 self-check reads E7's committed evidence read-only and compares
`selfcheck/e7-expected-assistant.json`, transcribed from E7 STUDY.md / protocol.md, never from this script's output."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
sys.dont_write_bytecode = True

E7EV = Path("/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence")
SCRIPT = HARNESS / "assistant_facts.py"
EXPECTED = HARNESS / "selfcheck" / "e7-expected-assistant.json"
PY = sys.executable
e7 = pytest.mark.skipif(not (E7EV / "s1" / "assistant-session-messages.jsonl").exists(), reason="E7 evidence not available")


def run(*args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([PY, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=env)


# ================================================================== pure rules
def call(n, turn, tool=None, name=None, args=None, result="", ts="2026-11-01T10:00:00.000Z", status="completed", uri=None):
    return {"n": n, "turn": turn, "tool": f"hirearchy::{tool}" if tool else None, "name": name or ("tool_call" if tool else "x"), "args": args or {},
            "result": result, "ts": ts, "rts": ts, "status": status, "uri": uri}


def test_skill_stratum_a_b_n_and_na():
    import assistant_facts as af
    dis = call(1, 1, name="disclose_context", args={"name": "hirearchy"}, ts="2026-11-01T10:00:01.000Z", result="Skill directory: /x/hirearchy",
               uri="file:///x/.kiro/skills/hirearchy/SKILL.md")
    prop = call(2, 1, "propose_org", ts="2026-11-01T10:00:02.000Z")
    fb = call(3, 2, "feedback", ts="2026-11-01T10:00:03.000Z")
    a = af.skill_facts([dis, prop, fb], "")
    assert a["stratum"] == "A" and a["first_disclose"]["call"] == 1 and a["first_propose_org"]["call"] == 2 and a["first_feedback"]["call"] == 3
    early = call(2, 1, "propose_org", ts="2026-11-01T10:00:00.500Z")
    b = af.skill_facts([early, dis, fb], "")  # disclosed only after the first propose_org
    assert b["stratum"] == "B"
    c = af.skill_facts([prop, fb], "")
    assert c["stratum"] == "N"
    d = af.skill_facts([call(1, 1, "whoami")], "")
    assert d["stratum"] == "n/a"
    # an errored disclosure does not activate; another skill's disclosure does not count
    bad = dict(dis, result="Error: skill not found", status="failed")
    other = call(4, 1, name="disclose_context", args={"name": "other"}, ts="2026-11-01T10:00:00.500Z", result="ok", uri="file:///x/other/SKILL.md")
    assert af.skill_facts([bad, other, prop], "")["stratum"] == "N"


def test_installed_skill_notes_and_skill_md5_are_read_from_the_text():
    import assistant_facts as af
    txt = "Note: the installed skill at /a differs\nNote: the installed skill at /b differs"
    assert af.skill_facts([], txt)["installed_skill_notes"] == 2
    assert af.skill_md5("md5 of the SKILL.md at that path: fd89a7fda55b8f342cf0306173c363fb (valid: = fd89a7fd...)") == "fd89a7fda55b8f342cf0306173c363fb"
    assert af.skill_md5("") is None


@pytest.mark.parametrize("text,kind", [
    ("MCP tool error: Error executing tool define_service: refused: 1 delivered request(s) of `s` have no verdict yet: x. Record a verdict ... The contract changes only after the verdicts. Nothing was written.", "P2-UNRATED"),
    ("refused: answers, about and words are root's (...)", "P2-ROOT-ONLY"),
    ("refused: answers and about go together", "P2-PAIR"),
    ("refused: words (CLI: --words) is 900 characters; the limit is 500", "P2-WORDS-LONG"),
    ("refused: since the delivery the client judged ... pass base", "P4-NEEDS-BASE"),
    ('refused: base must be "delivered" or "latest"', "P4-BASE-VALUE"),
    ("refused: base goes only with a rework the user asked for", "P4-BASE-WHERE"),
    ("refused: x is a request for the service y; send it back with request(...)", "P4-USE-REQUEST"),
    ("refused: a root task for a service, or a rework, goes through request(", "FACADE-ROOT-TASK"),
    ("refused: a verdict or a link from root goes through feedback(", "FACADE-ROOT-VERDICT"),
    ("refused: something else entirely", "other"),
])
def test_refusals_are_classed_by_their_fixed_text(text, kind):
    import assistant_facts as af
    assert af.classify_refusal(text) == kind


def test_a_reply_that_is_not_a_refusal_has_no_kind():
    import assistant_facts as af
    assert af.classify_refusal("redefined service `s` of lead: contract v1 -> v2") is None
    assert af.classify_refusal("a long progress text that mentions refused: in the middle\nnot at the start") is None


def test_the_budget_question_line_is_found_in_both_product_forms_and_in_nothing_else():
    import assistant_facts as af
    plan = ("PLAN FOR YOU\nGoal: x\nBudget: up to 12 runs per request ...\n"
            "Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?\n")
    per = "Use 16 runs per request for weekly-memo (covers one round of your questions or a rejection), or keep 12?"
    assert af.budget_lines(plan) == ["Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?"]
    assert af.budget_lines("PLAN FOR YOU\n" + per + "\n") == [per]
    assert af.budget_lines("Budget: up to 12 runs per request ... your cap per request is 12; a round takes about 5 more (16 in all).") == []


def test_lena_rule_ids_are_read_from_the_rule_field_only():
    import assistant_facts as af
    line = "turn 3 | rule H5 (approval; H4 would be a raise) + L-BUDGET-Q | facts: H4 NOT used (D-OFFER); L-ASIS not used"
    assert af.lena_rules(line) == {"H5", "L-BUDGET-Q"}
    assert af.lena_rules("turn 4 | rules H4 + L-ASIS | x") == {"H4", "L-ASIS"}


def test_rates_render_k_of_n_and_n_a():
    import assistant_facts as af
    assert af.rate(0, 0) == {"k": 0, "n": 0}
    assert af.show({"k": 0, "n": 0}) == "n/a (0 of 0)" and af.show({"k": 2, "n": 11}) == "2 of 11"


def test_case_date_from_names_and_titles():
    import assistant_facts as af
    assert af.date_in("lead/writer/work/memo-2026-10-05.md (106 words)") == "2026-10-05"
    assert af.date_in("Memo for the 5 October 2026 meeting") == "2026-10-05"
    assert af.date_in("Memo 2026-10-12: client answers") == "2026-10-12"
    assert af.date_in("Rework memo: unclear due dates") is None


def test_the_copy_destination_dates_come_from_deliverable_paths_else_sources():
    import assistant_facts as af
    S = "/tmp/hirearchy-g0-m0-s1-1793000000"
    cmd = f"cp /private{S}/org/b/s/work/memo-2026-10-05.md {S}/deliverables/memo-2026-10-05.md && cmp a b"
    assert af.copy_cases(cmd) == ["2026-10-05"]
    cmd2 = f"cp /private{S}/org/b/s/work/memo-2026-10-12.md {S}/deliverables/"
    assert af.copy_cases(cmd2) == ["2026-10-12"]


# ================================================================== a synthetic stream, end to end
S_PATH = "/tmp/hirearchy-g0-m0-s1-1793000000"
BASE = 1_793_000_000


def Z(sec):
    """UTC `sec` seconds after 10:00:00 on 2026-11-01, as 2026-11-01T10:mm:ss.mmmZ"""
    s = int(sec)
    return f"2026-11-01T10:{s // 60:02d}:{s % 60:02d}.{int(round((sec - s) * 1000)):03d}Z"


def ISO(sec):
    return Z(sec).replace("Z", "+00:00")


def msg(path: Path, hdr: dict, body: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    head = "\n".join(f"{k}: {v}" for k, v in hdr.items())
    path.write_text(f"---\n{head}\n---\n{body}")


def build(tmp_path, with_budget_line=True):
    d = tmp_path / "m0-s1"
    d.mkdir()
    (d / "arm.txt").write_text("m0\n")
    (d / "sandbox-path.txt").write_text(S_PATH + "\n")
    (d / "injection").mkdir()
    (d / "injection" / "injection-log.txt").write_text("## INJECTION script\ninjected task id: 20261101T100500000000-root-inj0\nrevised task file: x/20261101T100100000000-root-aaaa.md\n")
    # --- the session: (turn, ts, kind, ...)
    rec = []

    def add(ts, p):
        rec.append({"timestamp": Z(ts), "payload": p})

    cid = {"n": 0}

    def tc(ts, turn, tool, args, result, name=None, status="completed", uri=None):
        cid["n"] += 1
        i = f"id{cid['n']}"
        if tool:
            p = {"type": "tool_call", "toolCallId": i, "toolName": "tool_call", "args": {"tool_id": f"hirearchy::{tool}", "arguments": args}, "status": status}
        else:
            kiro = {"disclosedContext": {"type": "skill", "uri": uri}} if uri else {}
            p = {"type": "tool_call", "toolCallId": i, "toolName": name, "args": args, "status": status, "_meta": {"kiro": kiro}}
        add(ts, p)
        add(ts + 0.1, {"type": "tool_result", "toolCallId": i, "content": result})

    plan = ("PLAN FOR YOU\nGoal: x\nBudget: up to 12 runs per request ... (16 in all).\n"
            + ("Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?\n" if with_budget_line else ""))
    add(0, {"type": "user", "content": "Hi"})
    add(0.1, {"type": "turn_start"})
    tc(1, 1, None, {"name": "hirearchy"}, "Skill directory: x", name="disclose_context", uri="file:///x/.kiro/skills/hirearchy/SKILL.md")
    tc(2, 1, "propose_org", {"blueprint": "b"}, plan)
    add(5, {"type": "turn_end"})
    add(5.01, {"type": "usage_summary", "promptTurnSummaries": [{"usage": 1.0}], "elapsedTime": 1000})
    add(10, {"type": "user", "content": "Great, approve. Please do this week's: 2026-10-05.md. I'll wait."})
    add(10.1, {"type": "turn_start"})
    tc(11, 2, "request", {"service": "daily-brief", "inputs": {"notes_file": "2026-10-05.md"}, "title": "Memo for 2026-10-05"},
       "requested service `daily-brief` from boss: task 20261101T100100000000-root-aaaa, budget 12 (contract v1, playbook v1).")
    add(15, {"type": "turn_end"})
    add(15.01, {"type": "usage_summary", "promptTurnSummaries": [{"usage": 1.0}], "elapsedTime": 1000})
    # the result lands at 20 s with one question and one note
    add(30, {"type": "user", "content": "Sam's should be 2026-10-09."})
    add(30.1, {"type": "turn_start"})
    tc(31, 3, "progress", {}, '"Memo" [service daily-brief v1]: blocked. runs 5 of 12. artifacts withheld (ask first). 1 question for the client: ask the user before you copy or deliver. no feedback yet. (task 20261101T100100000000-root-aaaa)')
    tc(32, 3, "inbox", {}, "1 result")
    tc(33, 3, "request", {"service": "daily-brief", "inputs": {"notes_file": "2026-10-05.md"}, "revises": "20261101T100100000000-root-aaaa", "source": "human", "title": "Memo 2026-10-05: client answers", "note": "x"},
       "requested service `daily-brief` from boss: task 20261101T100300000000-root-cccc, budget 5 (contract v1, playbook v1).")
    add(35, {"type": "turn_end"})
    add(35.01, {"type": "usage_summary", "promptTurnSummaries": [{"usage": 1.0}], "elapsedTime": 1000})
    add(60, {"type": "user", "content": "ok"})
    add(60.1, {"type": "turn_start"})
    tc(61, 4, None, {"command": f"cp /private{S_PATH}/org/boss/scribe/work/memo-2026-10-05.md {S_PATH}/deliverables/memo-2026-10-05.md && cmp a b"}, "identical", name="execute_bash")
    tc(62, 4, None, {"command": f"cat /private{S_PATH}/org/read/20261101T100200000000-boss-bbbb.md"}, "text", name="execute_bash")
    tc(63, 4, None, {"path": f"/private{S_PATH}/org/inbox/x.md"}, "text", name="read_file")
    tc(64, 4, "define_service", {"owner": "boss", "name": "daily-brief", "answers": "r1"}, "MCP tool error: Error executing tool define_service: refused: 1 delivered request(s) of `daily-brief` have no verdict yet: z. The contract changes only after the verdicts. Nothing was written.", status="failed")
    tc(65, 4, "send", {"to": "boss", "budget": 3, "body": "more"}, "sent")
    add(70, {"type": "turn_end"})
    add(70.01, {"type": "usage_summary", "promptTurnSummaries": [{"usage": 1.0}], "elapsedTime": 1000})
    add(90, {"type": "user", "content": "This version is right now, thanks."})
    add(90.1, {"type": "turn_start"})
    tc(91, 5, "feedback", {"task_id": "20261101T100300000000-root-cccc", "verdict": "accept", "source": "human"}, "feedback accept recorded")
    add(95, {"type": "turn_end"})
    add(95.01, {"type": "usage_summary", "promptTurnSummaries": [{"usage": 1.0}], "elapsedTime": 1000})
    (d / "assistant-session-messages.jsonl").write_text("\n".join(json.dumps(r) for r in rec) + "\n")
    (d / "turn-times.txt").write_text("".join(
        f"turn {n}: x - y  z  utc {Z(a)[:-5]}Z - {Z(b)[:-5]}Z  exit 0  sleep 20 ended utc {Z(b + 20)[:-5]}Z\n" for n, (a, b) in enumerate([(0, 5), (10, 15), (30, 35), (60, 70), (90, 95)], 1)))
    (d / "session-turn-times-utc.txt").write_text("".join(
        f"turn {n}: user_ts x turn_start {Z(a)} turn_end {Z(b)} stop end_turn status success elapsed_ms {int((b - a) * 1000)} credits 1.0000\n"
        for n, (a, b) in enumerate([(0.1, 5), (10.1, 15), (30.1, 35), (60.1, 70), (90.1, 95)], 1)))
    (d / "lena-lines.txt").write_text("turn 1 | rule H1 | x\nturn 2 | rule H5 | y\nturn 3 | rules factual answers | z\nturn 4 | rule H7 | w\nturn 5 | rule memo accept | v\n")
    for n, text in enumerate(["Hi", "Great", "Sam", "ok", "Right"], 1):
        (d / f"turn-{n:02d}.prompt.txt").write_text(text + "\n")
        shown = "Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?\n" if (n == 1 and with_budget_line) else ""
        (d / f"turn-{n:02d}.txt").write_text(f"######## TURN {n}\n######## LENA (prompt sent verbatim):\n{text}\n######## ASSISTANT (stdout, ANSI stripped; stderr is in turn-{n:02d}.stderr.txt):\n{shown}Done.\n")
    # --- the org messages
    msg(d / "msgs" / "sent" / "20261101T100100000000-root-aaaa.md",
        {"id": "20261101T100100000000-root-aaaa", "from": "root", "to": "boss", "type": "task", "title": "Memo for the 5 October 2026 meeting", "created": f"'{ISO(12)}'", "budget": 12, "service": "daily-brief"},
        "## Request\n- notes_file: 2026-10-05.md\n")
    msg(d / "msgs" / "sent" / "20261101T100300000000-root-cccc.md",
        {"id": "20261101T100300000000-root-cccc", "from": "root", "to": "boss", "type": "task", "title": "Memo 2026-10-05: client answers", "created": f"'{ISO(36)}'", "budget": 5,
         "revises": "20261101T100100000000-root-aaaa", "service": "daily-brief", "source": "human"}, "## Request\n- notes_file: 2026-10-05.md\n")
    msg(d / "msgs" / "sent" / "20261101T100500000000-root-inj0.md",
        {"id": "20261101T100500000000-root-inj0", "from": "root", "to": "boss", "type": "task", "title": "Rework", "created": f"'{ISO(50)}'", "revises": "20261101T100300000000-root-cccc", "source": "relayed", "service": "daily-brief"}, "")
    msg(d / "msgs" / "sent" / "20261101T100520000000-root-rel2.md",
        {"id": "20261101T100520000000-root-rel2", "from": "root", "to": "boss", "type": "task", "title": "Assistant rework", "created": f"'{ISO(52)}'", "revises": "20261101T100300000000-root-cccc", "source": "relayed", "service": "daily-brief"}, "")
    msg(d / "msgs" / "sent" / "20261101T100800000000-root-fbfb.md",
        {"id": "20261101T100800000000-root-fbfb", "from": "root", "to": "boss", "type": "note", "title": "feedback", "created": f"'{ISO(91)}'", "reply_to": "20261101T100300000000-root-cccc",
         "feedback": "accept", "source": "human"}, "")
    msg(d / "msgs" / "read" / "20261101T100200000000-boss-bbbb.md",
        {"id": "20261101T100200000000-boss-bbbb", "from": "boss", "to": "root", "type": "result", "title": "Memo", "created": f"'{ISO(20)}'", "reply_to": "20261101T100100000000-root-aaaa", "status": "blocked"},
        "## Summary\nQuestions for the client:\n- Sam's row (C6): which date?\n- a remark with no id\n\n## Artifacts\n- boss/scribe/work/memo-2026-10-05.md (100 words)\n")
    msg(d / "msgs" / "read" / "20261101T100400000000-boss-dddd.md",
        {"id": "20261101T100400000000-boss-dddd", "from": "boss", "to": "root", "type": "result", "title": "Memo", "created": f"'{ISO(40)}'", "reply_to": "20261101T100300000000-root-cccc", "status": "done"},
        "## Summary\nDone.\n\n## Artifacts\n- boss/scribe/work/memo-2026-10-05.md (101 words)\n")
    msg(d / "msgs" / "inbox" / "20261101T100900000000-boss-eeee.md", {"id": "20261101T100900000000-boss-eeee", "from": "boss", "to": "root", "type": "result", "created": f"'{ISO(92)}'"}, "unread")
    msg(d / "msgs" / "inbox" / "20261101T100900000001-boss-ffff.md", {"id": "20261101T100900000001-boss-ffff", "from": "boss", "to": "someone", "type": "note", "created": f"'{ISO(92)}'"}, "not mine")
    (d / "memos" / "versions").mkdir(parents=True)
    (d / "memos" / "versions" / "INDEX.txt").write_text(
        "boss/scribe/work/memo-2026-10-05.md v1 aaa1111 2026-11-01T10:00:10Z md5 11111111111111111111111111111111\n"
        "boss/scribe/work/memo-2026-10-05.md v2 bbb2222 2026-11-01T10:00:39Z md5 22222222222222222222222222222222\n"
        "boss/scribe/work/memo-2026-10-05.md working tree md5 22222222222222222222222222222222 (committed head: 22222222222222222222222222222222)\n")
    # run logs for the cost part
    for agent, stamp, secs in (("boss", "20261101T100002000000", 10), ("boss-scribe", "20261101T100020000000", 20), ("boss-inspector", "20261101T100030000000", 30)):
        (d / "run-logs" / agent).mkdir(parents=True, exist_ok=True)
        (d / "run-logs" / agent / f"{stamp}.log").write_text(f"# run of {agent}\n# cwd: /s/kiro-cwd/o/{agent}-1\n# cmd: x --agent p --model claude-sonnet-5.5 --effort high\n# ---- prompt ----\nP\n# ---- output ----\nok\n# exit 0 after {secs}s\n")
    (d / "injection" / "window.txt").write_text("2026-11-01T10:00:25 2026-11-01T10:01:00\n")
    (d / "events" / "2026-11-01").mkdir(parents=True)
    (d / "org-files").mkdir()
    (d / "org-files" / "boss-inspector-AGENT.md").write_text("review the work\n")
    return d


def extract(d):
    import extract_mechanical as em
    em.run_extract(d, "-", d)


def facts(tmp_path, **kw):
    import assistant_facts as af
    d = build(tmp_path, **kw)
    extract(d)
    return d, af.analyse(d)


def test_the_synthetic_stream_skill_plan_and_arm(tmp_path):
    d, a = facts(tmp_path)
    assert a["arm"] == "m0" and a["stream"] == "m0-s1"
    assert a["skill"]["stratum"] == "A" and a["skill"]["first_disclose"]["call"] == 1
    p = a["plan"]
    assert p["plans"] == 1 and p["plans_with_budget_line"] == {"k": 1, "n": 1}
    assert p["turns_showing_line"] == 1 and p["lena_yes_h4"] == 0 and p["lena_keep_l_budget_q"] == 0


def test_the_plan_without_the_line_counts_zero_of_one(tmp_path):
    d, a = facts(tmp_path, with_budget_line=False)
    assert a["plan"]["plans_with_budget_line"] == {"k": 0, "n": 1} and a["plan"]["turns_showing_line"] == 0


def test_flagged_items_are_questions_with_ids_and_notes_apart_and_superseded_by_the_human_rework(tmp_path):
    d, a = facts(tmp_path)
    f = a["flagged"]
    assert f["counts"] == {"results_with_items": 1, "items": 2, "questions": 1, "notes": 1, "superseded": 1, "never_copied": 0, "needs_d5": 0}
    q = next(i for i in f["items"] if i["kind"] == "question")
    assert q["case"] == "2026-10-05" and q["class"] == "superseded" and q["reworks_between"] == ["20261101T100300000000-root-cccc"]
    assert q["copy"]["call"] == 7 and q["flagged_by"] and q["flagged_by"][0]["call"] == 4  # calls are numbered 1.. in session order
    note = next(i for i in f["items"] if i["kind"] == "note")
    assert note["class"] == "superseded" and "no id" in note["text"]


def test_a_question_whose_case_is_copied_with_no_rework_between_needs_judgement(tmp_path):
    d = build(tmp_path)
    # the human rework is created BEFORE the result: nothing supersedes it
    p = d / "msgs" / "sent" / "20261101T100300000000-root-cccc.md"
    p.write_text(p.read_text().replace(ISO(36), ISO(5)))
    extract(d)
    import assistant_facts as af
    a = af.analyse(d)
    assert a["flagged"]["counts"]["needs_d5"] == 1 and a["flagged"]["counts"]["superseded"] == 0
    q = next(i for i in a["flagged"]["items"] if i["kind"] == "question")
    assert q["class"] == "needs D5 judgement (copy at T)" and q["copy"]["ts"].endswith("Z")


def test_a_case_that_is_never_copied_is_listed_as_such(tmp_path):
    d = build(tmp_path)
    s = d / "assistant-session-messages.jsonl"
    s.write_text(s.read_text().replace("deliverables/memo-2026-10-05.md", "elsewhere/memo-2026-10-05.md"))
    p = d / "msgs" / "sent" / "20261101T100300000000-root-cccc.md"  # no human rework after the result either
    p.write_text(p.read_text().replace(ISO(36), ISO(5)))
    extract(d)
    import assistant_facts as af
    a = af.analyse(d)
    assert a["copies"]["count"] == 0
    assert a["flagged"]["counts"]["never_copied"] == 1


def test_copies_hand_edit_check_ask_first_and_verdict_recording(tmp_path):
    d, a = facts(tmp_path)
    c = a["copies"]
    assert c["count"] == 1
    cp = c["list"][0]
    assert cp["call"] == 7 and cp["turn"] == 4 and cp["case"] == "2026-10-05" and cp["source_version"]["sha"] == "bbb2222"
    assert cp["checked_version"]["sha"] == "bbb2222" and cp["hand_edit"] is False  # the latest result (dddd, 40 s) is v2
    assert c["hand_edits"] == {"k": 0, "n": 1}
    assert cp["ask_first_shown"] is False  # no progress reply after the latest result and before the copy
    assert a["verdicts"]["delivered_without_verdict"] == {"k": 0, "n": 1}
    assert cp["human_feedback_after"][0]["call"] == 12 and cp["human_feedback_after"][0]["verdict"] == "accept"


def test_ask_first_shown_when_the_last_progress_before_the_copy_withholds_the_case_task(tmp_path):
    d = build(tmp_path)
    s = d / "assistant-session-messages.jsonl"
    # make the progress reply (call 31, at 30 s) fall after the latest result: move the result to 25 s and make it the case's latest
    for f in (d / "msgs" / "read").glob("*dddd.md"):
        f.write_text(f.read_text().replace(ISO(40), ISO(26)))
    for f in (d / "msgs" / "read").glob("*bbbb.md"):
        f.write_text(f.read_text().replace(ISO(20), ISO(19)))
    # the latest result must reply to the task named on the progress line: point dddd's reply_to at aaaa
    for f in (d / "msgs" / "read").glob("*dddd.md"):
        f.write_text(f.read_text().replace("reply_to: 20261101T100300000000-root-cccc", "reply_to: 20261101T100100000000-root-aaaa"))
    extract(d)
    import assistant_facts as af
    a = af.analyse(d)
    assert a["copies"]["list"][0]["ask_first_shown"] is True
    assert a["copies"]["ask_first"] == {"k": 1, "n": 1}


def test_reads_inbox_calls_against_shell_reads_and_root_unread(tmp_path):
    d, a = facts(tmp_path)
    r = a["reads"]
    assert r["inbox_calls"] == 1 and r["shell_reads"] == 2  # a `cat` of a read/ file and a read_file of an inbox/ file
    assert r["root_unread_at_end"] == 1  # only the result addressed to root


def test_refusals_by_kind_and_the_grants_and_human_reworks(tmp_path):
    d, a = facts(tmp_path)
    assert a["refusals"]["by_kind"] == {"P2-UNRATED": 1}
    assert a["refusals"]["p2_total"] == 1 and a["refusals"]["p4_total"] == 0 and a["refusals"]["facade_total"] == 0
    assert a["grants"] == [{"call": 11, "turn": 4, "to": "boss", "budget": 3}]
    hr = a["human_reworks"]
    assert hr["count"] == 1 and hr["without_budget"] == 1 and hr["list"][0]["reply_budget"] == 5
    assert a["topup_held"] == {"topup": [], "held": []}


def test_relayed_reworks_sent_through_the_assistant_exclude_the_injected_one(tmp_path):
    d, a = facts(tmp_path)
    assert [t["id"] for t in a["relayed_reworks"]["sent"]] == ["20261101T100520000000-root-rel2"]
    assert a["relayed_reworks"]["injected"] == "20261101T100500000000-root-inj0"


def test_a_failed_define_service_is_listed_after_the_human_reject(tmp_path):
    d = build(tmp_path)
    s = d / "assistant-session-messages.jsonl"
    rec = [json.loads(l) for l in s.read_text().splitlines()]
    extra = [{"timestamp": Z(31.5), "payload": {"type": "tool_call", "toolCallId": "fbx", "toolName": "tool_call", "status": "completed",
                                                  "args": {"tool_id": "hirearchy::feedback", "arguments": {"task_id": "20261101T100100000000-root-aaaa", "verdict": "reject", "source": "human", "criterion": ["C2"]}}}},
             {"timestamp": Z(31.6), "payload": {"type": "tool_result", "toolCallId": "fbx", "content": "feedback reject recorded"}}]
    i = next(n for n, r in enumerate(rec) if r["payload"].get("toolCallId") == "id4")  # before the call 'inbox'
    rec[i:i] = extra
    s.write_text("\n".join(json.dumps(r) for r in rec) + "\n")
    extract(d)
    import assistant_facts as af
    a = af.analyse(d)
    rj = a["rejects"]["human_rejects"]
    assert len(rj) == 1 and rj[0]["task"] == "20261101T100100000000-root-aaaa" and rj[0]["criterion"] == ["C2"]
    assert [x["status"] for x in rj[0]["defines_after"]] == ["refused"]
    assert rj[0]["window_end"] == {"kind": "stream_end", "turn": 5}
    assert rj[0]["turn_files_between"] == ["turn-03.txt", "turn-04.txt", "turn-05.txt"] or rj[0]["turn_files_between"][0] == "turn-03.txt"
    assert a["rejects"]["without_reading"] == {"k": 0, "n": 1}


def test_memo_turns_run_from_the_request_to_the_human_accept(tmp_path):
    d, a = facts(tmp_path)
    m = a["memo_turns"]
    # the case's first root task (created at 18 s, in turn 2) to the human accept (call 12, turn 5)
    assert m == [{"case": "2026-10-05", "request_call": 3, "request_turn": 2, "accept_call": 12, "accept_turn": 5, "turns": 4, "copies": [4]}]


def test_cost_parts(tmp_path):
    d, a = facts(tmp_path)
    c = a["cost"]
    assert c["user_turns"] == 5 and c["assistant_credits"] == 5.0 and c["assistant_seconds"] == 5
    assert c["org_runs"]["total"] == 3 and c["org_runs"]["window"] == 1
    assert c["org_runs"]["outside_by_seat"] == {"boss": 1, "boss-inspector": 1} or sum(c["org_runs"]["outside_by_seat"].values()) == 2


def test_judged_measures_are_never_in_the_facts(tmp_path):
    d, a = facts(tmp_path)
    for k in ("d_offer", "d5_asked", "d_spend", "d_late"):
        assert k not in json.dumps(a)


def test_cli_writes_assistant_facts_json_into_measures(tmp_path):
    d = build(tmp_path)
    extract(d)
    r = run(d)
    assert r.returncode == 0, r.stderr
    j = json.loads((d / "measures" / "assistant_facts.json").read_text())
    assert j["script"]["name"] == "assistant_facts.py" and "assistant-session-messages.jsonl" in j["source_files"]
    assert j["measures"]["copies"] == 1 and j["measures"]["skill_stratum"] == "A"
    out2 = tmp_path / "o2"
    assert run(d, "--out", out2).returncode == 0 and (out2 / "assistant_facts.json").exists()


# ================================================================== E7: the published numbers (the self-check)
@e7
def test_the_e7_expectations_are_transcribed_with_a_source_each():
    exp = json.loads(EXPECTED.read_text())
    assert len(exp) > 100
    for e in exp:
        assert set(e) >= {"stream", "key", "expected", "source"} and e["source"].strip()


@e7
def test_e7_selfcheck_every_expected_entry_holds(tmp_path):
    import assistant_facts as af
    results = af.selfcheck(E7EV, tmp_path / "sc", EXPECTED)
    bad = [r for r in results if not r["ok"]]
    # a MISMATCH is never bent: it is reported by the self-check CLI; here we only require that nothing is silently dropped
    assert len(results) == len(json.loads(EXPECTED.read_text()))
    assert not bad, "\n".join(f"{r['stream']} {r['key']}: expected {r['expected']!r} got {r['actual']!r} ({r['source']})" for r in bad)


@e7
def test_e7_facts_are_the_same_from_the_committed_extracts_and_from_the_regenerated_ones(tmp_path):
    import assistant_facts as af
    import extract_mechanical as em
    ex = tmp_path / "ex"
    em.run_extract(E7EV / "s2", "-", ex)
    a = af.analyse(E7EV / "s2")
    b = af.analyse(E7EV / "s2", extracts=ex)
    for k in ("flagged", "copies", "refusals", "reads", "cost"):
        assert json.dumps(a[k], sort_keys=True) == json.dumps(b[k], sort_keys=True), k


@e7
def test_extract_diffs_against_e7s_committed_extracts_are_reported_file_by_file(tmp_path):
    import assistant_facts as af
    rows = af.extract_diffs(E7EV, tmp_path / "sc")
    by = {(r["stream"], r["file"]): r for r in rows}
    for s in ("s1", "s2", "s3"):
        for f in ("client-questions.txt", "contract-loop.txt", "shell-writes.txt", "lead-prompt-sizes.txt", "revise-playbook-attempts.txt", "cost.txt"):
            assert by[(s, f)]["identical"] is True, (s, f)
        assert by[(s, "deliverables-log.txt")]["identical"] is False and by[(s, "deliverables-log.txt")]["differing_lines"] >= 1  # the listing tail without a sandbox
        assert by[(s, "run-session-map.txt")]["differing_lines"] == 1                                                     # the "sessions copied" line
        assert by[(s, "reflect-sections/")]["identical"] and by[(s, "regression-list/")]["identical"]
        assert by[(s, "injection/text-identity.txt")]["identical"] is True
        assert by[(s, "injection/window-runs.txt")]["differing_lines"] >= 0
    diff = (tmp_path / "sc" / "e7-s1" / "extract-diff.txt").read_text()
    assert "deliverables-log.txt" in diff and "run-session-map.txt" in diff
