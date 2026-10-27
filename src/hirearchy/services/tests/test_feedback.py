# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError
from testkit.reflection_world import summarize
from testkit.services_world import ENG, define, deliver, request, svc, write_version

from hirearchy.services import FEEDBACK_HEADER, LINK_HEADER


# ----------------------------------------------------------------------------------------- feedback
def test_feedback_is_a_quiet_note_from_the_requester(svc):
    org = svc
    task = request(org)
    with pytest.raises(OrgError, match="wait for the result"):
        org.feedback(ROOT, task.id, "accept")
    deliver(org, "ceo", task)
    with pytest.raises(OrgError, match="verdict must be"):
        org.feedback(ROOT, task.id, "meh")
    with pytest.raises(OrgError, match="rejection needs a note"):
        org.feedback(ROOT, task.id, "reject")
    with pytest.raises(OrgError, match="limit is 1000"):
        org.feedback(ROOT, task.id, "reject", "x" * 1001)
    ceo_unread = org.unread("ceo")
    note = org.feedback(ROOT, task.id, "reject", "No week-over-week changes.")
    assert (note.type, note.to, note.reply_to, note.feedback, note.wake) == ("note", "ceo", task.id, "reject", False)
    assert note.title == f'feedback on "{task.title}": reject'
    assert note.body == FEEDBACK_HEADER + "\n\nNo week-over-week changes."
    assert org.unread("ceo") == ceo_unread and note.budget == 0
    assert "feedback: reject" in org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{note.id}.md").render()
    assert org.feedback(ROOT, task.id, "accept").body == FEEDBACK_HEADER + "\n\naccepted"


def test_only_the_requester_gives_feedback_on_a_service_request(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    org.delegate(ROOT, "ceo", "Project", "g", "c", budget=10)
    task = org.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    deliver(org, ENG, task)
    with pytest.raises(OrgError, match="is not a task you sent"):
        org.feedback(ROOT, task.id, "accept")  # root did not send it
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback("ceo", "nope", "accept")
    plain = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    with pytest.raises(OrgError, match="has no result yet"):
        org.feedback(ROOT, plain.id, "accept")  # a one-off task of root's: it takes a verdict once it has a result
    assert org.feedback("ceo", task.id, "accept").to == ENG


def test_feedback_on_a_rework_belongs_to_the_case_and_the_latest_is_the_final_verdict(svc):
    org = svc
    first = request(org)
    deliver(org, "ceo", first)
    org.feedback(ROOT, first.id, "reject", "Too long.")
    rework = request(org, revises=first.id, budget=3, source="human")  # root sends a request back with `request` (`delegate` is refused, P4)
    deliver(org, "ceo", rework)
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert case.verdict == "reject"  # feedback on the first task counts for the case
    time.sleep(0.002)
    org.feedback(ROOT, rework.id, "accept")
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert case.verdict == "accept" and case.feedback.reply_to == rework.id
    assert summarize([case]).accept == 1 and summarize([case]).reject == 0


# ----------------------------------------------------------------------------------------- confirms after an answer (P2, one answer per rejection)
V1 = ["At most 600 words", "Every factual claim has a source URL"]
NEW_RULE = "The memo starts with a Summary line"
YES = "Yes, add it."


def rejected(org, words="Always start with a Summary line."):
    task = request(org)
    deliver(org, "ceo", task)
    return task, org.feedback(ROOT, task.id, "reject", words, source="human")


def links_on(org, rejection):
    return [m for m in org.sent(ROOT) if m.reply_to == rejection.id and m.criterion]


def test_confirms_after_an_answering_version_with_a_link_is_answered(svc):
    org = svc
    task, no = rejected(org)
    org.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=[NEW_RULE], answers=no.id, about="C1", words=YES)
    (link,) = links_on(org, no)
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, task.id, "reject", "Also this.", source="human", criterion=["C3"], confirms=no.id)
    assert str(info.value) == (
        f"refused: rejection {no.id} was answered by contract v2 of `weekly-brief` (define_service(..., answers=\"{no.id}\"); CLI: define-service "
        f"--answers) and its link {link.id} records the user's yes: one rejection gets one answer. A different answer needs a new rejection and its "
        "question. Nothing was recorded."
    )
    assert links_on(org, no) == [link]  # nothing was recorded
    other_task, other = rejected(org, "Another thing entirely.")
    assert org.feedback(ROOT, other_task.id, "reject", "No.", source="human", criterion=["none"], confirms=other.id).criterion == "none"  # unanswered: as ever


