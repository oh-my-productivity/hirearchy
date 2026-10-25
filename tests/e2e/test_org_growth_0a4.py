# mypy: ignore-errors
"""Phase 0a.4, end to end: E6's recorded streams replayed against the new code, read from the raw evidence files (design 17.2).

No scheduler, no LLM, no network: ``testkit.e6_replay.materialize`` rebuilds the organization a stream had at one moment (messages, run-log names,
agents, contract), and the product's own ``progress`` and ``client_items`` read it. A missing evidence file fails the test, never skips it.

This module holds the replays of D-E6-1 (A1 and A2): A-1 to A-5, the question block of the results 8613, 762f, 6c63 and d80f, and of every result with a
block that root received in E6's three streams; and those of D-E6-2 (B): B-1 and B-2, the user's runs the team held or got back in E6's s3 memo 1.
"""

import re

import pytest
from testkit.e6_replay import EV6, materialize

from hirearchy.core import ROOT, Org
from hirearchy.kernel import client_items
from hirearchy.progress import progress
from hirearchy.reflection import user_approved, user_committed, user_spend

SERVICE = "weekly-memo"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


def replay(tmp_path, stream, cut, task_id, result_id):
    """The organization of ``stream`` at ``cut``; the line of the task ``task_id`` root sent in it, and the result ``result_id`` that answered it."""
    org = Org(materialize(stream, cut, tmp_path / "org"))
    assert any(m.id == task_id for m in org.sent(ROOT)), f"{task_id} is not in root's sent box at {cut}"
    result = next(m for box in ("read", "inbox") for m in org.messages(ROOT, box) if m.id.endswith(f"-lead-{result_id}"))
    return progress(org, task_id=task_id), client_items(result.body)


def test_a1_8613_lists_the_style_item_as_a_note_and_flags_the_two_questions(tmp_path):
    """A-1 (E6 s1 #56): 8613's block holds two items that name C6 and C3 (questions) and ``Style: 'himself' ...`` (a note). 0a.3 flagged three questions,
    and the style note decided s1's clause 3 FAIL; now the path stays withheld for the two questions and the note is only listed (D-E6-1)."""
    line, items = replay(tmp_path, "s1", "20261024T160847113000", "20261024T160535424081-root-b0fe", "8613")
    assert [q.split(":")[0] for q in items.questions] == ["C6", "C3"]
    assert items.notes == ("Style: 'himself' in Sam's table row (reviewer: harmless).",)
    assert (
        "artifacts withheld (ask first). 2 questions for the client: ask the user before you copy or deliver. "
        "1 note for the client (no criterion): Style: 'himself' in Sam's table row (reviewer: harmless). no feedback yet."
    ) in line


def test_a2_762f_the_marker_tail_is_no_item_and_the_three_list_items_are_the_questions(tmp_path):
    """A-2 (E6 s1 #70): 762f's marker line is ``Questions for the client: (reviewer flags; I did not settle them, and they touch your answers)`` before a
    list of three items (C5, C4, C5). 0a.3 counted the tail as a fourth question; A1 reads it as a remark."""
    line, items = replay(tmp_path, "s1", "20261024T161928019000", "20261024T161442312966-root-d675", "762f")
    assert len(items.questions) == 3 and items.notes == ()
    assert "3 questions for the client" in line and "note for the client" not in line
    assert "4 questions" not in line


def test_a3_6c63_the_one_question_without_a_criterion_is_a_note_and_its_path_is_shown(tmp_path):
    """A-3, A2's cost (E6 s3 #42): 6c63's one item names no criterion id, so it is a note: the path is shown (it was withheld for a question that Lena was
    asked anyway in T8, a declared limit of the design)."""
    line, items = replay(tmp_path, "s3", "20261024T172839677000", "20261024T172453163611-root-9a5b", "6c63")
    assert items.questions == () and len(items.notes) == 1
    assert "artifacts: lead/writer/work/memo-2026-10-05.md, lead/reviewer/work/review-memo-2026-10-05-summary-line.md" in line
    assert "1 note for the client (no criterion): Keep or delete the '## Open, not decided' section" in line
    assert "questions for the client" not in line and "withheld" not in line


def test_a4_d80f_two_questions_and_no_note_as_before(tmp_path):
    """A-4 (E6 s1 #23): d80f holds two items that name criteria: two questions, no note, the path withheld, as 0a.3 did."""
    line, items = replay(tmp_path, "s1", "20261024T154519419000", "20261024T154227019921-root-f06d", "d80f")
    assert len(items.questions) == 2 and items.notes == ()
    assert "artifacts withheld (ask first). 2 questions for the client: ask the user before you copy or deliver." in line
    assert "note for the client" not in line


def test_a5_every_recorded_result_holds_49_items_47_questions_and_2_notes():
    """A-5: over the 19 results with a ``Questions for the client:`` block that root received in E6's s1, s2 and s3 (49 items after A1, which drops
    762f's tail from 50): 47 name a criterion id and 2 do not (8613's style item and 6c63's section item)."""
    marker = re.compile(r"^\W*questions for the client", re.IGNORECASE | re.MULTILINE)
    results = []
    for stream in ("s1", "s2", "s3"):
        for box in ("read", "inbox"):
            folder = EV6 / stream / "msgs" / box
            if not folder.is_dir() and box == "read":
                pytest.fail(f"no evidence directory {folder}")
            for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
                text = path.read_text(encoding="utf-8")
                if "type: result" in text.split("---")[1] and marker.search(text):
                    results.append(client_items(text))
    assert len(results) == 19
    assert sum(len(r.questions) + len(r.notes) for r in results) == 49
    assert sum(len(r.questions) for r in results) == 47 and sum(len(r.notes) for r in results) == 2


