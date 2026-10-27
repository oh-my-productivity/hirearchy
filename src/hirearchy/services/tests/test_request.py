# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT, Message, OrgError, split_frontmatter
from testkit.reflection_world import lessons_of
from testkit.services_world import ENG, define, deliver, request, svc, work


# --------------------------------------------------------------------------------------------- request
def test_request_builds_a_task_from_the_contract(svc):
    org = svc
    msg = org.request(ROOT, "weekly-brief", {"topic": " ai chips ", "week": 42}, note="Short please.",
                      extra_acceptance=["Mention one risk"])
    assert isinstance(msg, Message) and msg.to == "ceo" and msg.type == "task"
    assert (msg.service, msg.contract, msg.playbook, msg.budget) == ("weekly-brief", 1, 0, 10)
    assert msg.title == "weekly-brief: ai chips"
    assert msg.body == (
        "## Goal\nDeliver the service `weekly-brief`: A one-page brief on the past week's news about a topic.\n\n"
        "## Request\n- topic: ai chips\n- week: 42\n\n"
        "## Acceptance criteria\n- C1: At most 600 words\n- C2: Every factual claim has a source URL\n- this request only: Mention one risk\n\n"
        "## Deliverable\none markdown file (format: markdown; at most 600 words)\n\n"
        "## Note from the requester\nShort please."
    )
    stored = org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{msg.id}.md")
    assert (stored.service, stored.contract, stored.playbook) == ("weekly-brief", 1, 0)
    head = stored.render().splitlines()[1]
    assert "service: weekly-brief (contract v1, playbook v0)" in head
    meta = split_frontmatter((org.dir("ceo") / "inbox" / f"{msg.id}.md").read_text())[0]
    assert meta["service"] == "weekly-brief" and meta["contract"] == 1 and meta["playbook"] == 0
    assert [m.id for m in org.outstanding(ROOT)] == [msg.id]


def test_request_records_the_current_playbook_version_and_optional_sections_are_absent(org):
    define(org, playbook="Steps.", deliverable={"description": "a file"}, inputs=[])
    msg = org.request(ROOT, "weekly-brief", None)
    assert msg.playbook == 1 and msg.title == "weekly-brief"
    assert "## Note from the requester" not in msg.body and "(no inputs)" in msg.body
    assert "## Deliverable\na file\n" in msg.body + "\n"


def test_request_checks_inputs(svc):
    org = svc
    with pytest.raises(OrgError, match="missing required input.*topic"):
        org.request(ROOT, "weekly-brief", {"week": "3"})
    with pytest.raises(OrgError, match="missing required input.*topic"):
        org.request(ROOT, "weekly-brief", {"topic": "  "})
    with pytest.raises(OrgError, match=r"unknown input\(s\).*colour.*Its inputs: topic, week"):
        org.request(ROOT, "weekly-brief", {"topic": "x", "colour": "red"})
    msg = org.request(ROOT, "weekly-brief", {"topic": "x", "week": ""})  # an empty optional input is simply absent
    assert "- week" not in msg.body and "- topic: x" in msg.body


def test_request_names_the_available_services_when_it_is_unknown(svc):
    with pytest.raises(OrgError, match=r"Services you can request: weekly-brief \(offered by ceo\)"):
        svc.request(ROOT, "nope", {})
    with pytest.raises(OrgError, match="Services you can request: none"):
        svc.request("ceo", "weekly-brief", {"topic": "x"})  # ceo has no reports that offer anything


