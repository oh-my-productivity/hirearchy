"""``CaseTaskLines``: the line of a root task, from the parts it is made of; ``artifacts_of`` and ``rated``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import ROOT, Message, artifact_paths, clip_line
from hirearchy.progress._lines import CaseTaskLines, artifacts_of
from hirearchy.progress._ports import TaskLines
from hirearchy.progress._counts import LogRunCounts
from hirearchy.progress._states import MailTaskStates
from hirearchy.progress._teams import AgentTaskTeams
from hirearchy.progress.testing import FixedCaseTotals, FixedTeamActivity, ProgressWorld
from hirearchy.reflection import Case, Verdict, rated
from hirearchy.reflection.testing import FixedCaseHistory


NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def lines(
    w: ProgressWorld, activity: FixedTeamActivity | None = None, history: FixedCaseHistory | None = None, totals: FixedCaseTotals | None = None,
) -> CaseTaskLines:
    return CaseTaskLines(
        AgentTaskTeams(w.agents), MailTaskStates(w.mail, w.pauses, w.tasks), LogRunCounts(w.mail, w.runs), activity or FixedTeamActivity(),
        history or w.history, totals or w.totals, w.mail,
    )


def case(tasks: list[Message], verdicts: list[Verdict] | None = None, reworks: int = 0) -> Case:
    return Case(
        id=tasks[0].id, service="brief", owner="ceo", tasks=tasks, result=None, state="done", playbook=1, used=1, reworks=reworks, budget=0, runs=0,
        lessons=[], verdicts=verdicts or [], started=None, finished=None,
    )


def verdict(step: int, task: Message) -> Verdict:
    return Verdict("accept", "", None, task.id, step, task)


def test_it_is_a_task_lines(w: ProgressWorld) -> None:
    assert isinstance(lines(w), TaskLines)


def test_a_line_is_the_title_the_state_the_runs_and_the_id(w: ProgressWorld, task: Message) -> None:
    assert lines(w).line(task, None, NOW) == f'"Write the report": working. unread work: ceo. runs 0 of 8. (task {task.id})'


def test_the_last_activity_is_how_long_ago(w: ProgressWorld, task: Message) -> None:
    ago = FixedTeamActivity({"ceo": NOW - timedelta(minutes=7)})
    assert ". last activity 7m ago. " in lines(w, ago).line(task, None, NOW)
    assert ". last activity 0s ago. " in lines(w, FixedTeamActivity({"ceo": NOW + timedelta(minutes=7)})).line(task, None, NOW)  # not before now
    assert "last activity" not in lines(w).line(task, None, NOW)


def test_a_finished_task_lists_its_artifacts_or_says_there_are_none(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", "## Summary\nok\n\n## Artifacts\n- a/b.md (3 words)\n* c.md", 0)
    assert ". artifacts: a/b.md, c.md. " in lines(w).line(task, done, NOW)
    failed = w.answer(task, "failed", "no", 0)
    assert ". no artifacts. " in lines(w).line(task, failed, NOW)
    blocked = w.answer(task, "blocked", "no", 0)
    assert "artifacts" not in lines(w).line(task, blocked, NOW)


def request(w: ProgressWorld, title: str = "brief: ai", playbook: int | None = 2) -> Message:
    """A request for the service ``brief`` of ``ceo`` (the delivered task, marked as one)."""
    made = w.delegate(ROOT, "ceo", title, 5)
    made.service, made.playbook = "brief", playbook
    return made


def test_a_service_request_carries_its_tag_and_the_version_of_the_playbook(w: ProgressWorld) -> None:
    assert lines(w).line(request(w), None, NOW).startswith('"brief: ai" [service brief v2]: working.')
    assert lines(w).line(request(w, playbook=None), None, NOW).startswith('"brief: ai" [service brief v0]: working.')


def test_a_delivered_request_asks_for_feedback_until_the_client_gives_it(w: ProgressWorld) -> None:
    first = request(w)
    done = w.answer(first, "done", "ok", 0)
    assert ". no feedback yet. " not in lines(w).line(first, None, NOW)
    assert ". no feedback yet. " in lines(w).line(first, done, NOW)
    rated_case = FixedCaseHistory([case([first], [verdict(0, first)])])
    assert "no feedback yet" not in lines(w, history=rated_case).line(first, done, NOW)


def test_a_rework_chain_adds_the_total_of_the_case_without_a_dangling_full_stop(w: ProgressWorld) -> None:
    first, second = request(w), request(w, "brief: ai again")
    total = "case total: 5 runs used of 16 handed down (contract: 10 per request)."
    chain = FixedCaseHistory([case([first, second], reworks=1)])
    out = lines(w, history=chain, totals=FixedCaseTotals({first.id: total})).line(first, None, NOW)
    assert f". {total} (task {first.id})" in out and ".." not in out
    single = FixedCaseHistory([case([first], reworks=0)])
    assert "case total" not in lines(w, history=single, totals=FixedCaseTotals({first.id: total})).line(first, None, NOW)


def test_a_total_of_several_sentences_joins_with_full_stops_and_never_doubles_them(w: ProgressWorld) -> None:
    """D-E5-1: the case total can now hold the overspend sentence and the relayed sentence; each ends in a full stop, and the line joins them with
    ". " and strips only the last one."""
    first, second = request(w), request(w, "brief: ai again")
    total = (
        "case total: 14 runs used: 11 by the user's requests, 3 by your relayed rework R; 13 handed down (contract: 10 per request). "
        "The user's requests now cost 11 runs, more than the 10 the user approved for this case (contract: 10 per request): tell the user. "
        "The runs of your relayed rework are your own spend, not the user's: report them to the user as yours, and never ask the user to fund them."
    )
    chain = FixedCaseHistory([case([first, second], reworks=1)])
    out = lines(w, history=chain, totals=FixedCaseTotals({first.id: total})).line(first, None, NOW)
    assert out.endswith(f"{total} (task {first.id})") and ".." not in out


def test_artifacts_of_drops_the_word_counts_and_the_bullets() -> None:
    result = Message(sender="ceo", to=ROOT, type="result", body="## Summary\nx\n## Artifacts\n- ceo/a.md (12 words)\n\n* ceo/b.md\n## Lessons\n- not me")
    assert artifacts_of(result) == ["ceo/a.md", "ceo/b.md"]
    assert artifacts_of(Message(sender="ceo", to=ROOT, type="result", body="no sections")) == []


def test_artifacts_of_is_artifact_paths_of_the_body() -> None:
    """``progress`` and ``reflection`` parse a result's artifacts one way: ``kernel.artifact_paths``."""
    bodies = ["## Summary\nx\n## Artifacts\n- ceo/a.md (12 words)\n\n* ceo/b.md\n## Lessons\n- not me", "no sections", "", "## ARTIFACTS\n-   c.md (1 words)"]
    for body in bodies:
        assert artifacts_of(Message(sender="ceo", to=ROOT, type="result", body=body)) == artifact_paths(body)