def test_confirms_after_an_answering_version_without_a_link_takes_only_the_recovery_link(svc):
    org = svc
    task, no = rejected(org)
    write_version(org, 2, [*V1, NEW_RULE, "Names its week"], answers=no.id, about="C1", words=YES)  # the contract answers it; its link was never written
    recovery = (
        f"refused: rejection {no.id} was answered by contract v2 of `weekly-brief`, and its link is missing (its write failed). The only link it "
        f'still takes is that one: feedback(task_id="{task.id}", verdict="reject", confirms="{no.id}", criterion=["C3", "C4"], source="human", '
        "note=<the user's answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was recorded."
    )
    for wrong in ({"criterion": ["C3"]}, {"criterion": ["none"]}, {"criterion": ["C3", "C4"], "source": "relayed"}, {"criterion": ["C4", "C3", "C1"]}):
        with pytest.raises(OrgError) as info:
            org.feedback(ROOT, task.id, "reject", YES, **{"source": "human", **wrong}, confirms=no.id)
        assert str(info.value) == recovery
    link = org.feedback(ROOT, task.id, "reject", YES, source="human", criterion=["c4", "C3"], confirms=no.id)  # the same ids as a set
    assert (link.criterion, link.source, link.reply_to) == ("C4, C3", "human", no.id)
    assert org.runtime.service_evidence.confirmed("ceo", "weekly-brief") == frozenset({"C3", "C4"})  # the amendment is confirmed by its own link
    with pytest.raises(OrgError, match=f"^refused: rejection {no.id} was answered by contract v2 of `weekly-brief` \\(define_service"):
        org.feedback(ROOT, task.id, "reject", YES, source="human", criterion=["C3", "C4"], confirms=no.id)  # one link only


def test_a_second_confirms_without_a_contract_change_is_still_accepted(svc):
    """0a.1: the user may correct an answer; the latest human link decides what the rejection is about. Only an answering contract version closes it."""
    org = svc
    task, no = rejected(org)
    first = org.feedback(ROOT, task.id, "reject", "A one-off.", source="human", criterion=["none"], confirms=no.id)
    second = org.feedback(ROOT, task.id, "reject", "On reflection, about C1.", source="human", criterion=["C1"], confirms=no.id)
    assert (first.criterion, second.criterion) == ("none", "C1") and links_on(org, no) == [first, second]


def test_the_confirms_link_note_is_byte_identical(svc):
    org = svc
    task, no = rejected(org)
    link = org.feedback(ROOT, task.id, "reject", YES, source="human", criterion=["C1", "C2"], confirms=no.id)
    assert (link.sender, link.to, link.type, link.wake, link.source, link.criterion, link.reply_to, link.feedback) == (
        ROOT, "ceo", "note", False, "human", "C1, C2", no.id, None,
    )
    assert link.title == f'criterion link on "{task.title}": C1, C2'
    assert link.body == LINK_HEADER.format(confirms=no.id) + "\n\n" + YES
    assert link.body == (
        f"The client says what their rejection {no.id} was about, for reflection only: it does not change any task's acceptance criteria or outcome."
        "\n\nYes, add it."
    )


# ----------------------------------------------------------------------------------------- feedback on a one-off task (design 8.1, 8.3)
def one_off(org, to="ceo", status="done", title="Plain"):
    """Root's task without a service, answered by ``to``."""
    task = org.delegate(ROOT, to, title, "g", "c", budget=2)
    deliver(org, to, task, status=status)
    return task