def test_request_resolves_among_direct_reports_only(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief", budget=4)
    with pytest.raises(OrgError, match="no service `eng-brief`"):
        org.request(ROOT, "eng-brief", {"topic": "x"})  # root's direct reports are top-level agents
    org.delegate(ROOT, "ceo", "Project", "g", "c", budget=10)
    msg = org.request("ceo", "eng-brief", {"topic": "x"})
    assert msg.to == ENG and msg.service == "eng-brief"


def test_request_budget_defaults_to_the_contract_and_follows_the_reserve_rule(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief", budget=4)
    org.delegate(ROOT, "ceo", "Project", "g", "c", budget=5)
    work(org, "ceo")  # 1 run used: 4 left
    # 4 left, 1 reserved for the result of this request: 3 can be handed down, the contract wants 4
    with pytest.raises(OrgError, match="not enough budget.*at most 3"):
        org.request("ceo", "eng-brief", {"topic": "x"})
    msg = org.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    assert msg.budget == 3 and org.budget("ceo") == 1
    define(org, name="plain", description="d")  # root has no limit: the contract budget is used as is
    root_msg = org.request(ROOT, "plain", {"topic": "y"})
    assert root_msg.budget == 10
    with pytest.raises(OrgError, match="at least 1"):
        org.request(ROOT, "plain", {"topic": "y"}, budget=0)


def test_request_revises_must_be_an_earlier_request_of_the_same_service(svc):
    org = svc
    first = request(org)
    plain = org.delegate(ROOT, "ceo", "Other", "g", "c", budget=2)
    with pytest.raises(OrgError, match="revises must be"):
        request(org, revises=plain.id)  # not a request of this service
    with pytest.raises(OrgError, match="revises must be"):
        request(org, revises="nope")
    rework = request(org, revises=first.id)
    assert rework.revises == first.id and rework.service == "weekly-brief"


def test_delegate_revises_a_plain_task_and_request_sends_a_service_request_back_inside_its_case(org):
    define(org, playbook="v1 steps.")
    first = request(org)
    deliver(org, "ceo", first)
    with pytest.raises(OrgError, match="^refused: .* is a request for the service `weekly-brief`: send it back with request\\(service="):
        org.delegate(ROOT, "ceo", "Fix it", "Add sources", "Every claim has a URL", budget=3, revises=first.id)  # P4-USE-REQUEST
    rework = request(org, revises=first.id, budget=3)
    assert (rework.service, rework.contract, rework.playbook, rework.revises) == ("weekly-brief", 1, 1, first.id)
    plain = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    assert plain.service is None and plain.contract is None and plain.playbook is None
    plain_rework = org.delegate(ROOT, "ceo", "Plain 2", "g", "c", budget=2, revises=plain.id)
    assert plain_rework.service is None
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert [t.id for t in case.tasks] == [first.id, rework.id] and case.reworks == 1


def test_old_messages_without_service_fields_parse_as_before(org):
    msg = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    stored = org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{msg.id}.md")
    assert stored.service is stored.contract is stored.playbook is stored.feedback is None
    assert "service" not in stored.meta() and "feedback" not in stored.meta()
    assert "service:" not in stored.render()


# ---------------------------------------------------------------------------------------------- report
def test_report_on_a_service_request_requires_lessons(svc):
    org = svc
    task = request(org)
    work(org, "ceo")
    for status in ("done", "failed", "blocked"):
        with pytest.raises(OrgError, match="request for service `weekly-brief`: pass `lessons`"):
            org.report("ceo", task.id, status, "Delivered.")
        with pytest.raises(OrgError, match="pass `lessons`"):
            org.report("ceo", task.id, status, "Delivered.", lessons="   ")
    with pytest.raises(OrgError, match="limit is 800"):
        org.report("ceo", task.id, "done", "Delivered.", lessons="x" * 801)
    blocked = org.report("ceo", task.id, "blocked", "Waiting for sources.", lessons="Sources were not provided.")
    assert lessons_of(blocked) == "Sources were not provided."  # required for blocked too
    org.write("ceo", "ceo/work/brief.md", "# Brief")
    final = org.report("ceo", task.id, "done", "Delivered.", ["ceo/work/brief.md"], lessons="Search first.\nTwo runs.")
    assert final.body.index("## Summary") < final.body.index("## Lessons") < final.body.index("## Artifacts")
    assert "## Lessons\nSearch first.\nTwo runs." in final.body
    assert lessons_of(final) == "Search first.\nTwo runs."


def test_lessons_are_optional_for_plain_tasks_and_kept_when_given(org):
    task = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    work(org, "ceo")
    res = org.report("ceo", task.id, "done", "Done.", lessons="Anyway.")
    assert "## Lessons\nAnyway." in res.body
    other = org.delegate(ROOT, "ceo", "Plain 2", "g", "c", budget=2)
    assert "## Lessons" not in org.report("ceo", other.id, "done", "Done.").body


# ---------------------------------------------------------------------------------------------- the base of a human rework (P4)
MEMO = "ceo/work/memo.md"
V1, V2 = "| Marta | 2026-10-14 |\n", "| Marta | none |\n"


def deliver_memo(org, task, text, lessons="Worked."):
    """The lead writes the memo and reports it as the artifact of ``task``."""
    path = org.dir("ceo") / "work" / "memo.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    work(org, "ceo")
    msg = org.report("ceo", task.id, "done", "Delivered.", artifacts=[str(path)], lessons=lessons)
    org.end_run("ceo", ok=True)
    return msg


def relayed_change(org):
    """The memo is delivered and rejected by the user; root's own rework (relayed) changes it. Returns (the first request, the relayed rework)."""
    first = request(org)
    deliver_memo(org, first, V1)
    org.feedback(ROOT, first.id, "reject", "Marta's date is wrong.", source="human")
    again = request(org, revises=first.id)  # no source: root's own reading
    deliver_memo(org, again, V2)
    return first, again


def needs_base(first, again):
    return (
        f"refused: since the delivery the client judged (task {first.id}, result {{result}}), relayed rework {again.id} (your own reading, not the "
        f"client's) changed {MEMO}. Say which version the user's corrections apply to: base=\"delivered\" (the lead restores the version they "
        "judged, then applies their corrections) or base=\"latest\" (the relayed changes stay; tell the user) (CLI: --base delivered or --base latest). "
        "Nothing was sent."
    )


def test_base_must_be_delivered_or_latest(svc):
    first, again = relayed_change(svc)
    sent = len(svc.sent(ROOT))
    for bad in ("both", "", "Delivered"):
        with pytest.raises(OrgError) as e:
            request(svc, revises=first.id, source="human", base=bad)
        assert str(e.value) == f'refused: base must be "delivered" or "latest": {bad}. Nothing was sent.'
    assert len(svc.sent(ROOT)) == sent


def test_base_goes_only_with_a_human_rework_by_root(svc):
    where = (
        'refused: base goes only with a rework the user asked for: revises=<an earlier request of this service>, source="human" '
        "(CLI: --revises <task id> --source human). Nothing was sent."
    )
    first, again = relayed_change(svc)
    sent = len(svc.sent(ROOT))
    for kw in ({}, {"revises": first.id}, {"revises": first.id, "source": "relayed"}):
        with pytest.raises(OrgError) as e:
            request(svc, base="delivered", **kw)
        assert str(e.value) == where
    assert len(svc.sent(ROOT)) == sent


def test_a_human_rework_after_relayed_changes_needs_a_base(svc):
    first, again = relayed_change(svc)
    sent = len(svc.sent(ROOT))
    result = max(r.id for r in svc.messages(ROOT, "read", "inbox") if r.type == "result" and r.reply_to == first.id)
    with pytest.raises(OrgError) as e:
        request(svc, revises=first.id, source="human")
    assert str(e.value) == needs_base(first, again).format(result=result)
    assert len(svc.sent(ROOT)) == sent  # nothing was sent
    kept = request(svc, revises=first.id, source="human", base="latest")
    assert kept.source == "human" and kept.body.endswith("Keep those changes unless this request says otherwise.")
    judged = request(svc, revises=first.id, source="human", base="delivered")
    assert judged.source == "human" and "## Base: the version the client judged" in judged.body


def test_a_base_when_none_is_needed_changes_nothing(svc):
    first = request(svc)
    deliver_memo(svc, first, V1)
    svc.feedback(ROOT, first.id, "reject", "No.", source="human")
    plain = request(svc, revises=first.id, source="human")  # no relayed rework: no base needed
    assert "## Base: " not in plain.body
    plain_with_base = request(svc, revises=first.id, source="human", base="delivered")
    assert plain_with_base.body == plain.body and plain_with_base.source == "human"


# ------------------------------------------------------------------------------ the default budget of a rework the user asked for (D-E5-1, 4.5)
from pathlib import Path  # noqa: E402

from hirearchy.kernel import OrgError as KernelOrgError  # noqa: E402
from hirearchy.services.testing import FixedAllowance, fs_world, memory_world  # noqa: E402

from . import _support as sup  # noqa: E402


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def allowed(request, tmp_path: Path):
    """A services world whose requester asks a ``FixedAllowance`` (``answers``: revised task -> what is left), the service defined (contract 10)."""
    allowance = FixedAllowance()
    w = sup.populated(request.param(tmp_path, allowance=allowance))
    sup.define(w)
    return w, allowance


def ask_first(w):
    return w.commands.request("root", "weekly-brief", {"topic": "ai"})


def user_rework(w, first, **kw):
    """The rework the user asked for: root sends the request back with ``source="human"``."""
    return w.commands.request("root", "weekly-brief", {"topic": "ai"}, revises=first.id, source="human", **kw)


@pytest.mark.parametrize(("left", "budget"), [(6, 6), (10, 10), (25, 10), (1, 1), (0, 1), (-3, 1)])
def test_a_rework_the_user_asked_for_gets_what_is_left_at_most_the_contracts_and_one_when_nothing_is_left(allowed, left, budget):
    """4.5: ``min(left, contract)`` when ``left >= 1``; the contract's budget above it; 1 run (the minimum a task carries) when nothing is left, and
    nothing is refused."""
    w, allowance = allowed
    first = ask_first(w)
    allowance.answers[first.id] = left
    assert user_rework(w, first).budget == budget
    assert allowance.asked == [("ceo", "weekly-brief", first.id)]


def test_a_rework_with_no_answer_about_its_case_gets_the_contracts_budget(allowed):
    w, allowance = allowed
    first = ask_first(w)  # the allowance has no answer for this task: it is in no case it knows
    assert user_rework(w, first).budget == 10 and allowance.asked == [("ceo", "weekly-brief", first.id)]


@pytest.mark.parametrize("error", [KernelOrgError("a mailbox cannot be read"), OSError("a run log directory cannot be read")], ids=["OrgError", "OSError"])
def test_a_record_that_cannot_be_read_gives_the_contracts_budget_and_refuses_nothing(allowed, error):
    w, allowance = allowed
    first = ask_first(w)
    allowance.error = error
    assert user_rework(w, first).budget == 10


@pytest.mark.parametrize("source", [None, "relayed"], ids=["no source (relayed by default)", "relayed"])
def test_a_relayed_rework_keeps_the_contracts_budget_and_is_never_asked(allowed, source):
    w, allowance = allowed
    first = ask_first(w)
    allowance.answers[first.id] = 3
    again = w.commands.request("root", "weekly-brief", {"topic": "ai"}, revises=first.id, source=source)
    assert again.budget == 10 and allowance.asked == []


def test_an_agents_rework_keeps_the_contracts_budget_and_is_never_asked(allowed):
    w, allowance = allowed
    sup.grant(w, "ceo", 60)
    sup.define(w, owner="ceo/eng", name="inner", actor="ceo", budget=4)
    first = w.commands.request("ceo", "inner", {"topic": "x"})
    allowance.answers[first.id] = 1
    again = w.commands.request("ceo", "inner", {"topic": "x"}, revises=first.id)
    assert again.budget == 4 and allowance.asked == []


def test_a_fresh_request_keeps_the_contracts_budget_and_is_never_asked(allowed):
    w, allowance = allowed
    assert ask_first(w).budget == 10 and ask_first(w).budget == 10 and allowance.asked == []


def test_an_explicit_budget_is_kept_and_never_asked(allowed):
    w, allowance = allowed
    first = ask_first(w)
    allowance.answers[first.id] = 2
    assert user_rework(w, first, budget=7).budget == 7 and allowance.asked == []


def test_an_explicit_budget_of_zero_is_refused_before_a_wrong_revises(allowed):
    """The precedence of the refusals is unchanged: the explicit budget is checked first."""
    w, allowance = allowed
    with pytest.raises(KernelOrgError, match="a request needs a budget of at least 1 run"):
        w.commands.request("root", "weekly-brief", {"topic": "ai"}, revises="20260101T000000000001-root-0000", source="human", budget=0)
    assert allowance.asked == []


def test_the_refusals_of_revises_and_base_still_come_before_the_default_is_computed(allowed):
    w, allowance = allowed
    first = ask_first(w)
    with pytest.raises(KernelOrgError, match="revises must be the id of an earlier request"):
        user_rework(w, type(first)(sender="root", to="ceo", type="task", body="", id="20260101T000000000001-root-0000"))
    with pytest.raises(KernelOrgError, match="base must be"):
        user_rework(w, first, base="oops")
    with pytest.raises(KernelOrgError, match="base goes only with a rework the user asked for"):
        w.commands.request("root", "weekly-brief", {"topic": "ai"}, base="latest")
    assert allowance.asked == []


# ------------------------------------------------------------------------------ REQUEST-UNANSWERED: a new request waits for the answers (clause 2, design 13.1)
from hirearchy.services import AmendmentBasis, Rejection  # noqa: E402
from hirearchy.services.testing import AdmittingServiceEvidence  # noqa: E402

OLD_NOTE = "20000101T000000000000-root-0001"  # recorded long before any request of the test
NEW_NOTE = "29990101T000000000000-root-0001"  # recorded after every request of the test
QUESTION = 'About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.'


class BasisEvidence(AdmittingServiceEvidence):
    """The admitting stand-in whose record a test sets (``basis``) or makes unreadable (``error``)."""

    def __init__(self) -> None:
        super().__init__()
        self.basis = AmendmentBasis((), ())
        self.error: Exception | None = None

    def amendment_basis(self, owner: str, service: str) -> AmendmentBasis:
        if self.error is not None:
            raise self.error
        return self.basis


def held(note: str, assertion: str = "R1", task: str = "20260101T000000000001-root-0001", answered: str = "") -> Rejection:
    return Rejection(note, assertion, task, "weekly-brief: ai", (), "Too long.", answered, QUESTION, task)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def gated(request, tmp_path: Path):
    """A services world whose requester asks a ``BasisEvidence`` (the record the test sets), the service defined."""
    evidence = BasisEvidence()
    w = sup.populated(request.param(tmp_path, evidence=evidence))
    sup.define(w)
    return w, evidence


def unanswered_text(note: str, assertion: str, task: str, more: str = "", question: str = QUESTION) -> str:
    """REQUEST-UNANSWERED (design 13.1), written out here word for word, for ``weekly-brief`` of ``ceo``."""
    return (
        f"refused: rejection {assertion} (message {note}) on task {task} of `weekly-brief` has no recorded answer yet{more}, so the next request of "
        "`weekly-brief` waits: every rejection gets the user's answer within one request. "
        f"Ask the user the one question first: {question.removesuffix('.')}. On yes: "  # the question ends with its own full stop: one is kept
        'define_service(owner="ceo", name="weekly-brief", ..., answers="' + note + '", about=<the id you asked about>, words=<their answer, verbatim>) '
        "(CLI: hirearchy define-service ... --answers, --about, --words). "
        'On no, a one-off or "as it is": feedback(task_id="' + task + '", verdict="reject", confirms="' + note + '", criterion=["none"], '
        '["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>) '
        "(CLI: hirearchy feedback <task> reject --confirms ... --criterion ... --source human --note ...). "
        "A rework of that case (revises=) is not held. Nothing was sent."
    )


def rejected_first(org):
    """The user rejects the delivery of the first request, and nobody has answered: returns (the request, the rejection note)."""
    first = request(org)
    deliver(org, "ceo", first)
    return first, org.feedback(ROOT, first.id, "reject", "Too long.", source="human")


def test_a_new_request_is_refused_while_a_human_rejection_since_the_previous_new_request_has_no_answer(svc):
    first, no = rejected_first(svc)
    sent = len(svc.sent(ROOT))
    with pytest.raises(OrgError, match="^refused: rejection R1 .* has no recorded answer yet, so the next request of `weekly-brief` waits"):
        request(svc, "next")
    assert len(svc.sent(ROOT)) == sent  # nothing was sent
    svc.feedback(ROOT, first.id, "reject", "No: a one-off.", source="human", confirms=no.id, criterion=["none"])  # the user's answer
    assert request(svc, "next").type == "task"


def test_the_refusal_is_request_unanswered_word_for_word(svc):
    first, no = rejected_first(svc)
    with pytest.raises(OrgError) as refusal:
        request(svc, "next")
    assert str(refusal.value) == unanswered_text(no.id, "R1", first.id)


def test_several_unanswered_name_the_oldest_then_and_k_more(svc):
    first, one = rejected_first(svc)
    again = request(svc, revises=first.id, source="human")  # a rework is never held
    deliver(svc, "ceo", again)
    svc.feedback(ROOT, again.id, "reject", "Still too long.", source="human")
    with pytest.raises(OrgError) as refusal:
        request(svc, "next")
    assert str(refusal.value) == unanswered_text(one.id, "R1", first.id, more=" (and 1 more: R2)")
    three_task = request(svc, revises=again.id, source="human")
    deliver(svc, "ceo", three_task)
    svc.feedback(ROOT, three_task.id, "reject", "Again.", source="human")
    with pytest.raises(OrgError, match=r"has no recorded answer yet \(and 2 more: R2, R3\), so the next request"):
        request(svc, "next")


def test_an_unreadable_record_refuses_with_request_unreadable(gated):
    w, evidence = gated
    ask_first(w)
    evidence.error = KernelOrgError("a mailbox cannot be read")
    sent = len(w.d.mail.sent("root"))
    with pytest.raises(KernelOrgError) as refusal:
        ask_first(w)
    assert str(refusal.value) == (
        "refused: the record of `weekly-brief` cannot be read (a mailbox cannot be read), so the request was not sent. "
        "Try again; if it persists, tell the user."
    )
    assert len(w.d.mail.sent("root")) == sent
    evidence.error = OSError("disk")
    with pytest.raises(KernelOrgError, match=r"cannot be read \(disk\)"):
        ask_first(w)


# guards: they pin the edges of 13.1 and are green when written
def test_a_rework_is_never_held(svc):
    first, no = rejected_first(svc)
    rework = request(svc, revises=first.id, source="human")
    assert rework.revises == first.id
    assert request(svc, revises=first.id).revises == first.id  # a relayed rework too


def test_a_rejection_before_the_previous_new_request_is_not_due(gated):
    w, evidence = gated
    ask_first(w)
    evidence.basis = AmendmentBasis((held(OLD_NOTE),), ())  # an older backlog: recorded before the previous new request
    assert ask_first(w).type == "task"


def test_no_earlier_new_request_means_nothing_is_due(gated):
    w, evidence = gated
    evidence.basis = AmendmentBasis((held(NEW_NOTE),), ())
    assert ask_first(w).type == "task"  # the first new request of the service: nothing is due
    first = w.d.mail.sent("root")[-1]
    assert w.commands.request("root", "weekly-brief", {"topic": "ai"}, revises=first.id, source="human").revises == first.id


def test_relayed_and_agent_rejections_hold_nothing(svc):
    first = request(svc)
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "The assistant's reading.", source="relayed")
    svc.feedback(ROOT, first.id, "reject", "Without a source.")
    assert request(svc, "next").type == "task"  # relayed rejections are not assertions
    define(svc, owner=ENG, actor="ceo", name="eng-brief", budget=4)
    svc.delegate(ROOT, "ceo", "Project", "g", "c", budget=20)
    inner = svc.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    deliver(svc, ENG, inner)
    svc.feedback("ceo", inner.id, "reject", "Not good.")
    assert svc.request("ceo", "eng-brief", {"topic": "y"}, budget=3).type == "task"  # an agent client's rejection is agent tier


def test_an_answer_by_human_link_or_by_answering_version_releases_the_request(svc):
    first, no = rejected_first(svc)
    svc.feedback(ROOT, first.id, "reject", "No: a one-off.", source="human", confirms=no.id, criterion=["none"])  # the user's "no": a human link
    second = request(svc, "second")
    deliver(svc, "ceo", second)
    no2 = svc.feedback(ROOT, second.id, "reject", "Missing a source.", source="human")
    svc.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=["Always name a source"], answers=no2.id, about="C1", words="Yes, add it.")
    assert request(svc, "third").type == "task"  # the answer is a contract version (and its link)
