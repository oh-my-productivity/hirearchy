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


# ------------------------------------------------------------------------------------------ 14.3: the items and the watch in root's listing
# These tests build ``TextServiceReports`` over a ``ReflectionWorld`` with a stand-in for the watch (``evidence``), so that each state is one value of
# ``ItemWatch`` and not a story of verdicts (the stories are FEAT-010's). The listing carries ids and counts only, never an item's words.
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from hirearchy.kernel import OrgError  # noqa: E402
from hirearchy.reflection._reports import TextServiceReports  # noqa: E402
from hirearchy.reflection.testing import ReflectionWorld, fs_world  # noqa: E402
from hirearchy.services import ItemWatch  # noqa: E402
from hirearchy.services.testing import AdmittingServiceEvidence, ServiceEvidence  # noqa: E402

from . import _support as sup  # noqa: E402


@pytest.fixture
def pw(tmp_path: Path) -> ReflectionWorld:
    """A world where ``ceo`` owns ``weekly-brief`` with playbook v1 (``first``: P1-P3, steps under ``## Steps``)."""
    w = sup.populated(fs_world(tmp_path))
    sup.define(w)
    sup.first_playbook(w, sup.STEPS)
    return w


class FailingWatch(AdmittingServiceEvidence):
    """The watch that cannot read the record."""

    def watch(self, owner, service):
        raise OrgError("the mailbox of root cannot be read")


def another_world(tmp_path: Path, name: str) -> ReflectionWorld:
    """A second organization under ``tmp_path`` with ``ceo`` and the service defined (no playbook)."""
    (tmp_path / name).mkdir()
    w = sup.populated(fs_world(tmp_path / name))
    sup.define(w)
    return w


def listing(w, watch=(), *, evidence: ServiceEvidence | None = None, actor: str = "root") -> str:
    evidence = evidence or AdmittingServiceEvidence(watch=watch)
    return TextServiceReports(w.s.d.agents, w.s.catalog, w.history, w.paths, evidence).services_text(actor)


def playbook_line(text: str, service: str = "weekly-brief") -> str:
    block = text.split(f"- {service} (")[1]
    return next(x for x in block.splitlines() if x.startswith("  playbook v"))


def add_rules(w, *, n: int = 2) -> None:
    for k in range(n):
        w.s.commands.revise_playbook("ceo", sup.SERVICE, "add", "a rule", ["R1"], kind="rule", when=f"case {k} comes up", then=f"handle case {k}")


def test_the_playbook_line_gains_items_rules_and_the_watched_items(pw):
    add_rules(pw)
    watch = [
        ItemWatch("P1", "step", "kept", 1), ItemWatch("P2", "step", "kept", 1),
        ItemWatch("P3", "step", "warning", 1, related=("R4",)),
        ItemWatch("P4", "rule", "new", 2, k=3, clean=1, waiting=1),
        ItemWatch("P5", "rule", "kept", 3),
    ]
    for who in ("root", "ceo"):  # the same builder for the client and for the owner
        line = playbook_line(listing(pw, watch, actor=who))
        assert line.startswith('  playbook v3 (') and '"' in line
        assert line.endswith(
            '; 5 items (2 rules); watched: P3 warning (R4; the next related rejection retires it), '
            "P4 new (1 of 3 clean cases, k 3; waiting for the client's verdict on 1 case)"
        )
    text = listing(pw, watch)
    assert "handle case 0" not in text and "case 1 comes up" not in text  # ids and counts only: no item's words