def test_root_records_a_verdict_on_a_one_off_task_as_a_quiet_note(svc):
    org = svc
    task = one_off(org)
    ceo_unread = org.unread("ceo")
    note = org.feedback(ROOT, task.id, "reject", "  Too long.  ", source="human")
    assert (note.sender, note.to, note.type, note.reply_to, note.feedback, note.wake) == (ROOT, "ceo", "note", task.id, "reject", False)
    assert (note.source, note.criterion, note.budget) == ("human", None, 0)
    assert note.title == f'feedback on "{task.title}": reject'
    assert note.body == FEEDBACK_HEADER + "\n\nToo long."
    assert org.unread("ceo") == ceo_unread
    accepted = org.feedback(ROOT, task.id, "accept")
    assert accepted.body == FEEDBACK_HEADER + "\n\naccepted" and accepted.source == "relayed"  # the default of a root verdict


def test_a_one_off_verdict_on_a_blocked_or_failed_result_is_recorded(svc):
    org = svc
    for status in ("blocked", "failed"):
        task = one_off(org, status=status, title=f"Plain {status}")
        assert org.feedback(ROOT, task.id, "reject", "No.", source="human").reply_to == task.id


def test_a_one_off_task_without_a_result_keeps_todays_text(svc):
    org = svc
    task = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, task.id, "accept")
    assert str(info.value) == f"task {task.id} has no result yet: wait for the result, then give feedback."


def test_a_one_off_verdict_with_criterion_or_confirms_is_refused_one_off_no_link(svc):
    org = svc
    task = one_off(org)
    refusal = (
        f"refused: {task.id} is a one-off task: it has no contract, so its verdict names no criterion and answers no rejection. "
        "Leave out criterion and confirms (CLI: --criterion, --confirms). Nothing was recorded."
    )
    for extra in ({"criterion": ["none"]}, {"criterion": ["C1"]}, {"confirms": "20261017T000000000000-root-abcd"}):
        with pytest.raises(OrgError) as info:
            org.feedback(ROOT, task.id, "reject", "No.", source="human", **extra)
        assert str(info.value) == refusal
    assert not [m for m in org.sent(ROOT) if m.feedback]  # nothing was recorded


def test_a_one_off_verdict_on_a_retired_assignees_task_is_refused_one_off_gone(svc):
    org = svc
    org.hire(ROOT, "ops", "Operations", "Run ops.")
    task = one_off(org, to="ops")
    org.retire(ROOT, "ops", "closed")
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, task.id, "reject", "No.", source="human")
    assert str(info.value) == f"refused: ops, who did {task.id}, was retired, so the verdict has no one to tell. Nothing was recorded."
    assert not [m for m in org.sent(ROOT) if m.feedback]


def test_an_unknown_task_id_is_refused_one_off_unknown_with_roots_newest_ten_with_a_result(svc):
    org = svc
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, "nope", "accept")
    assert str(info.value) == (
        "refused: nope is not a task you sent: feedback records the user's verdict on one of your service requests or one-off tasks that has a "
        "result. Your newest: none. Nothing was recorded."
    )
    open_task = org.delegate(ROOT, "ceo", "Still open", "g", "c", budget=2)  # no result: not listed
    ids = []
    for n in range(6):
        service_task = request(org, topic=f"t{n}")
        deliver(org, "ceo", service_task)
        ids.append(service_task.id)
        ids.append(one_off(org, title=f"Plain {n}").id)
    with pytest.raises(OrgError) as info:
        org.feedback(ROOT, "nope", "accept")
    newest = ", ".join(sorted(ids, reverse=True)[:10])
    assert open_task.id not in newest and len(ids) == 12
    assert str(info.value) == (
        "refused: nope is not a task you sent: feedback records the user's verdict on one of your service requests or one-off tasks that has a "
        f"result. Your newest: {newest}. Nothing was recorded."
    )