@pytest.mark.parametrize(("step_of_verdicts", "expected"), [([], False), ([0], True), ([1], True), ([2], True)])
def test_a_delivery_is_rated_by_a_verdict_on_it_or_on_a_later_rework(step_of_verdicts: list[int], expected: bool) -> None:
    first, second = Message(sender=ROOT, to="ceo", type="task", title="a", body="", id="1"), Message(sender=ROOT, to="ceo", type="task", title="b", body="", id="2")
    found = case([first, second], [verdict(s, [first, second][min(s, 1)]) for s in step_of_verdicts], reworks=1)
    assert rated(found, second) is (bool(step_of_verdicts) and max(step_of_verdicts) >= 1)
    assert rated(found, first) is expected
    assert rated(None, first) is False


def test_a_line_says_who_kept_the_runs(w: ProgressWorld, task: Message) -> None:
    w.write(ROOT, "ceo", "More", "7 more", 7)
    for _ in range(9):
        w.use_run("ceo")
    done = w.answer(task, "done", "ok", 0)
    assert ". runs 9 of 15. 0 returned (kept by ceo). " in lines(w).line(task, done, NOW)
    returned = w.answer(task, "done", "ok", 6)
    assert "kept by" not in lines(w).line(task, returned, NOW)
    assert "kept by" not in lines(w).line(task, None, NOW)


