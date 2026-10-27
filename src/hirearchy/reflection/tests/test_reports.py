# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.services_world import amend_legacy, svc


def test_status_tree_names_the_services_an_agent_offers(svc):
    tree = svc.tree()
    assert "ceo [Chief executive]" in tree and " services: weekly-brief" in tree.split("\n")[1]
    assert "services:" not in tree.split("\n")[2]


def test_the_services_listing_shows_criteria_by_id(svc):
    from testkit.reach.hirearchy.core import ROOT

    amend_legacy(svc, add_acceptance=["Never longer than one page"], remove_acceptance=["At most 600 words"])
    for who in (ROOT, "ceo"):
        out = svc.runtime.service_reports.services_text(who)
        assert "    C2: Every factual claim has a source URL\n    C3: Never longer than one page (amendment, not confirmed)\n  record:" in out
        assert "C1" not in out and "1. " not in out.split("record:")[0]  # the removed C1 is not listed, and nothing is numbered by position


def reject(svc, words, topic="ai", **kw):
    """The user rejects a delivery (their own judgement); returns the request and the verdict note. A ``criterion`` is the user's yes: it is
    recorded as a ``confirms`` link after the verdict."""
    from testkit.services_world import deliver
    from testkit.services_world import request_unheld as request  # a new request that clause 2 would hold: these tests are about other rules

    task = request(svc, topic)
    deliver(svc, "ceo", task, lessons="L.")
    criterion = kw.pop("criterion", None)
    note = svc.feedback(ROOT_ADDR, task.id, "reject", words, source="human", **kw)
    if criterion:  # the user's yes to what it was about: a `confirms` link (a criterion on the rejection itself is not the client's)
        svc.feedback(ROOT_ADDR, task.id, "reject", "Yes, it is about that.", source="human", criterion=criterion, confirms=note.id)
    return task, note


ROOT_ADDR = "root"


def assertion_lines(out):
    return out.split("  regression list (the client's rejections):\n")[1].split("\n  playbook")[0].splitlines()


def test_a_service_without_a_rejection_lists_no_regressions(svc):
    assert "regression list" not in svc.runtime.service_reports.services_text("root")


def test_the_services_listing_lists_every_assertion_clipped_to_160(svc):
    first, note = reject(svc, "w " * 100)
    for k in range(12):
        reject(svc, f"Problem {k + 2}.", f"t{k}")
    for who in ("root", "ceo"):
        out = svc.runtime.service_reports.services_text(who)
        assert out.split("record:")[1].split("\n")[1] == "  regression list (the client's rejections):"
        lines = assertion_lines(out)
        assert len(lines) == 13 and lines[0].startswith(f'    R1 (case {first.id}): "w w w ')
        assert lines[0].endswith('w…"') and len(lines[0].split(': "')[1]) == 160 + 1  # 159 characters, the ellipsis, the closing quote
        assert lines[-1].endswith('"Problem 13."') and lines[-1].startswith("    R13 (case ")


def test_the_services_listing_says_what_each_assertion_is_about(svc):
    from testkit.services_world import deliver
    from testkit.services_world import request_unheld as request  # a new request that clause 2 would hold: this test is about the listing

    a, one = reject(svc, "One.", criterion=["C1", "C2"])
    b, two = reject(svc, "Two.", "b", criterion=["none"])
    c, three = reject(svc, "Three.", "c")
    d, four = reject(svc, "Four.", "d")
    svc.feedback("root", d.id, "reject", "Probably.", source="relayed", criterion=["C1"], confirms=four.id)
    e, five = reject(svc, "Five.", "e")
    svc.feedback("root", e.id, "reject", "Probably.", source="relayed", criterion=["none"], confirms=five.id)
    f = request(svc, "f")
    deliver(svc, "ceo", f, lessons="L.")
    svc.feedback("root", f.id, "reject", "Six.", source="human", criterion=["C2"])  # a criterion on the rejection itself: not the client's yes
    assert assertion_lines(svc.runtime.service_reports.services_text("root")) == [
        f'    R1 (case {a.id}, about C1, C2): "One."',
        f'    R2 (case {b.id}, no lasting rule): "Two."',
        f'    R3 (case {c.id}): "Three."',
        f'    R4 (case {d.id}, about C1 (not confirmed)): "Four."',
        f'    R5 (case {e.id}, possibly a one-off (not confirmed)): "Five."',
        f'    R6 (case {f.id}, about C2 (not confirmed)): "Six."',
    ]