def test_a_reject_needs_a_note_and_the_note_limit_holds_for_one_offs(svc):
    org = svc
    task = one_off(org)
    with pytest.raises(OrgError, match="rejection needs a note"):
        org.feedback(ROOT, task.id, "reject", "  ")
    with pytest.raises(OrgError, match="limit is 1000"):
        org.feedback(ROOT, task.id, "reject", "x" * 1001)
    with pytest.raises(OrgError, match="verdict must be"):
        org.feedback(ROOT, task.id, "meh")


def test_an_agents_feedback_on_a_non_service_task_keeps_todays_refusal(svc):
    org = svc
    org.send(ROOT, "ceo", "runs", budget=5)
    delegated = org.delegate("ceo", ENG, "Plain", "g", "c", budget=1)
    deliver(org, ENG, delegated)
    with pytest.raises(OrgError) as info:
        org.feedback("ceo", delegated.id, "accept")
    assert str(info.value) == f"{delegated.id} is not a service request you sent. Feedback is for requests made with `request`. Yours: none"


# ----------------------------------------------------------------------------------------- FEEDBACK-UNANSWERED: an accept waits for the case's answers (clause 2, design 13.2)
from hirearchy.kernel import Message  # noqa: E402
from hirearchy.services import AmendmentBasis  # noqa: E402
from hirearchy.services.testing import fs_world, memory_world  # noqa: E402

from . import _support as sup  # noqa: E402
from .test_request import QUESTION, BasisEvidence, held  # noqa: E402


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def gated(request, tmp_path):
    """A services world whose feedback asks a ``BasisEvidence`` (the record the test sets), the service defined."""
    evidence = BasisEvidence()
    w = sup.populated(request.param(tmp_path, evidence=evidence))
    sup.define(w)
    return w, evidence


def unanswered_text(note, assertion, rejected_task, service="weekly-brief", more="", question=QUESTION):
    """FEEDBACK-UNANSWERED (design 13.2), written out here word for word, for ``weekly-brief`` of ``ceo``."""
    return (
        f"refused: rejection {assertion} (message {note}) on task {rejected_task} of this case of `{service}` has no recorded answer yet{more}, so "
        "the user's accept waits: a case is closed only after its rejections have the user's answers. Record the answer first, then this accept again. "
        f"Ask the user the one question first if you have not: {question.removesuffix('.')}. On yes: "
        'define_service(owner="ceo", name="' + service + '", ..., answers="' + note + '", about=<the id you asked about>, words=<their answer, verbatim>) '
        "(CLI: hirearchy define-service ... --answers, --about, --words). "
        'On no, a one-off or "as it is": feedback(task_id="' + rejected_task + '", verdict="reject", confirms="' + note + '", criterion=["none"], '
        '["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>) '
        "(CLI: hirearchy feedback <task> reject --confirms ... --criterion ... --source human --note ...). Nothing was recorded."
    )


def test_a_human_accept_is_refused_while_an_earlier_human_rejection_of_the_same_case_has_no_answer(svc):
    task, no = rejected(svc)
    sent = len(svc.sent(ROOT))
    with pytest.raises(OrgError, match=r"^refused: rejection R1 \(message " + no.id + r"\) on task " + task.id + " of this case of `weekly-brief` has no recorded answer yet"):
        svc.feedback(ROOT, task.id, "accept", "This is right after all.", source="human")  # L-ASIS: "as it is", before the answer
    assert len(svc.sent(ROOT)) == sent  # nothing was recorded
    svc.feedback(ROOT, task.id, "reject", "No: as it is.", source="human", criterion=["none"], confirms=no.id)  # the user's answer
    assert svc.feedback(ROOT, task.id, "accept", "This is right after all.", source="human").feedback == "accept"


def test_the_refusal_is_feedback_unanswered_word_for_word(svc):
    task, no = rejected(svc)
    with pytest.raises(OrgError) as refusal:
        svc.feedback(ROOT, task.id, "accept", source="human")
    assert str(refusal.value) == unanswered_text(no.id, "R1", task.id, question='About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.')


