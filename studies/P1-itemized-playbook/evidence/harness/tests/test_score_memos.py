"""Tests of score_memos.py (G0 harness, helper M). Synthetic inputs in tmp_path; E7's committed evidence is read-only."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))

import score_memos as sm  # noqa: E402

MEMO_1012_GOOD = """# Platform team weekly memo, 2026-10-12

Summary: The team approved the RFC, made the postmortem blameless and set a deploy freeze.

## Decisions

- Approve the rate limiter RFC with the token bucket per API key design, behind a feature flag first.
- The postmortem for the Oct 8 outage will be blameless and shared with the whole company.
- Deploy freeze on Oct 22 and Oct 23 for the customer demo.

## Actions

| Owner | Action | Due |
|---|---|---|
| Dev | Write the postmortem for the Oct 8 outage | 2026-10-14 |
| Marta | Send the demo agenda to the customer | 2026-10-16 |
| Priya | Start implementing the rate limiter behind a feature flag | 2026-10-20 |
| Sam | Refresh the staging test data, ready the day before the freeze | 2026-10-21 |
| Lee | Carry the pager during demo week by swapping shifts with Dev | none |
"""

MEMO_1019_GOOD = """# Platform team weekly memo, 2026-10-19

Summary: Demo goes ahead, SSO renewed, meeting moved.

## Decisions

- Go ahead with the customer demo, leaving the rate limiter out of it.
- Renew with the current SSO vendor for twelve months.
- Move the weekly meeting from Monday 10:00 to Monday 14:00, starting 26 October.

## Actions

| Owner | Action | Due |
|---|---|---|
| Marta | Collect demo feedback and circulate it | 2026-10-23 |
| Dev | Remove the deploy freeze in the pipeline config | 2026-10-24 |
| Priya | Present the rate limiter benchmark results at the next meeting | 2026-10-26 |
| Lee | Sign off on the SSO vendor renewal once legal replies | 2026-10-30 |
| Sam | Pair with Jo on the CI pipeline during Jo's first week | none |
"""

MEMO_1005_GOOD = """# Platform team weekly memo, 2026-10-05

Summary: Gateway migration pushed, Renovate adopted.

## Decisions

- Push the API gateway migration to the week of 26 October.
- Adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos.

## Actions