# D-E6-1 (A2): only an item that names a criterion id (``C<k>``) is a question for the client; these items name one, so the tests below keep exercising
# the question path (the flag, the withheld path). The notes (items without an id) are tested in their own tests.
QUESTIONS = "## Summary\nok\n\nQuestions for the client:\n- C1: Keep Marta's row?\n- C2: Which Friday?\n\n## Artifacts\n- a/b.md (3 words)"
FLAG = "for the client: ask the user before you copy or deliver"


def rework(w: ProgressWorld, first: Message, source: str | None) -> Message:
    """Root sends a rework of ``first``; ``source`` says whether the user asked for it (``human``) or the assistant did (``relayed``)."""
    return w.post(Message(sender=ROOT, to="ceo", type="task", title="again", body="goal", budget=3, revises=first.id, source=source))


def test_a_done_result_with_client_questions_is_flagged(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", QUESTIONS, 0)
    assert f". artifacts withheld (ask first). 2 questions for the client: ask the user before you copy or deliver. (task {task.id})" in lines(w).line(task, done, NOW)


def test_one_question_is_singular(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", "Questions for the client: C1: Keep Marta's row?\n\n## Artifacts\n- a.md", 0)  # D-E6-1: the item names C1
    out = lines(w).line(task, done, NOW)
    assert f". 1 question {FLAG}. " in out and "1 questions" not in out


def test_a_service_request_is_flagged_before_the_no_feedback_part(w: ProgressWorld) -> None:
    first = request(w)
    done = w.answer(first, "done", QUESTIONS, 0)
    assert f". artifacts withheld (ask first). 2 questions for the client: ask the user before you copy or deliver. no feedback yet. " in lines(w).line(first, done, NOW)


def test_the_flag_ends_with_a_verdict_or_a_human_rework(w: ProgressWorld) -> None:
    first = request(w)
    done = w.answer(first, "done", QUESTIONS, 0)
    assert FLAG in lines(w).line(first, done, NOW)
    rated_case = FixedCaseHistory([case([first], [verdict(0, first)])])
    assert FLAG not in lines(w, history=rated_case).line(first, done, NOW)  # the client's verdict on the case
    rework(w, first, "human")
    assert FLAG not in lines(w).line(first, done, NOW)  # the user asked for the rework: it answers the questions


def test_a_relayed_rework_keeps_the_flag(w: ProgressWorld) -> None:  # DR-17
    first = request(w)
    done = w.answer(first, "done", QUESTIONS, 0)
    rework(w, first, "relayed")
    assert "2 questions for the client: ask the user before you copy or deliver" in lines(w).line(first, done, NOW)


def test_a_one_off_task_keeps_its_flag_until_a_human_rework_revises_it(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", QUESTIONS, 0)
    assert "2 questions for the client" in lines(w).line(task, done, NOW)  # nothing else records that the questions were asked
    rework(w, task, "relayed")
    assert "2 questions for the client" in lines(w).line(task, done, NOW)
    rework(w, task, "human")
    assert "questions for the client" not in lines(w).line(task, done, NOW)


def test_a_blocked_result_with_questions_is_flagged(w: ProgressWorld, task: Message) -> None:  # inverts 0a.1's test_a_blocked_result_is_not_flagged
    blocked = w.answer(task, "blocked", QUESTIONS, 0)
    assert ": blocked" in lines(w).line(task, blocked, NOW)
    assert f". 2 questions {FLAG}. (task {task.id})" in lines(w).line(task, blocked, NOW)
    failed = w.answer(task, "failed", QUESTIONS, 0)
    assert "for the client" not in lines(w).line(task, failed, NOW)  # a failed result has nothing to copy or deliver
    assert "for the client" not in lines(w).line(task, None, NOW)


def test_a_blocked_result_has_no_artifact_part(w: ProgressWorld, task: Message) -> None:
    blocked = w.answer(task, "blocked", QUESTIONS, 0)
    assert "artifacts" not in lines(w).line(task, blocked, NOW)  # neither "artifacts: ..." nor "no artifacts" nor the withheld part


def test_the_artifact_path_is_withheld_while_questions_are_open(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", QUESTIONS, 0)
    out = lines(w).line(task, done, NOW)
    assert f". artifacts withheld (ask first). 2 questions {FLAG}. (task {task.id})" in out
    assert "a/b.md" not in out and "artifacts:" not in out
    failed = w.answer(task, "failed", QUESTIONS, 0)
    assert ". artifacts: a/b.md. " in lines(w).line(task, failed, NOW)  # a failed result asks nothing: today's text, the path included


def test_the_path_returns_once_the_questions_are_settled(w: ProgressWorld) -> None:
    first = request(w)
    done = w.answer(first, "done", QUESTIONS, 0)
    assert "artifacts withheld (ask first)" in lines(w).line(first, done, NOW) and "a/b.md" not in lines(w).line(first, done, NOW)
    rework(w, first, "relayed")
    assert "artifacts withheld (ask first)" in lines(w).line(first, done, NOW)  # the assistant's own rework settles nothing
    rated_case = FixedCaseHistory([case([first], [verdict(0, first)])])
    settled = lines(w, history=rated_case).line(first, done, NOW)
    assert ". artifacts: a/b.md. " in settled and "withheld" not in settled  # the client's verdict
    rework(w, first, "human")
    assert ". artifacts: a/b.md. " in lines(w).line(first, done, NOW)  # the user asked for the rework: it answers the questions
    plain = w.answer(first, "done", "## Summary\nok\n\n## Artifacts\n- a/b.md", 0)
    assert ". artifacts: a/b.md. " in lines(w).line(first, plain, NOW)  # no questions, no withholding


def test_a_result_whose_questions_are_none_is_not_flagged(w: ProgressWorld, task: Message) -> None:  # zero pin: no items, no flag
    for body in ("Questions for the client: none.\n\n## Artifacts\n- a.md", "ok, nothing asked", "Questions for the client:\n\n## Lessons\n- x"):
        assert "for the client" not in lines(w).line(task, w.answer(task, "done", body, 0), NOW)


# ------------------------------------------------------------------------------ the notes for the client (D-E6-1, A2/A3)

STYLE = "Style: 'himself' in Sam's table row (reviewer: harmless)."
NOTES = f"## Summary\nok\n\nQuestions for the client:\n- {STYLE}\n- Keep the title short?\n\n## Artifacts\n- a/b.md (3 words)"
MIXED = f"## Summary\nok\n\nQuestions for the client:\n- C3: Keep Marta's row?\n- {STYLE}\n- C4: Which Friday?\n\n## Artifacts\n- a/b.md (3 words)"
ONE_NOTE = f"## Summary\nok\n\nQuestions for the client:\n- {STYLE}\n\n## Artifacts\n- a/b.md (3 words)"
NOTE_PART = "note for the client (no criterion)"


def test_a_note_is_listed_and_withholds_nothing(w: ProgressWorld, task: Message) -> None:
    """D-E6-1: an item without a criterion id is a note: the line lists it, the path stays, no flag."""
    done = w.answer(task, "done", ONE_NOTE, 0)
    out = lines(w).line(task, done, NOW)
    assert f". artifacts: a/b.md. 1 {NOTE_PART}: Style: 'himself' in Sam's table row (reviewer: harmless). (task {task.id})" in out
    assert "withheld" not in out and FLAG not in out and "1 notes" not in out


def test_notes_are_plural_and_keep_the_order_of_the_block(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", NOTES, 0)
    out = lines(w).line(task, done, NOW)
    assert f". artifacts: a/b.md. 2 notes for the client (no criterion): {STYLE}; Keep the title short?. (task {task.id})" in out
    assert FLAG not in out


def test_only_the_last_full_stop_of_the_notes_part_is_stripped(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", "Questions for the client:\n- first note.\n- last note.\n\n## Artifacts\n- a.md", 0)
    out = lines(w).line(task, done, NOW)
    assert f". 2 notes for the client (no criterion): first note.; last note. (task {task.id})" in out  # "last note" + the join's ". " + the task id
    assert ".." not in out


def test_more_than_five_notes_are_counted(w: ProgressWorld, task: Message) -> None:
    body = "Questions for the client:\n" + "\n".join(f"- note {i}" for i in range(1, 8)) + "\n\n## Artifacts\n- a.md"
    out = lines(w).line(task, w.answer(task, "done", body, 0), NOW)
    assert f". 7 notes for the client (no criterion): note 1; note 2; note 3; note 4; note 5; and 2 more. (task {task.id})" in out


def test_each_note_is_cut_to_160_characters(w: ProgressWorld, task: Message) -> None:
    long = "A long note about the memo? " * 12
    out = lines(w).line(task, w.answer(task, "done", f"Questions for the client:\n- {long}\n\n## Artifacts\n- a.md", 0), NOW)
    assert f"(no criterion): {clip_line(long.strip(), 160)}" in out and len(clip_line(long.strip(), 160)) == 160 and long.strip() not in out


def test_questions_and_notes_flag_withhold_and_list_the_notes_after_the_questions(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", MIXED, 0)
    out = lines(w).line(task, done, NOW)
    assert (
        f". artifacts withheld (ask first). 2 questions {FLAG}. 1 {NOTE_PART}: Style: 'himself' in Sam's table row (reviewer: harmless). (task {task.id})" in out
    )
    assert "a/b.md" not in out


def test_the_notes_part_comes_before_no_feedback_yet(w: ProgressWorld) -> None:
    first = request(w)
    done = w.answer(first, "done", MIXED, 0)
    assert (
        f". 2 questions {FLAG}. 1 {NOTE_PART}: Style: 'himself' in Sam's table row (reviewer: harmless). no feedback yet. " in lines(w).line(first, done, NOW)
    )
    notes_only = w.answer(first, "done", ONE_NOTE, 0)
    assert f". artifacts: a/b.md. 1 {NOTE_PART}: Style: 'himself' in Sam's table row (reviewer: harmless). no feedback yet. " in lines(w).line(first, notes_only, NOW)


def test_an_id_tagged_marker_tail_before_a_list_of_notes_is_still_a_question(w: ProgressWorld, task: Message) -> None:
    """A1/Deviation 1: the tail names C4, so it is a question; its path is withheld although the list holds only notes."""
    body = f"Questions for the client: C4: should non-actions be excluded?\n- {STYLE}\n\n## Artifacts\n- a/b.md"
    out = lines(w).line(task, w.answer(task, "done", body, 0), NOW)
    assert f". artifacts withheld (ask first). 1 question {FLAG}. 1 {NOTE_PART}: Style: 'himself' in Sam's table row (reviewer: harmless). (task {task.id})" in out
    assert "a/b.md" not in out


def test_a_blocked_result_lists_its_notes_without_an_artifact_part(w: ProgressWorld, task: Message) -> None:
    out = lines(w).line(task, w.answer(task, "blocked", ONE_NOTE, 0), NOW)
    assert f". 1 {NOTE_PART}: " in out and "artifacts" not in out and FLAG not in out


def test_a_failed_result_and_no_result_list_no_notes(w: ProgressWorld, task: Message) -> None:
    assert NOTE_PART not in lines(w).line(task, w.answer(task, "failed", ONE_NOTE, 0), NOW)
    assert NOTE_PART not in lines(w).line(task, None, NOW)


def test_settled_notes_are_no_longer_listed(w: ProgressWorld) -> None:
    first = request(w)
    done = w.answer(first, "done", MIXED, 0)
    assert NOTE_PART in lines(w).line(first, done, NOW)
    rework(w, first, "relayed")
    assert NOTE_PART in lines(w).line(first, done, NOW)  # the assistant's own rework settles neither part (DR-17)
    rated_case = FixedCaseHistory([case([first], [verdict(0, first)])])
    assert NOTE_PART not in lines(w, history=rated_case).line(first, done, NOW) and "for the client" not in lines(w, history=rated_case).line(first, done, NOW)
    rework(w, first, "human")
    out = lines(w).line(first, done, NOW)
    assert NOTE_PART not in out and FLAG not in out  # the user asked for the rework: neither part


def test_a_block_that_says_none_adds_no_part(w: ProgressWorld, task: Message) -> None:
    out = lines(w).line(task, w.answer(task, "done", "Questions for the client: none.\n\n## Artifacts\n- a.md", 0), NOW)
    assert "for the client" not in out and ". artifacts: a.md. " in out