def test_an_unconfirmed_amendment_is_marked_in_the_listing(svc):
    from testkit.reach.hirearchy.core import ROOT

    amend_legacy(svc, add_acceptance=["One page", "Names its week"])
    _, no = reject(svc, "No week.")
    svc.feedback(ROOT, no.reply_to, "reject", "Yes, add it.", source="human", criterion=["C4"], confirms=no.id)
    out = svc.runtime.service_reports.services_text("root")
    assert "    C3: One page (amendment, not confirmed)\n" in out and "    C4: Names its week\n" in out  # the client's yes unmarks C4
    assert "    C1: At most 600 words\n" in out  # a v1 criterion was never an amendment


def test_a_user_initiated_amendment_is_marked_never_admits_a_playbook_revision(svc):
    from testkit.reach.hirearchy.core import ROOT
    from testkit.services_world import write_version

    write_version(svc, 2, ["At most 600 words", "Every factual claim has a source URL", "One page"], initiated="user", words="Keep it to one page.")
    out = svc.runtime.service_reports.services_text("root")
    assert "    C3: One page (amendment, user-initiated: never admits a playbook revision)\n" in out
    _, no = reject(svc, "Too long.")
    svc.feedback(ROOT, no.reply_to, "reject", "Yes.", source="human", criterion=["C3"], confirms=no.id)  # a human link names it: still never admitted
    out = svc.runtime.service_reports.services_text("ceo")
    assert "    C3: One page (amendment, user-initiated: never admits a playbook revision)\n" in out
    assert "not confirmed)\n    C" not in out and "C3: One page (amendment, not confirmed)" not in out


def test_the_services_listing_marks_a_removed_criterion(svc):
    first, note = reject(svc, "Too long.", criterion=["C1", "C2"])
    amend_legacy(svc, add_acceptance=["One page"], remove_acceptance=["Every factual claim has a source URL"])
    assert assertion_lines(svc.runtime.service_reports.services_text("root")) == [
        f'    R1 (case {first.id}, about C1, C2 (removed)): "Too long."'
    ]


def test_case_total_warns_on_spend_not_on_runs_handed_down(svc):
    """Rule R (design 13): the rework is the user's (``source="human"``); a relayed default would be named apart and called the assistant's spend."""
    from testkit.services_world import deliver, request

    first = request(svc, "ai")  # the contract hands down 10
    deliver(svc, "ceo", first, runs=3)
    svc.feedback(ROOT_ADDR, first.id, "reject", "Too long.", source="human")
    from testkit.services_world import request_unheld  # a new request that clause 2 would hold: this test is about the case total
    rework = svc.request(ROOT_ADDR, "weekly-brief", {"topic": "ai"}, revises=first.id, budget=8, source="human")  # 18 handed down: past the contract's 10
    deliver(svc, "ceo", rework, runs=4)  # but 7 runs used
    done = svc.runtime.service_reports.case_total(rework)
    assert done == "case total: 7 runs used of 18 handed down (contract: 10 per request)"
    over = request_unheld(svc, "other")
    deliver(svc, "ceo", over, runs=11)  # more used than the contract allows
    assert svc.runtime.service_reports.case_total(over) == (
        "case total: 11 runs used of 10 handed down (contract: 10 per request). "
        "This case now exceeds the per-request budget of 10: tell the user."
    )