| Owner | Action | Due |
|---|---|---|
| Priya | Draft the RFC for the new per-key rate limiter | 2026-10-09 |
| Dev | Enable Renovate on the three core repos | 2026-10-08 |
| Sam | Look into the flaky CI | 2026-10-09 |
| Marta | Book the on-call training room | 2026-10-14 |
| Lee | Ping the identity vendor about the SSO certificate renewal | none |
"""


def score(text, meeting):
    return sm.score_memo(text, meeting)


def test_perfect_memos_score_full_marks():
    for text, meeting, nd in ((MEMO_1005_GOOD, "2026-10-05", 2), (MEMO_1012_GOOD, "2026-10-12", 3), (MEMO_1019_GOOD, "2026-10-19", 3)):
        r = score(text, meeting)
        assert r["decisions"] == {"k": nd, "n": nd}, meeting
        assert r["actions"] == {"k": 5, "n": 5}, meeting
        assert r["wrong_dates"] == [] and r["extra_rows"] == [], meeting
        assert r["summary_first"] is True and r["decisions_before_actions"] is True, meeting


def test_wrong_due_is_reported_with_owner_due_and_expected():
    text = MEMO_1012_GOOD.replace("| Sam | Refresh the staging test data, ready the day before the freeze | 2026-10-21 |",
                                  "| Sam | Refresh the staging test data, ready the day before the freeze | 2026-10-20 |")
    r = score(text, "2026-10-12")
    assert r["wrong_dates"] == [{"owner": "Sam", "due": "2026-10-20", "expected": "2026-10-21", "action": "A4"}]
    assert r["actions"] == {"k": 5, "n": 5}  # the row is still the key action, only its Due is wrong
    assert r["extra_rows"] == []


def test_none_where_the_key_has_a_date_is_a_wrong_date_and_a_date_where_the_key_says_none_too():
    t1 = MEMO_1005_GOOD.replace("| Sam | Look into the flaky CI | 2026-10-09 |", "| Sam | Look into the flaky CI | none |")
    assert score(t1, "2026-10-05")["wrong_dates"] == [{"owner": "Sam", "due": "none", "expected": "2026-10-09", "action": "A4"}]
    t2 = MEMO_1005_GOOD.replace("report back", "report back").replace("renewal | none |", "renewal | 2026-10-09 |")
    assert score(t2, "2026-10-05")["wrong_dates"] == [{"owner": "Lee", "due": "2026-10-09", "expected": "none", "action": "A5"}]


def test_due_with_a_trailing_remark_is_read_by_its_first_token():
    t = MEMO_1005_GOOD.replace("| Sam | Look into the flaky CI | 2026-10-09 |", "| Sam | Look into the flaky CI | 2026-10-09 (before Friday) |")
    t = t.replace("renewal | none |", "renewal | none (this week, no hard date) |")
    r = score(t, "2026-10-05")
    assert r["wrong_dates"] == []


def test_extra_row_is_a_row_matching_no_key_action_and_does_not_count_as_a_key_action():
    text = MEMO_1019_GOOD.rstrip("\n") + "\n| Marta | Keep the agenda as sent | none |\n"
    r = score(text, "2026-10-19")
    assert r["actions"] == {"k": 5, "n": 5}
    assert r["extra_rows"] == ["Marta | Keep the agenda as sent | none"]
    assert r["wrong_dates"] == []


def test_duplicate_row_for_a_key_action_is_an_extra_row():
    text = MEMO_1012_GOOD.rstrip("\n") + "\n| Dev | Write the postmortem for the Oct 8 outage (again) | 2026-10-14 |\n"
    r = score(text, "2026-10-12")
    assert r["actions"] == {"k": 5, "n": 5}
    assert len(r["extra_rows"]) == 1 and r["extra_rows"][0].startswith("Dev | Write the postmortem")


def test_row_with_the_wrong_owner_does_not_count_and_is_extra():
    text = MEMO_1012_GOOD.replace("| Dev | Write the postmortem", "| Lee | Write the postmortem")
    r = score(text, "2026-10-12")
    assert r["actions"]["k"] == 4
    assert len(r["extra_rows"]) == 1 and r["extra_rows"][0].startswith("Lee | Write the postmortem")


def test_missing_decision_and_missing_action_lower_the_counts():
    text = MEMO_1012_GOOD.replace("- Deploy freeze on Oct 22 and Oct 23 for the customer demo.\n", "")
    text = text.replace("| Lee | Carry the pager during demo week by swapping shifts with Dev | none |\n", "")
    r = score(text, "2026-10-12")
    assert r["decisions"] == {"k": 2, "n": 3}
    assert r["actions"] == {"k": 4, "n": 5}


def test_a_decision_only_in_another_section_does_not_count():
    text = MEMO_1012_GOOD.replace("- Deploy freeze on Oct 22 and Oct 23 for the customer demo.\n", "")
    text += "\n## Open items\n\n- Deploy freeze on Oct 22 and Oct 23.\n"
    assert score(text, "2026-10-12")["decisions"] == {"k": 2, "n": 3}


def test_open_items_bullets_and_other_tables_are_not_action_rows():
    text = MEMO_1012_GOOD + "\n## Open items\n\n- Sam might look at the CI cache.\n\n| Who | What |\n|---|---|\n| Sam | CI cache |\n"
    r = score(text, "2026-10-12")
    assert r["extra_rows"] == []


@pytest.mark.parametrize("text,expected", [
    ("# Title\n\nSummary: one line.\n\n## Decisions\n", True),
    ("Summary: one line.\n\n## Decisions\n", True),
    ("# Title\n## Decisions\n", False),
    ("# Title\n\nPresent: a, b.\n\nSummary: late.\n", False),
    ("# Title\n\nSummary: first line\nand it continues on a second line.\n\n## Decisions\n", False),
    ("# One\n# Two\nSummary: x\n", False),  # at most ONE title heading
    ("\n\n# Title\n\n\nSummary: x\n", True),
    ("Summary x without a colon\n", False),
])
def test_summary_first(text, expected):
    assert sm.summary_first(text) is expected


def test_decisions_before_actions():
    assert sm.decisions_before_actions("## Decisions\n- a\n## Actions\n| Owner | Action | Due |\n") is True
    assert sm.decisions_before_actions("## Actions\n| Owner | Action | Due |\n## Decisions\n- a\n") is False
    assert sm.decisions_before_actions("## Action items\n| Owner | Action | Due |\n## Decisions\n- a\n") is False
    assert sm.decisions_before_actions("## Decisions\n- a\n") is False  # no action section: not "before"


def test_words_equal_wc_w(tmp_path):
    p = tmp_path / "m.md"
    p.write_text(MEMO_1012_GOOD)
    wc = int(subprocess.run(["wc", "-w", str(p)], capture_output=True, text=True).stdout.split()[0])
    assert sm.words(p.read_bytes()) == wc
    assert score(MEMO_1012_GOOD, "2026-10-12")["words"] == wc


def test_bold_label_headings_and_bullet_continuations_are_understood():
    text = ("Summary: x.\n\n**Decisions**\n\n- Push the API gateway migration to the week of\n  26 October.\n- Adopt Renovate, weekly Monday batch.\n\n"
            "**Action items**\n\n| Owner | Action | Due |\n|---|---|---|\n| Dev | Enable Renovate | 2026-10-08 |\n")
    r = score(text, "2026-10-05")
    assert r["decisions"] == {"k": 2, "n": 2}
    assert r["actions"]["k"] == 1
    assert r["decisions_before_actions"] is True


def test_unknown_meeting_is_an_error():
    with pytest.raises(KeyError):
        score(MEMO_1012_GOOD, "2026-11-02")


def test_key_has_the_published_shape():
    assert {m: (len(v["decisions"]), len(v["actions"])) for m, v in sm.KEY.items()} == {
        "2026-10-05": (2, 5), "2026-10-12": (3, 5), "2026-10-19": (3, 5)}
    # D15 accepted Dues (E7 protocol D15)
    due = {m: {a["owner"]: a["due"] for a in v["actions"]} for m, v in sm.KEY.items()}
    assert due["2026-10-05"] == {"Priya": "2026-10-09", "Dev": "2026-10-08", "Marta": "2026-10-14", "Sam": "2026-10-09", "Lee": "none"}
    assert due["2026-10-12"] == {"Priya": "2026-10-20", "Dev": "2026-10-14", "Marta": "2026-10-16", "Sam": "2026-10-21", "Lee": "none"}
    assert due["2026-10-19"] == {"Priya": "2026-10-26", "Dev": "2026-10-24", "Marta": "2026-10-23", "Sam": "none", "Lee": "2026-10-30"}


# ---------------------------------------------------------------------------------------------------------------------------
# stream level: versions, copies, reviews, finals, key check, CLI, self-check
# ---------------------------------------------------------------------------------------------------------------------------
V1_TEXT = MEMO_1012_GOOD.replace("Summary: The team approved the RFC, made the postmortem blameless and set a deploy freeze.\n\n", "") \
    .replace("| Sam | Refresh the staging test data, ready the day before the freeze | 2026-10-21 |",
             "| Sam | Refresh the staging test data, ready the day before the freeze | 2026-10-20 |")
V2_TEXT = MEMO_1012_GOOD


def _msg(path, **h):
    body = h.pop("body", "")
    head = "\n".join(f"{k}: {v}" for k, v in h.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{head}\n---\n{body}")


def make_stream(tmp_path, name="s1", with_final=True):
    s = tmp_path / name
    ver = s / "memos" / "versions"
    ver.mkdir(parents=True)
    (ver / "memo-2026-10-12.v1.aaaaaaa.md").write_text(V1_TEXT)
    (ver / "memo-2026-10-12.v2.bbbbbbb.md").write_text(V2_TEXT)
    m1, m2 = md5_of(V1_TEXT), md5_of(V2_TEXT)
    (ver / "INDEX.txt").write_text(
        f"lead/writer/work/memo-2026-10-12.md v1 aaaaaaa 2026-10-25T08:00:00Z md5 {m1}\n"
        f"lead/writer/work/memo-2026-10-12.md v2 bbbbbbb 2026-10-25T08:10:00Z md5 {m2}\n"
        f"lead/writer/work/memo-2026-10-12.md working tree md5 {m2} (committed head: {m2})\n")
    if with_final:
        (s / "memos" / "memo-2026-10-12.md").write_text(V2_TEXT)
    (s / "deliverables-log.txt").write_text(
        "# deliverables log (protocol 7.2, D6); facts only\n\n"
        "[2026-10-25T08:11:00.000Z] call #5 turn 3 execute_bash\nCOMMAND: cp a b\n"
        "source file(s): ['lead/writer/work/memo-2026-10-12.md -> org-git commit at that time: bbbbbbb 2026-10-25T08:10:00Z']\n"
        "result: Output:\nidentical\n\n"
        f"final listing of deliverables/:\n  memo-2026-10-12.md size 10 mtime 08:11:00 local md5 {m2}\n")
    # the agents
    (s / "org-files").mkdir()
    (s / "org-files" / "lead-reviewer-AGENT.md").write_text("---\nrole: Independent Reviewer\n---\n")
    (s / "org-files" / "lead-writer-AGENT.md").write_text("---\nrole: Writer\n---\n")
    _msg(s / "msgs" / "sent" / "20261025T075900000000-root-aaaa.md", id="20261025T075900000000-root-aaaa", **{"from": "root"}, to="lead",
         type="task", title="Memo for the 12 October 2026 meeting", created="'2026-10-25T07:59:00+00:00'", service="weekly-meeting-memo")
    rv = s / "msgs"
    # review tasks to the reviewer (lead -> lead/reviewer)
    def task(i, created, title, body="Check lead/writer/work/memo-2026-10-12.md"):
        _msg(rv / "lead-reviewer-read" / f"{i}.md", id=i, **{"from": "lead"}, to="lead/reviewer", type="task", title=title,
             created=f"'{created}'", body=body)
    task("20261025T075950000000-lead-t0t0", "2026-10-25T07:59:50+00:00", "Review memo 2026-10-12")  # 10 s before v1's commit
    task("20261025T080030000000-lead-t1t1", "2026-10-25T08:00:30+00:00", "Review memo 2026-10-12")
    task("20261025T081020000000-lead-t2t2", "2026-10-25T08:10:20+00:00", "Re-check memo-2026-10-12.md after answers")
    task("20261025T082000000000-lead-t3t3", "2026-10-25T08:20:00+00:00", "Misc check", body="unrelated to any memo")

    def result(i, reply_to, created, status, body):
        _msg(rv / "lead-reviewer-sent" / f"{i}.md", id=i, **{"from": "lead/reviewer"}, to="lead", type="result", title="Review",
             created=f"'{created}'", reply_to=reply_to, status=status, body=body)
    result("20261025T080100000000-lead.reviewer-r1r1", "20261025T080030000000-lead-t1t1", "2026-10-25T08:01:00+00:00", "blocked",
           "## Summary\ncriteria met: 6 of 7 (C6 ambiguous). Verdict: not pass until C6 is resolved.\n")
    result("20261025T080500000000-lead.reviewer-r1r2", "20261025T080030000000-lead-t1t1", "2026-10-25T08:05:00+00:00", "done",
           "## Summary\ncriteria met: 7 of 7. Verdict: pass.\n")
    result("20261025T081100000000-lead.reviewer-r2r2", "20261025T081020000000-lead-t2t2", "2026-10-25T08:11:00+00:00", "done",
           "## Summary\nCriteria met: 7 of 7. Verdict: PASS. Ambiguous: nothing.\n")
    result("20261025T080000000001-lead.reviewer-r0r0", "20261025T075950000000-lead-t0t0", "2026-10-25T08:00:00+00:00", "done",
           "## Summary\ncriteria met: 5 of 7. Verdict: FAIL.\n")
    return s


def md5_of(text):
    return hashlib.md5(text.encode()).hexdigest()


def test_load_versions_reads_index_and_files(tmp_path):
    s = make_stream(tmp_path)
    vs = sm.load_versions(s)
    assert [(v["memo"], v["version"], v["sha"], v["commit_time"]) for v in vs] == [
        ("2026-10-12", 1, "aaaaaaa", "2026-10-25T08:00:00Z"), ("2026-10-12", 2, "bbbbbbb", "2026-10-25T08:10:00Z")]
    assert vs[0]["md5"] == md5_of(V1_TEXT) and vs[0]["file"] == "memos/versions/memo-2026-10-12.v1.aaaaaaa.md"


def test_load_versions_without_an_index_uses_the_file_names_and_md5(tmp_path):
    s = make_stream(tmp_path)
    (s / "memos" / "versions" / "INDEX.txt").unlink()
    vs = sm.load_versions(s)
    assert [(v["version"], v["sha"], v["commit_time"]) for v in vs] == [(1, "aaaaaaa", None), (2, "bbbbbbb", None)]


def test_copies_are_read_from_the_log_and_mark_versions_delivered(tmp_path):
    s = make_stream(tmp_path)
    cps = sm.load_copies(s)
    assert cps == [{"call": 5, "turn": 3, "time": "2026-10-25T08:11:00.000Z", "tool": "execute_bash", "memo": "2026-10-12",
                    "commit": "bbbbbbb", "commit_time": "2026-10-25T08:10:00Z"}]
    vs = sm.mark_copied(sm.load_versions(s), cps, sm.load_log_md5s(s), sm.final_md5s(s))
    assert [v["copied"] for v in vs] == [False, True]
    assert vs[1]["copies"][0]["call"] == 5 and vs[1]["copied_by"] == ["log-commit", "log-md5", "final-md5"]


def test_a_version_equal_to_a_final_file_is_copied_even_without_a_log_entry(tmp_path):
    s = make_stream(tmp_path)
    (s / "deliverables-log.txt").write_text("# deliverables log\n")
    vs = sm.mark_copied(sm.load_versions(s), sm.load_copies(s), sm.load_log_md5s(s), sm.final_md5s(s))
    assert [v["copied"] for v in vs] == [False, True]
    assert vs[1]["copied_by"] == ["final-md5"]


def test_roles_reviewer_by_charter_then_by_results(tmp_path):
    s = make_stream(tmp_path)
    roles = sm.find_roles(s)
    assert roles["owner"] == "lead" and roles["reviewer"] == "lead/reviewer" and roles["detected_by"] == "charter"
    (s / "org-files" / "lead-reviewer-AGENT.md").write_text("---\nrole: Quality gate\n---\n")
    roles = sm.find_roles(s)
    assert roles["reviewer"] == "lead/reviewer" and roles["detected_by"] == "results"


def test_review_task_maps_to_the_version_by_the_window_and_first_result_wins(tmp_path):
    s = make_stream(tmp_path)
    vs = sm.load_versions(s)
    rv = sm.map_reviews(s, vs, sm.find_roles(s))
    v1, v2 = rv["by_version"]["2026-10-12", 1], rv["by_version"]["2026-10-12", 2]
    assert v1["task"].endswith("t1t1") and v1["result"].endswith("r1r1")  # not r1r2: the FIRST result counts
    assert (v1["met"], v1["of"], v1["all_met"], v1["status"], v1["verdict"]) == (6, 7, False, "blocked", "NOT PASS")
    assert v2["task"].endswith("t2t2") and (v2["met"], v2["of"], v2["all_met"], v2["verdict"]) == (7, 7, True, "PASS")
    assert [t["task"] for t in rv["unmapped"]] == ["20261025T075950000000-lead-t0t0", "20261025T082000000000-lead-t3t3"]
    t0 = rv["unmapped"][0]
    assert t0["memo"] == "2026-10-12" and t0["candidate_version"] == 1 and t0["seconds_before_candidate_commit"] == 10
    assert (t0["first_result_met"], t0["first_result_of"], t0["first_result_verdict"]) == (5, 7, "FAIL")
    t3 = [t for t in rv["unmapped"] if t["task"].endswith("t3t3")]
    assert t3 and t3[0]["memo"] is None


def test_review_task_after_the_last_commit_belongs_to_the_last_version(tmp_path):
    s = make_stream(tmp_path)
    rv = sm.map_reviews(s, sm.load_versions(s), sm.find_roles(s))
    assert rv["by_version"]["2026-10-12", 2]["task_created"] == "2026-10-25T08:10:20Z"


def write_git_log(s, commits):
    """org-git-log.txt (``git log --stat --date=iso``, newest first) from [(short sha, 'YYYY-MM-DD HH:MM:SS', [paths])], oldest first."""
    out = []
    for short, when, paths in reversed(commits):
        out += [f"commit {short.ljust(40, '0')}", "Author: hirearchy <hirearchy@localhost>", f"Date:   {when} +0000", "", "    lead: run ok", ""]
        out += [f" {p} | 1 +" for p in paths] + [f" {len(paths)} files changed", ""]
    (s / "org-git-log.txt").write_text("\n".join(out) + "\n")


def test_a_review_task_reviews_the_version_in_the_first_commit_that_holds_its_sent_copy(tmp_path):
    """Protocol 12 A3's reading of D21 (manager-decision-selfcheck.md item 4): the version a review task reviews is the work file at the first
    org-git commit that holds the task's sent copy (the commit that closes the run which sent it; design 0a.2's at_result rule for a message).
    E7 s2's 1414 was sent 10 s before that commit, which also committed the version: it reviews that version."""
    s = make_stream(tmp_path)
    write_git_log(s, [("aaaaaaa", "2026-10-25 08:00:00", ["lead/sent/20261025T075950000000-lead-t0t0.md", "lead/writer/work/memo-2026-10-12.md"]),
                      ("bbbbbbb", "2026-10-25 08:10:00", ["lead/writer/work/memo-2026-10-12.md"])])
    rv = sm.map_reviews(s, sm.load_versions(s), sm.find_roles(s))
    v1 = rv["by_version"]["2026-10-12", 1]
    assert v1["task"].endswith("t0t0") and v1["mapped_by"] == "commit" and v1["sent_before_commit_s"] == 10
    assert (v1["met"], v1["of"], v1["verdict"]) == (5, 7, "FAIL")  # its first result
    assert v1["tasks"][:2] == ["20261025T075950000000-lead-t0t0", "20261025T080030000000-lead-t1t1"]
    v2 = rv["by_version"]["2026-10-12", 2]
    assert v2["task"].endswith("t2t2") and v2["mapped_by"] == "time" and v2["sent_before_commit_s"] == 0  # not in the log: the time window
    assert [t["task"] for t in rv["unmapped"]] == ["20261025T082000000000-lead-t3t3"]
    literal = sm.map_reviews(s, sm.load_versions(s), sm.find_roles(s), rule="time")  # D21's literal timing, reported beside it
    assert literal["by_version"]["2026-10-12", 1]["task"].endswith("t1t1")
    assert [t["task"] for t in literal["unmapped"]] == ["20261025T075950000000-lead-t0t0", "20261025T082000000000-lead-t3t3"]