def the_case(org, task_id):
    """The case of ``lead``'s service that holds the task ``task_id``."""
    (case,) = [c for c in org.runtime.case_history.cases("lead", SERVICE) if task_id in {t.id for t in c.tasks}]
    return case


def test_b1_bc02_the_team_holds_the_users_runs_of_the_open_request_and_the_reply_says_so(tmp_path):
    """B-1 (E6 s3 #19, D-E6-2): bc02 revises 4a3e, whose only result (11cc) is ``blocked``, so the request is open and the team holds 17 - 5 - 1 = 11 of the
    user's runs. 0a.3 said "Nothing else is left ... Ask the user now for 4 more run(s)" there; the default hand-down is unchanged (1 run, nothing is
    left of the approval), and after bc02 the approval is 16: the default's run with nothing left is no approval of the user's (D-E7-2 A2, design 4.7),
    so the case total names the overspend of the contract (17 of 16) in the same reply."""
    org = Org(materialize("s3", "20261024T171425096624", tmp_path / "org"))
    bc02 = next(m for m in org.sent(ROOT) if m.id == "20261024T171425096624-root-bc02")
    four = "20261024T170957358424-root-4a3e"
    assert org.runtime.service_steps.rework_step(bc02) == f"The team still holds 11 of the user's runs for {four}; the rework can use them."
    case = the_case(org, bc02.id)
    assert case.open_tasks == (four, bc02.id) and user_approved(case, 16) == 16
    assert org.runtime.service_reports.case_total(bc02) == (
        "case total: 5 runs used of 17 handed down (contract: 16 per request). This case now exceeds the per-request budget of 16: tell the user."
    )
    before = Org(materialize("s3", "20261024T171425096623", tmp_path / "before"))
    assert before.runtime.case_allowance.left("lead", SERVICE, four) == 0  # the held runs are not handed down again: bc02 got 1


def test_b2_9a5b_the_runs_the_relayed_result_carried_back_are_the_users_and_the_rework_asks_for_nothing(tmp_path):
    """B-2 (E6 s3 #36, D-E6-2): 5d4a (relayed, 6 runs, 5 charged) was answered by 406b with a return of 7: 6 are the user's runs coming back. At 9a5b the
    user has committed 12 of the 16 approved (0a.3 read 18 of 18 and said "Ask the user now for 4 more run(s)"; 0a.4 read 17: bc02's default run with
    nothing left is no approval of the user's, D-E7-2 A2, design 4.7), so the step is empty."""
    org = Org(materialize("s3", "20261024T172453163611", tmp_path / "org"))
    nine = next(m for m in org.sent(ROOT) if m.id == "20261024T172453163611-root-9a5b")
    case = the_case(org, nine.id)
    assert case.relayed_to_user == 6
    assert user_approved(case, 16) - user_committed(case) == 4 and user_spend(case) == 12
    assert org.runtime.service_steps.rework_step(nine) == ""


def test_b2_just_before_9a5b_the_default_hand_down_is_what_the_user_has_left(tmp_path):
    """B-2 (E6 s3 #36, D-E6-2): before 9a5b, 5d4a's 1 unspent run was all it still had, so 406b's 7 carry 6 back to the user: the default hand-down is what
    is left of the approval (it was 1: nothing was left). bc02's own run is no approval of the user's (D-E7-2 A2, design 4.7), so that is 5 (0a.4 read 6)."""
    org = Org(materialize("s3", "20261024T172453163610", tmp_path / "org"))
    assert org.runtime.case_allowance.left("lead", SERVICE, "20261024T171425096624-root-bc02") == 5


def test_f1_dd34_the_lead_works_at_the_relayed_tier_while_roots_relayed_rework_is_open(tmp_path):
    """F-1 (E6 s1; D-E6-5, F-E6-7): at dd34's cut roots relayed 3a54 is the lead's open task, so the delegation the lead sends without ``revises`` (the
    window writer task ``...-lead-dd34``, unstamped in E6) inherits ``relayed``."""
    org = Org(materialize("s1", "20261024T154745377872", tmp_path / "org"))
    assert org.runtime.rework_context.work_tier("lead") == "relayed"
    assert org.runtime.rework_context.work_tier(ROOT) is None


@pytest.mark.parametrize("cut", ["20261024T172627799242", "20261024T172724489270"], ids=["395b", "d13d"])
def test_f2_395b_and_d13d_the_lead_works_at_the_human_tier_while_9a5b_is_open(tmp_path, cut):
    """F-2 (E6 s3; D-E6-5, F-E6-7): the user's rework 9a5b is the lead's open task at the cuts of 395b and d13d, so their delegations inherit ``human``."""
    org = Org(materialize("s3", cut, tmp_path / "org"))
    assert org.runtime.rework_context.work_tier("lead") == "human"