def test_case_total_with_one_credited_run_does_not_say_exceeds(svc):
    from testkit.services_world import deliver, request

    from hirearchy.kernel import RUNTIME, Message, run_credit_title

    over = request(svc, "other")
    deliver(svc, "ceo", over, runs=11)  # 11 run logs: more than the 10 the contract allows
    assert "exceeds" in svc.runtime.service_reports.case_total(over)
    throttled = svc.runtime.run_log_reader.files("ceo")[-1].stem  # one of them ended on a model-service throttle and was not charged
    svc.runtime.delivery.deliver(Message(sender=RUNTIME, to="ceo", type="note", budget=1, wake=False, title=run_credit_title("ceo", throttled), body="returned"))
    assert svc.runtime.service_reports.case_total(over) == "case total: 10 runs used of 10 handed down (contract: 10 per request)"


# ------------------------------------------------------------------ D-E5-1 and DR-0a3-1 over the Org facade
def test_a_relayed_rework_just_sent_says_it_has_used_no_run_yet(svc):
    """DR-0a3-1: R alone and just sent (no run in its interval, nothing after it): form 1 and RELAYED_NONE_YET, never "0 by your relayed rework"."""
    from testkit.services_world import deliver, request

    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=3)
    relayed = svc.request(ROOT_ADDR, "weekly-brief", {"topic": "ai"}, revises=first.id, budget=6)  # root's rework without a source is relayed
    total = svc.runtime.service_reports.case_total(relayed)
    assert total == (
        "case total: 3 runs used of 16 handed down (contract: 10 per request). "
        f"Your relayed rework {relayed.id} has used no run yet; its runs will be your own spend, not the user's: report them to the user as yours, "
        "and never ask the user to fund them."
    )
    assert "by your relayed rework" not in total


def test_a_relayed_rework_answered_with_its_whole_budget_before_the_next_request_still_says_none_yet(svc):
    """DR-0a3-1: R (6) answers with 6 back and no run before H is sent; H's 4 runs are the user's: RELAYED_NONE_YET."""
    from testkit.services_world import deliver, request, work

    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=1)
    relayed = svc.request(ROOT_ADDR, "weekly-brief", {"topic": "ai"}, revises=first.id, budget=6)
    deliver(svc, "ceo", relayed, runs=0)  # the runtime hands the whole 6 back with the result
    human = svc.request(ROOT_ADDR, "weekly-brief", {"topic": "ai"}, revises=relayed.id, source="human", budget=10)  # the contract's, as before 0a.3 (Rule B)
    work(svc, "ceo", 4)
    total = svc.runtime.service_reports.case_total(human)
    assert f"Your relayed rework {relayed.id} has used no run yet; its runs will be your own spend" in total
    assert "no run counted apart" not in total


def test_a_relayed_rework_followed_by_the_users_request_before_it_ran_says_its_runs_could_not_be_split(svc):
    """DR-0a3-1: R (6) is followed by H before any run and has no result; 4 runs fall in H's interval. Form 1 and RELAYED_UNSPLIT with
    "4 run(s)", never "has used no run yet"."""
    from testkit.services_world import deliver, request, work

    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=1)
    relayed = svc.request(ROOT_ADDR, "weekly-brief", {"topic": "ai"}, revises=first.id, budget=6)
    human = svc.request(ROOT_ADDR, "weekly-brief", {"topic": "ai"}, revises=relayed.id, source="human", budget=10)  # the contract's, as before 0a.3 (Rule B)
    work(svc, "ceo", 4)
    total = svc.runtime.service_reports.case_total(human)
    assert total == (
        "case total: 5 runs used of 26 handed down (contract: 10 per request). "
        f"Your relayed rework {relayed.id} has no run counted apart: a request of the user's followed before it finished, so its runs could not be "
        "split from the user's interval, which holds 4 run(s) since then, all counted with the user's requests. Its runs are your own spend, not "
        "the user's: report them to the user as yours, and never ask the user to fund them."
    )
    assert "has used no run yet" not in total