def test_parse_review_result_variants():
    assert sm.parse_review("Criteria met: 5 of 6. Verdict: FAIL") == {"met": 5, "of": 6, "all_met": False, "verdict": "FAIL", "ambiguous_token": False}
    assert sm.parse_review("criteria met 7 of 7. PASS, no required changes")["of"] == 7
    r = sm.parse_review("criteria met: 7 of 9 (C1-C7, C9, R1; C9 and R1 fail)")
    assert (r["met"], r["of"], r["verdict"]) == (7, 9, None)
    assert sm.parse_review("Ambiguous (not decided): Lee")["ambiguous_token"] is True
    assert sm.parse_review("no counts here") == {"met": None, "of": None, "all_met": None, "verdict": None, "ambiguous_token": False}


def test_score_stream_has_the_whole_picture(tmp_path):
    s = make_stream(tmp_path)
    out = sm.score_stream(s, answer_key=None)
    assert out["label"] == "s1"
    v1, v2 = out["versions"]
    assert v1["wrong_dates"] == [{"owner": "Sam", "due": "2026-10-20", "expected": "2026-10-21", "action": "A4"}]
    assert (v1["n_wrong_dates"], v1["wrong_date_text"], v1["n_extra_rows"]) == (1, ["Sam 2026-10-20"], 0)
    assert (v2["n_wrong_dates"], v2["wrong_date_text"], v2["n_extra_rows"]) == (0, [], 0)
    assert v1["summary_first"] is False and v2["summary_first"] is True
    assert (v1["copied"], v2["copied"]) == (False, True)
    assert v1["review"]["met"] == 6 and v2["review"]["met"] == 7
    assert out["finals"][0]["memo"] == "2026-10-12" and out["finals"][0]["md5"] == md5_of(V2_TEXT)
    assert out["finals"][0]["is_version"] == {"version": 2, "sha": "bbbbbbb"}
    t = out["final_totals"]
    assert t["decisions"] == {"k": 3, "n": 8} and t["actions"] == {"k": 5, "n": 15}
    assert t["wrong_dates"] == 0 and t["extra_rows"] == 0 and t["summary"] == {"k": 1, "n": 3} and t["memos"] == 1
    assert out["delivered"] == {"k": 1, "n": 2}
    assert out["script"]["name"] == "score_memos.py" and re_md5(out["script"]["md5"])
    assert "msgs/lead-reviewer-sent/20261025T080100000000-lead.reviewer-r1r1.md" in out["source_files"]
    assert out["source_files"] == sorted(set(out["source_files"]))


