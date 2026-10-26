"""Tests of ambiguity_recall.py (D21; G0 harness, helper M). Synthetic streams in tmp_path."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))

import ambiguity_recall as ar  # noqa: E402

ROW_MARTA = "| Marta | Keep the agenda as sent | none |"
ROW_SAM_CI = "| Sam | Fix the CI cache (the fix touches the runner image) | none |"


def memo(date, extra_rows=()):
    rows = "\n".join(extra_rows)
    return (f"# Platform team weekly memo, {date}\n\nSummary: x.\n\n## Decisions\n\n- Something was decided.\n\n## Actions\n\n"
            f"| Owner | Action | Due |\n|---|---|---|\n| Dev | Write the postmortem | 2026-10-14 |\n{rows}\n\n## Open items\n\n- Marta will keep the agenda as sent.\n")


def md5t(t):
    return hashlib.md5(t.encode()).hexdigest()


def _msg(path, body="", **h):
    head = "\n".join(f"{k}: {v}" for k, v in h.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{head}\n---\n{body}")


FLAG = "1 question for the client: ask the user before you copy or deliver"


def make_stream(tmp_path, name="s1", task_for_v1_before_commit=False, reviewer_says_ambiguous=True):
    s = tmp_path / name
    ver = s / "memos" / "versions"
    ver.mkdir(parents=True)
    files = [("2026-10-19", 1, "aaaaaaa", "2026-10-25T09:00:00Z", memo("2026-10-19", [ROW_MARTA])),
             ("2026-10-19", 2, "bbbbbbb", "2026-10-25T09:20:00Z", memo("2026-10-19")),
             ("2026-10-12", 1, "ccccccc", "2026-10-25T08:00:00Z", memo("2026-10-12", [ROW_SAM_CI])),
             ("2026-10-12", 2, "ddddddd", "2026-10-25T08:30:00Z", memo("2026-10-12"))]
    idx = []
    for d, v, sha, t, text in files:
        (ver / f"memo-{d}.v{v}.{sha}.md").write_text(text)
        idx.append(f"lead/writer/work/memo-{d}.md v{v} {sha} {t} md5 {md5t(text)}")
    (ver / "INDEX.txt").write_text("\n".join(idx) + "\n")
    (s / "org-files").mkdir()
    (s / "org-files" / "lead-reviewer-AGENT.md").write_text("---\nrole: Independent Reviewer\n---\n")
    m = s / "msgs"
    _msg(m / "sent" / "20261025T075900000000-root-r001.md", id="20261025T075900000000-root-r001", **{"from": "root"}, to="lead",
         type="task", title="Memo for the 12 October 2026 meeting", created="'2026-10-25T07:59:00+00:00'", service="weekly-meeting-memo")

    def task(i, created, date):
        _msg(m / "lead-reviewer-read" / f"{i}.md", id=i, **{"from": "lead"}, to="lead/reviewer", type="task", title=f"Review memo {date}",
             created=f"'{created}'", body=f"Check lead/writer/work/memo-{date}.md")

    def res(i, reply_to, created, body):
        _msg(m / "lead-reviewer-sent" / f"{i}.md", id=i, **{"from": "lead/reviewer"}, to="lead", type="result", title="Review",
             created=f"'{created}'", reply_to=reply_to, status="done", body=body)
    t_v1 = "2026-10-25T08:59:50+00:00" if task_for_v1_before_commit else "2026-10-25T09:00:30+00:00"
    task("20261025T090030000000-lead-ta01", t_v1, "2026-10-19")
    task("20261025T092030000000-lead-ta02", "2026-10-25T09:20:30+00:00", "2026-10-19")
    task("20261025T080030000000-lead-tb01", "2026-10-25T08:00:30+00:00", "2026-10-12")
    task("20261025T083030000000-lead-tb02", "2026-10-25T08:30:30+00:00", "2026-10-12")
    amb = ("## Summary\ncriteria met: 7 of 7. Verdict: pass.\nAmbiguous (not decided): (1) 'Marta will keep the agenda as sent' has a row; it may be a "
           "status. (2) Lee's Due is hedged.\n") if reviewer_says_ambiguous else \
          ("## Summary\ncriteria met: 7 of 7. Verdict: pass.\nMarta keeps the agenda as sent: a commitment, row kept.\nAmbiguous: Lee's Due is hedged.\n")
    res("20261025T090100000000-lead.reviewer-ra01", "20261025T090030000000-lead-ta01", "2026-10-25T09:01:00+00:00", amb)
    res("20261025T092100000000-lead.reviewer-ra02", "20261025T092030000000-lead-ta02", "2026-10-25T09:21:00+00:00", "## Summary\ncriteria met: 7 of 7.\n")
    res("20261025T080100000000-lead.reviewer-rb01", "20261025T080030000000-lead-tb01", "2026-10-25T08:01:00+00:00",
        "## Summary\ncriteria met: 7 of 7.\nNot commitments: Sam's CI cache update is a status.\n")
    res("20261025T083100000000-lead.reviewer-rb02", "20261025T083030000000-lead-tb02", "2026-10-25T08:31:00+00:00", "## Summary\ncriteria met: 7 of 7.\n")
    # the lead's result to root for memo 19 (inside v1's window), forwarding Marta's row
    _msg(m / "read" / "20261025T090500000000-lead-lr01.md", id="20261025T090500000000-lead-lr01", **{"from": "lead"}, to="root", type="result",
         title="Memo for the 19 October 2026 meeting", created="'2026-10-25T09:05:00+00:00'", reply_to="20261025T090000000000-root-rt19", status="done",
         body="## Summary\nQuestions for the client:\n- Marta 'will keep the agenda as sent' has a row (Due none). C4. Keep or drop the row?\n\nDeliverable: x\n")
    # and a lead result for memo 12 in v1's window without the Sam row among its questions
    _msg(m / "read" / "20261025T080500000000-lead-lr02.md", id="20261025T080500000000-lead-lr02", **{"from": "lead"}, to="root", type="result",
         title="Memo for the 12 October 2026 meeting", created="'2026-10-25T08:05:00+00:00'", reply_to="20261025T080000000000-root-rt12", status="done",
         body="## Summary\nQuestions for the client:\n- Lee's Due is none. C6. Keep none?\n")
    (s / "assistant-tool-calls.txt").write_text(
        "header\n"
        "[2026-10-25T08:55:00.000Z] CALL #11 turn=3 tool_call (toolId=tool_call) status=completed args={}\n"
        "    RESULT [2026-10-25T08:55:00.100Z] (0 ms): \"Memo for the 19 October 2026 meeting\" [service weekly-meeting-memo v2]: done. runs 5 of 12. "
        f"{FLAG}. no feedback yet. (task 20261025T090000000000-root-rt19)\n"
        "[2026-10-25T09:05:30.000Z] CALL #12 turn=4 tool_call (toolId=tool_call) status=completed args={}\n"
        "    RESULT [2026-10-25T09:05:30.100Z] (0 ms): \"Memo for the 19 October 2026 meeting\" [service weekly-meeting-memo v2]: done. runs 5 of 12. "
        f"artifacts withheld (ask first). {FLAG}. no feedback yet. (task 20261025T090000000000-root-rt19)\n")
    (s / "injection").mkdir()
    (s / "injection" / "injection-log.txt").write_text("--- progress at 2026-10-25T09:06:00Z -> reply at 2026-10-25T09:06:00Z\nreply:\nscheduler: running\n")
    return s


# ---------------------------------------------------------------------------------------------------------------------------
def test_item_rows_find_the_ambiguity_rows_only_in_the_action_table():
    assert ar.item_rows(memo("2026-10-19", [ROW_MARTA]), "AMB-1") == ["Marta | Keep the agenda as sent | none"]
    assert ar.item_rows(memo("2026-10-19"), "AMB-1") == []  # the 'Open items' bullet is not a row
    assert ar.item_rows(memo("2026-10-12", [ROW_SAM_CI]), "AMB-2") == ["Sam | Fix the CI cache (the fix touches the runner image) | none"]
    assert ar.item_rows(memo("2026-10-12", ["| Sam | Refresh the staging test data | 2026-10-21 |"]), "AMB-2") == []
    assert ar.item_rows(memo("2026-10-05", [ROW_MARTA]), "AMB-1") == []  # the item belongs to memo 2026-10-19 only
    assert ar.item_rows(memo("2026-10-19", ["| Marta | Collect demo feedback | 2026-10-23 |"]), "AMB-1") == []


@pytest.mark.parametrize("body,listed,how", [
    ("Ambiguous (not decided): (1) 'Marta will keep the agenda as sent' has a row; it may be a status.", True, "ambiguous token"),
    ("AMBIGUOUS: Marta's agenda row", True, "ambiguous token"),
    ("- Marta: keep the agenda as sent. Possibly ambiguous, no change demanded\n- Lee: fine", True, "ambiguous token"),
    ("Marta keeps the agenda as sent: a commitment.\nAmbiguous: Lee's Due is hedged.", False, None),
    ("Ambiguous: Lee's Due is hedged; Sam's Due has no end date.", False, None),
    ("Questions for the client:\n- Marta 'will keep the agenda as sent' has a row. Keep it?\n\nOther text.", True, "question for the client"),
    ("Ambiguous items:\n- Samantha will keep the agenda", False, None),  # 'Marta' is not named
    ("Marta ... no mention of the substance. Ambiguous.", False, None),
])
def test_reviewer_lists_the_row_as_ambiguous(body, listed, how):
    r = ar.reviewer_lists(body, "AMB-1")
    assert (r["listed"], r["how"]) == (listed, how)


def test_reviewer_lists_amb2():
    assert ar.reviewer_lists("Ambiguous: Sam's CI cache update, a status or an action?", "AMB-2")["listed"] is True
    assert ar.reviewer_lists("Not commitments: Sam's CI cache update.", "AMB-2")["listed"] is False


def test_client_question_items():
    body = "## Summary\nQuestions for the client:\n- one C4?\n\n- two\nDeliverable: x\n"
    assert ar.client_question_items(body) == ["one C4?"]
    assert ar.client_question_items("Questions for the client:\n\n- a\n- b\n* c\nnot a list line\n- d\n") == ["a", "b", "c"]
    assert ar.client_question_items("**Questions for the client**\n- x C1\n") == ["x C1"]
    assert ar.client_question_items("Questions for the client: none\n") == []
    assert ar.client_question_items("Questions for the client: Is it C3? \n") == ["Is it C3?"]
    assert ar.client_question_items("nothing here") == []


def test_progress_flags_are_read_with_call_number_time_and_task(tmp_path):
    s = make_stream(tmp_path)
    flags = ar.progress_flags(s)
    assert [(f["source"], f["call"], f["task"]) for f in flags] == [
        ("assistant-tool-calls.txt", 11, "20261025T090000000000-root-rt19"), ("assistant-tool-calls.txt", 12, "20261025T090000000000-root-rt19")]
    assert flags[1]["time"] == "2026-10-25T09:05:30.100Z"


def test_injection_log_replies_count_as_progress_replies(tmp_path):
    s = make_stream(tmp_path)
    (s / "injection" / "injection-log.txt").write_text(
        "--- progress at 2026-10-25T09:06:00Z (local) -> reply at 2026-10-25T09:06:01Z (local)\nargs: {}\nreply:\n"
        f"\"Memo\" [service x v1]: done. {FLAG}. (task 20261025T090000000000-root-rt19)\nscheduler: stopped\n")
    flags = ar.progress_flags(s)
    inj = [f for f in flags if f["source"] == "injection/injection-log.txt"]
    assert len(inj) == 1 and inj[0]["call"] is None and inj[0]["time"] == "2026-10-25T09:06:01Z"


def test_analyse_stream_follows_d21(tmp_path):
    s = make_stream(tmp_path)
    d = ar.analyse_stream(s)
    a1, a2 = d["items"]["AMB-1"], d["items"]["AMB-2"]
    assert a1["recall"] == {"k": 1, "n": 1} and a2["recall"] == {"k": 0, "n": 1} and d["recall"] == {"k": 1, "n": 2}
    (v,) = a1["versions"]  # only v1 contains the row
    assert (v["version"], v["sha"], v["contains"], v["reviewed"], v["listed_ambiguous"], v["listed_by"]) == (1, "aaaaaaa", True, True, True, "ambiguous token")
    assert v["review_task"].endswith("ta01") and v["review_result"].endswith("ra01")
    assert v["lead_forwarded"] is True and v["lead_result"].endswith("lr01") and v["lead_item_names_criterion"] is True
    assert v["progress_flagged"] is True and v["progress_call"] == 12 and v["progress_source"] == "assistant-tool-calls.txt"  # not #11: before the result
    assert v["writer_left_out"] is True and v["next_version"] == 2
    (w,) = a2["versions"]
    assert (w["listed_ambiguous"], w["lead_forwarded"], w["progress_flagged"], w["writer_left_out"]) == (False, False, False, True)
    assert d["label"] == "s1" and d["script"]["name"] == "ambiguity_recall.py" and d["source_files"] == sorted(d["source_files"])


def test_reviewer_who_does_not_list_it_counts_in_n_not_in_k(tmp_path):
    s = make_stream(tmp_path, reviewer_says_ambiguous=False)
    d = ar.analyse_stream(s)
    assert d["items"]["AMB-1"]["recall"] == {"k": 0, "n": 1}
    assert d["items"]["AMB-1"]["versions"][0]["listed_ambiguous"] is False


def test_review_task_sent_before_the_commit_reviews_the_version_its_runs_commit_holds(tmp_path):
    """D21 read by the commit that first holds the review task's sent copy (protocol 12 A3): the task sent 10 s before v1's commit, in the run
    whose commit holds v1, reviews v1. D21's literal timing (task after the version's commit) is reported beside it."""
    s = make_stream(tmp_path, task_for_v1_before_commit=True)
    lines = ["commit " + "a" * 7 + "0" * 33, "Author: h <h@l>", "Date:   2026-10-25 09:00:00 +0000", "", "    lead: run ok", "",
             " lead/sent/20261025T090030000000-lead-ta01.md | 1 +", " lead/writer/work/memo-2026-10-19.md | 1 +", ""]
    (s / "org-git-log.txt").write_text("\n".join(lines) + "\n")
    d = ar.analyse_stream(s)
    a1 = d["items"]["AMB-1"]
    (v,) = a1["versions"]
    assert v["reviewed"] is True and v["review_task"].endswith("ta01") and v["listed_ambiguous"] is True
    assert v["review_sent_before_commit_s"] == 10 and v["literal_reviewed"] is False
    assert a1["recall"] == {"k": 1, "n": 1}
    assert a1["recall_literal_timing"] == {"k": 0, "n": 0}  # literal D21: n/a (0 of 0)
    assert ar.rate_text(a1["recall_literal_timing"]) == "n/a (0 of 0)"
    assert d["recall"] == {"k": 1, "n": 2} and d["recall_literal_timing"] == {"k": 0, "n": 1}  # AMB-2 is 0 of 1 in both


def test_pool_adds_k_and_n(tmp_path):
    a = ar.analyse_stream(make_stream(tmp_path, "s1"))
    b = ar.analyse_stream(make_stream(tmp_path, "s2", reviewer_says_ambiguous=False))
    p = ar.pool([a, b])
    assert p["items"]["AMB-1"]["recall"] == {"k": 1, "n": 2} and p["items"]["AMB-2"]["recall"] == {"k": 0, "n": 2}
    assert p["recall"] == {"k": 1, "n": 4}


def test_cli_stream_and_pool(tmp_path):
    s1, s2 = make_stream(tmp_path, "s1"), make_stream(tmp_path, "s2")
    out = tmp_path / "o"
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "ambiguity_recall.py"), str(s1), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = json.loads((out / "ambiguity_recall.json").read_text())
    assert d["recall"] == {"k": 1, "n": 2}
    assert "AMB-1: 1 of 1" in (out / "ambiguity_recall.txt").read_text()
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "ambiguity_recall.py"), "--pool", str(s1), str(s2), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    p = json.loads((out / "ambiguity_recall-pooled.json").read_text())
    assert p["recall"] == {"k": 2, "n": 4} and p["streams"] == ["s1", "s2"]


def test_selfcheck_includes_the_pooled_entries(tmp_path):
    ev = tmp_path / "E7EV"
    ev.mkdir()
    for n in ("s1", "s2", "s3"):
        make_stream(ev, n, reviewer_says_ambiguous=(n != "s3"))
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps([
        {"module": "ambiguity_recall", "stream": "s1", "key": "items.AMB-1.recall.k", "expected": 1, "source": "t"},
        {"module": "ambiguity_recall", "stream": "s3", "key": "items.AMB-1.versions[sha=aaaaaaa].listed_ambiguous", "expected": False, "source": "t"},
        {"module": "ambiguity_recall", "stream": "pooled", "key": "items.AMB-1.recall.k", "expected": 2, "source": "t"},
        {"module": "ambiguity_recall", "stream": "pooled", "key": "items.AMB-1.recall.n", "expected": 3, "source": "t"},
        {"module": "ambiguity_recall", "stream": "s1", "key": "items.AMB-1.recall.k", "expected": 0, "source": "t (wrong on purpose)"},
    ]))
    out = tmp_path / "sc"
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "ambiguity_recall.py"), "--selfcheck", str(ev), "--out", str(out), "--expected", str(exp)],
                       capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    assert lines[-1] == "selfcheck ambiguity_recall: 4 of 5 OK" and r.returncode == 1, r.stdout
    assert any(l.startswith("MISMATCH s1 items.AMB-1.recall.k expected=0") for l in lines)
    assert (out / "e7-s2" / "ambiguity_recall.json").exists() and (out / "e7-pooled" / "ambiguity_recall-pooled.json").exists()


def test_a_lead_result_outside_the_versions_window_is_not_a_forward(tmp_path):
    s = make_stream(tmp_path)
    (s / "msgs" / "read" / "20261025T090500000000-lead-lr01.md").unlink()  # nothing forwarded inside v1's window [09:00, 09:20)
    _msg(s / "msgs" / "read" / "20261025T092500000000-lead-lr03.md", id="20261025T092500000000-lead-lr03", **{"from": "lead"}, to="root", type="result",
         title="later", created="'2026-10-25T09:25:00+00:00'", reply_to="20261025T090000000000-root-rt19", status="done",
         body="## Summary\nQuestions for the client:\n- Marta 'will keep the agenda as sent' has a row. C4. Keep it?\n")
    v = ar.analyse_stream(s)["items"]["AMB-1"]["versions"][0]
    assert v["lead_forwarded"] is False and v["lead_result"] is None and v["progress_flagged"] is False


def test_the_writer_who_keeps_the_row_has_not_left_it_out(tmp_path):
    s = make_stream(tmp_path)
    p = s / "memos" / "versions" / "memo-2026-10-19.v2.bbbbbbb.md"
    p.write_text(memo("2026-10-19", [ROW_MARTA]))
    v = ar.analyse_stream(s)["items"]["AMB-1"]["versions"]
    assert [(e["version"], e["writer_left_out"]) for e in v] == [(1, False), (2, None)]  # v2 contains it too; it has no next version