def test_several_unanswered_name_the_oldest_then_and_k_more(svc):
    first, one = rejected(svc)
    again = request(svc, revises=first.id, source="human")  # the same case
    deliver(svc, "ceo", again)
    svc.feedback(ROOT, again.id, "reject", "Still no.", source="human")
    with pytest.raises(OrgError) as refusal:
        svc.feedback(ROOT, again.id, "accept", source="human")  # the rework already has its verdict: it is not unrated
    assert str(refusal.value).startswith(f"refused: rejection R1 (message {one.id}) on task {first.id} of this case of `weekly-brief` has no recorded answer yet (and 1 more: R2), so the user's accept waits")


def test_an_accept_of_an_already_judged_delivery_a_blocked_result_or_an_earlier_delivery_waits(svc):
    first, no = rejected(svc)
    rework = request(svc, revises=first.id, source="human")
    deliver(svc, "ceo", rework)  # unrated: its accept is the exception
    with pytest.raises(OrgError, match="has no recorded answer yet"):
        svc.feedback(ROOT, first.id, "accept", source="human")  # an earlier delivery of the case, already judged
    svc.feedback(ROOT, first.id, "reject", "No: a one-off.", source="human", criterion=["none"], confirms=no.id)  # answer R1 so the next request passes
    blocked = request(svc, "blocked")
    deliver(svc, "ceo", blocked, status="blocked")
    no_blocked = svc.feedback(ROOT, blocked.id, "reject", "It never finished.", source="human")  # a rejection of a blocked result is a rejection to answer
    with pytest.raises(OrgError, match=f"rejection R2 \\(message {no_blocked.id}\\) on task {blocked.id}"):
        svc.feedback(ROOT, blocked.id, "accept", source="human")


def test_a_revises_chain_to_another_assignee_starts_its_own_case(gated):
    w, evidence = gated
    first = sup.request(w)
    sup.answer(w, first)
    evidence.basis = AmendmentBasis((held("29990101T000000000000-root-0001", "R1", task=first.id),), ())
    elsewhere = w.d.post(Message(
        sender="root", to="ops", type="task", title="elsewhere", body="b", service="weekly-brief", revises=first.id, budget=1, source="human",
    ))  # sent to another assignee: not followed into the rejected case
    sup.answer(w, elsewhere)
    assert w.commands.feedback("root", elsewhere.id, "accept", source="human").feedback == "accept"  # its own case: nothing waits for it
    rework = sup.request(w, revises=first.id, source="human")  # the same assignee: the rejected case
    sup.answer(w, rework)
    with pytest.raises(OrgError, match="^refused: rejection R1 .* of this case of `weekly-brief` has no recorded answer yet"):
        w.commands.feedback("root", rework.id, "accept", source="human")  # not in `unrated` here: no exception


def test_an_unreadable_record_refuses_with_feedback_unreadable(gated):
    w, evidence = gated
    task = sup.request(w)
    sup.answer(w, task)
    evidence.error = OrgError("a mailbox cannot be read")
    sent = len(w.d.mail.sent("root"))
    with pytest.raises(OrgError) as refusal:
        w.commands.feedback("root", task.id, "accept", source="human")
    assert str(refusal.value) == (
        "refused: the record of `weekly-brief` cannot be read (a mailbox cannot be read), so the verdict was not recorded. "
        "Try again; if it persists, tell the user."
    )
    assert len(w.d.mail.sent("root")) == sent
    evidence.error = OSError("disk")
    with pytest.raises(OrgError, match=r"cannot be read \(disk\)"):
        w.commands.feedback("root", task.id, "accept", source="human")


# guards: they pin the edges of 13.2 and are green when written
def test_the_accept_of_the_cases_unrated_latest_rework_passes_and_then_the_answer_passes_p2_unrated(svc):
    first, no = rejected(svc)
    rework = request(svc, revises=first.id, source="human")
    deliver(svc, "ceo", rework)  # delivered before the answer: it has no verdict yet
    with pytest.raises(OrgError, match="have no verdict yet"):
        svc.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=[NEW_RULE], answers=no.id, about="C1", words=YES)  # P2-UNRATED: the verdict first
    assert svc.feedback(ROOT, rework.id, "accept", "This is right.", source="human").feedback == "accept"  # the exception (13.2)
    svc.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=[NEW_RULE], answers=no.id, about="C1", words=YES)  # then the answer passes
    assert svc.feedback(ROOT, first.id, "accept", source="human").feedback == "accept"  # and every accept passes