def re_md5(s):
    return len(s) == 32 and all(c in "0123456789abcdef" for c in s)


KEY_TEXT = """# Answer key (private)
## 2026-10-12
Decisions
- D1 a
- D2 b
- D3 c
Actions
- A1 (explicit) Dev | write postmortem | 2026-10-14
- A2 (explicit) Marta | send agenda | 2026-10-16
- A3 (explicit) Priya | start | 2026-10-20
- A4 (IMPLICIT) Sam | refresh | 2026-10-21
- A5 (IMPLICIT) Lee | swap | none (demo week)
"""


def test_key_check_compares_counts_owners_and_dues_without_copying_the_key(tmp_path):
    k = tmp_path / "answer-key.md"
    k.write_text(KEY_TEXT)
    chk = sm.key_check(k)
    assert chk["md5"] == md5_of(KEY_TEXT) and "text" not in json.dumps(chk)
    m = chk["meetings"]["2026-10-12"]
    assert m == {"decisions": 3, "actions": 5, "owners_match": True, "dues_match": True}
    assert chk["meetings"]["2026-10-05"] is None and chk["ok"] is False  # the other two meetings are absent from this tiny key
    assert sm.key_check(tmp_path / "missing.md") == {"status": "missing"}


def test_key_check_flags_a_changed_due(tmp_path):
    k = tmp_path / "answer-key.md"
    k.write_text(KEY_TEXT.replace("| 2026-10-21", "| 2026-10-22"))
    assert sm.key_check(k)["meetings"]["2026-10-12"]["dues_match"] is False