def test_none_watched_free_text_not_in_item_form_and_no_items(pw, tmp_path):
    kept = [ItemWatch(i, "step", "kept", 1) for i in ("P1", "P2", "P3")]
    assert playbook_line(listing(pw, kept)).endswith("; 3 items (0 rules), none watched")
    assert playbook_line(listing(pw, ())).endswith("; 3 items (0 rules), none watched")  # a watch of nothing: nothing is watched
    one = another_world(tmp_path, "one")
    sup.first_playbook(one, "## Steps\n1. Only step.")
    assert playbook_line(listing(one)).endswith("; 1 item (0 rules), none watched")
    # a retired item is not watched either
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "retire", "not needed", [], item="P2")
    assert playbook_line(listing(pw, [ItemWatch("P2", "step", "retired", 1), *kept])).endswith("; 2 items (0 rules), none watched")

    legacy = another_world(tmp_path, "legacy")
    sup.legacy_playbook(legacy, "## Steps\n1. Search.\n2. Write.")
    assert playbook_line(listing(legacy)).endswith("; free text (items when the owner first changes one)")

    broken = another_world(tmp_path, "broken")
    meta = {"service": sup.SERVICE, "version": 1, "revised": "2026-01-15T10:00:00+00:00", "by": "ceo", "reason": "x", "items_max": 1, "rules": [], "why": {}, "op": "first"}
    broken.s.store.write_playbook("ceo", sup.SERVICE, 1, meta, "not an item at all\n", None)
    line = playbook_line(listing(broken))
    assert "; not in item form (line 1: " in line and line.endswith("): it becomes items at the owner's next change")

    empty = another_world(tmp_path, "empty")
    sup.first_playbook(empty, "## Steps\n1. Only step.")
    empty.s.commands.revise_playbook("ceo", sup.SERVICE, "retire", "not needed", [], item="P1")
    assert playbook_line(listing(empty)).endswith("; no items")

    bare = another_world(tmp_path, "bare")
    assert "  playbook: none yet" in listing(bare)  # no playbook, no suffix


def test_waiting_and_the_next_related_rejection_retires_it(pw):
    watch = [
        ItemWatch("P1", "step", "new", 1, k=3, clean=0, waiting=2, pending=("R5", "R6")),
        ItemWatch("P2", "step", "new", 1, k=3, clean=2, carried="P9"),
        ItemWatch("P3", "step", "warning", 1, related=("R4", "R6"), retire_due=True),
    ]
    assert playbook_line(listing(pw, watch)).endswith(
        "; 3 items (0 rules); watched: "
        "P1 new (0 of 3 clean cases, k 3; waiting for the client's verdict on 2 cases; waiting for the user's answer to R5, R6), "
        "P2 new (2 of 3 clean cases, k 3; carried from P9), "
        "P3 warning (R4, R6; retire due)"
    )
    one = [ItemWatch("P1", "step", "warning", 1, related=("R4",)), ItemWatch("P2", "step", "restored", 3, restores=1)]
    line = playbook_line(listing(pw, one))
    assert "watched: P1 warning (R4; the next related rejection retires it)" in line and "P2" not in line  # a restored text is not in its watch


def test_watch_not_read_and_the_listing_goes_on(pw):
    sup.define(pw, name="second")
    pw.s.commands.revise_playbook("ceo", "second", "first", "first", [], text="## Steps\n1. Do it.")
    out = listing(pw, evidence=FailingWatch())
    assert playbook_line(out).endswith("; watch not read (the mailbox of root cannot be read)")
    assert playbook_line(out, "second").endswith("; watch not read (the mailbox of root cannot be read)")  # every listed service reads its own watch
    assert out.count("  record: no requests yet") == 2 and "playbook file:" not in out.split("Services you offer:")[0]  # the rest of the listing is whole


def rejected_world(w):
    """The client's request is delivered and rejected (R1) in ``w``; returns the request."""
    task = sup.ask(w)
    sup.deliver(w, task, lessons="L.")
    sup.rate(w, task, "reject", "Too long.")
    return task


def assertion_block(out):
    return out.split("  regression list (the client's rejections):\n")[1].split("\n  playbook")[0].splitlines()


def test_the_regression_line_names_the_rules_citing_it(pw, tmp_path):
    task = rejected_world(pw)
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "add", "from R1", ["R1"], kind="rule", when="it runs long", then="cut it")
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "add", "from R1 too", ["R1"], kind="rule", when="it runs longer", then="cut it again")
    assert assertion_block(listing(pw)) == [f'    R1 (case {task.id}): "Too long." (rules citing it: P4, P5)']
    assert assertion_block(listing(pw, actor="ceo")) == [f'    R1 (case {task.id}): "Too long." (rules citing it: P4, P5)']
    steps = another_world(tmp_path, "steps")
    sup.first_playbook(steps, sup.STEPS)
    rejected_world(steps)
    steps.s.commands.revise_playbook("ceo", sup.SERVICE, "add", "a step from R1", ["R1"], kind="step", text="Cut it.")
    assert assertion_block(listing(steps))[0].endswith('"Too long." (items citing it: P4)')  # a step cites too: the label does not call it a rule
    plain = another_world(tmp_path, "plain")
    sup.first_playbook(plain, sup.STEPS)
    rejected_world(plain)
    assert "citing it" not in listing(plain)  # no item cites R1