def test_an_accept_without_source_is_stamped_relayed_and_never_held(svc):
    task, no = rejected(svc)
    accepted = svc.feedback(ROOT, task.id, "accept")  # Org.feedback's default source is None: stamped relayed on root's verdict note
    assert (accepted.feedback, accepted.source) == ("accept", "relayed")


def test_relayed_and_agent_accepts_are_never_held(svc):
    task, no = rejected(svc)
    assert svc.feedback(ROOT, task.id, "accept", source="relayed").source == "relayed"
    define(svc, owner=ENG, actor="ceo", name="eng-brief", budget=4)
    svc.delegate(ROOT, "ceo", "Project", "g", "c", budget=20)
    inner = svc.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    deliver(svc, ENG, inner)
    svc.feedback("ceo", inner.id, "reject", "Not good.")
    assert svc.feedback("ceo", inner.id, "accept").feedback == "accept"  # an agent client's accept after its own rejection
    plain = svc.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    deliver(svc, "ceo", plain)
    assert svc.feedback(ROOT, plain.id, "accept", source="human").feedback == "accept"  # a one-off task has no service: never held


# ----------------------------------------------------------------------------------------- the settler after a human link (design 8.5)
from hirearchy.services import ItemWatch  # noqa: E402
from hirearchy.services.testing import AdmittingServiceEvidence, RecordingSettler  # noqa: E402

BEFORE = (ItemWatch("P1", "rule", "new", 1),)
AFTER = (ItemWatch("P1", "rule", "warning", 1, related=("R1",)),)


class Evolving(AdmittingServiceEvidence):
    """The watch the files derive, one state per read: ``states[0]`` at the first read (the state before the link), the next at the second."""

    def __init__(self, *states):
        super().__init__()
        self.states = states
        self.reads = 0

    def watch(self, owner, service):
        self.reads += 1
        return self.states[min(self.reads, len(self.states)) - 1]


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def settled(request, tmp_path):
    """A services world with a recording settler over the real one, and the stand-in whose watch changes after the first read."""
    evidence = Evolving(BEFORE, AFTER)
    made = []

    def spy(inner):
        found = RecordingSettler(inner, look=lambda: [m.id for m in w.d.inbox("ceo") if m.criterion])  # the links in the owner's inbox at the call
        made.append(found)
        return found

    w = sup.populated(request.param(tmp_path, evidence=evidence, settler=spy))
    sup.define(w)
    return w, made[0], evidence


def rejection(w, words="Too long."):
    task = sup.request(w)
    sup.answer(w, task)
    return task, w.commands.feedback("root", task.id, "reject", words, source="human")


def test_a_human_link_runs_the_settler_with_the_state_before_the_link(settled):
    w, spy, evidence = settled
    task, no = rejection(w)
    assert spy.calls == []  # a verdict relates nothing: only an answer does
    link = w.commands.feedback("root", task.id, "reject", "No, a one-off.", source="human", criterion=["none"], confirms=no.id)
    assert spy.calls == [("ceo", "weekly-brief", BEFORE, False)]  # the watch as it stood before the link was written
    assert spy.looks == [[link.id]]  # and the link was written when the settler ran
    assert evidence.reads == 2  # the state before the link, then the settler's own derivation


def test_a_relayed_link_runs_no_settler(settled):
    w, spy, evidence = settled
    task, no = rejection(w)
    w.commands.feedback("root", task.id, "reject", "A one-off.", source="relayed", criterion=["none"], confirms=no.id)
    assert spy.calls == [] and evidence.reads == 0  # a relayed link relates nothing
    other, other_no = rejection(w, "Again.")
    w.commands.feedback("root", other.id, "accept", source="human")
    assert spy.calls == []  # nor does an accept