def test_cli_writes_json_and_txt(tmp_path):
    s = make_stream(tmp_path)
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "score_memos.py"), str(s), "--out", str(out), "--answer-key", str(tmp_path / "none.md")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = json.loads((out / "score_memos.json").read_text())
    assert d["final_totals"]["memos"] == 1 and (out / "score_memos.txt").read_text().startswith("score_memos")
    assert (out / "score_memos.json").read_text() == json.dumps(d, sort_keys=True, indent=2) + "\n"


def test_resolve_path_and_compare_ops():
    d = {"a": {"b": [{"sha": "x1", "n": 3}, {"sha": "x2", "n": {"k": 1}}]}, "c": None}
    assert sm.resolve(d, "a.b[sha=x2].n.k") == (True, 1)
    assert sm.resolve(d, "a.b[sha=zz].n") == (False, None)
    assert sm.resolve(d, "c") == (True, None)
    assert sm.resolve(d, "a.q") == (False, None)
    assert sm.compare("abc123", "abc", "startswith") and sm.compare("x-lead-d20d", "-lead-d20d", "endswith") and sm.compare(3, 3, "eq")
    assert not sm.compare(3, 4, "eq") and not sm.compare(None, "a", "startswith")


def test_selfcheck_runs_the_expected_file_and_reports_mismatches(tmp_path):
    ev = tmp_path / "E7EV"
    for n in ("s1", "s2", "s3"):
        make_stream(ev, n)
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps([
        {"module": "score_memos", "stream": "s1", "key": "final_totals.actions.k", "expected": 5, "source": "test"},
        {"module": "score_memos", "stream": "s2", "key": "versions[sha=aaaaaaa].wrong_dates", "expected": [], "source": "test"},
        {"module": "ambiguity_recall", "stream": "s1", "key": "x", "expected": 1, "source": "other module: skipped"},
    ]))
    out = tmp_path / "sc"
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "score_memos.py"), "--selfcheck", str(ev), "--out", str(out), "--expected", str(exp),
                        "--answer-key", str(tmp_path / "none.md")], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    assert lines[-1] == "selfcheck score_memos: 1 of 2 OK" and r.returncode == 1, r.stdout
    assert any(l.startswith("MISMATCH s2 versions[sha=aaaaaaa].wrong_dates") for l in lines)
    assert any(l.startswith("OK s1 final_totals.actions.k") for l in lines)
    for n in ("s1", "s2", "s3"):
        assert (out / f"e7-{n}" / "score_memos.json").exists()
