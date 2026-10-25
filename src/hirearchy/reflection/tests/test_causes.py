"""``cause_of``, ``attribution`` and ``failure_class``: every escape gets a cause typed by rule, and one attribution (pure; design 5, 4.4).

Message ids start with a microsecond timestamp, so a larger number is a later id. The tests build the messages, the verdicts with their link notes
and the cases by hand, and take the assertions from ``regressions`` and the deliveries from ``deliveries_of``, so the rules run on the values the
product derives."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from hirearchy.kernel import Message, latest_results, link_ids, msg_time, verdict_tier
from hirearchy.reflection import (
    CAUSES, FAILURE_CLASSES, LASTING_WORDS, Assertion, Case, Cause, Delivery, Verdict, attribution, cause_of, deliveries_of, failure_class,
    regressions,
)
from hirearchy.services import BASE_DELIVERED_HEADING, BASE_LATEST_HEADING

OWNER = "ceo"
SHARED = "ceo/eng/work/memo.md"


def ident(n: int, sender: str = "ceo") -> str:
    """The id of the message sent ``n`` seconds after the origin (so ids order like ``n``)."""
    return f"20260101T00{n // 60:02d}{n % 60:02d}000000-{sender.replace('/', '-')}-{n:04d}"


def task(n: int, *, source: str | None = None, body: str = "b", contract: int | None = None, revises: str | None = None) -> Message:
    return Message(
        sender="root", to=OWNER, type="task", body=body, title=f"t{n}", id=ident(n, "root"), service="s", source=source, contract=contract, revises=revises,
    )


def done(for_task: Message, n: int, *artifacts: str) -> Message:
    body = "Delivered." + ("\n\n## Artifacts\n" + "\n".join(f"- {a}" for a in artifacts) if artifacts else "")
    return Message(sender=OWNER, to="root", type="result", body=body, id=ident(n), reply_to=for_task.id, status="done")


def rejection(
    on: Message, n: int, *, links: tuple[str, ...] = (), link_source: str | None = "human", words: str = "not good", kind: str = "reject",
) -> Verdict:
    """The verdict ``kind`` on ``on`` sent at second ``n``, with one link note naming ``links`` (source ``link_source``) sent a second later."""
    note = Message(sender="root", to=OWNER, type="note", body=words, id=ident(n, "root"), reply_to=on.id, feedback=kind, source="human")
    link_notes: list[Message] = []
    confirmed: tuple[str, ...] = ()
    tier = ""
    if links:
        link = Message(
            sender="root", to=OWNER, type="note", body="link", id=ident(n + 1, "root"), reply_to=note.id, criterion=", ".join(links), source=link_source,
        )
        link_notes.append(link)
        tier = verdict_tier(link)
        confirmed = tuple(x for x in link_ids(link) if x.startswith("C")) if tier == "human" else ()
    return Verdict(
        kind, words, msg_time(note), on.id, 0, note, tier="human", links=links, links_tier=tier, confirmed=confirmed, link_notes=tuple(link_notes),
    )


def case_of(tasks: list[Message], results: list[Message], *verdicts: Verdict, name: str = "") -> Case:
    state = results[-1].status or "open" if results else "open"
    return Case(
        id=name or tasks[0].id, service="s", owner=OWNER, tasks=tasks, result=results[-1] if results else None, state=state, playbook=0, used=0,
        reworks=len(tasks) - 1, budget=1, runs=1, lessons=[], verdicts=list(verdicts), started=None, finished=None,
    )


@dataclass
class Escape:
    """One escape: the case, its results, the delivery that was rejected, and its assertion."""

    case: Case
    results: dict[str, Message]
    delivery: Delivery
    assertion: Assertion

    def cause(
        self, carried: frozenset[str] | None = frozenset(), answer_removes: tuple[str, ...] = (), *,
        lasting: Sequence[str] = LASTING_WORDS, version: int | None = None, answering: int = 0,
    ) -> Cause:
        return cause_of(
            self.delivery, self.case, self.assertion, carried, answer_removes, self.results, lasting, version=version, answering=answering,
        )


def escape(
    *, relayed: bool = False, carry_over: bool = False, links: tuple[str, ...] = (), link_source: str | None = "human", words: str = "not good",
    base: str = "", before: bool = False, source: str | None = None, contract: int | None = None,
) -> Escape:
    """The head task ``T0`` is delivered at 10 and accepted at 20. With ``carry_over`` the assistant's relayed rework ``R`` (sent 30) delivers ``SHARED``
    at 40. The task ``T`` (sent 50, ``relayed`` or after ``base``) delivers ``SHARED`` at 60 and is rejected at 70 with ``links`` and ``words``; with
    ``before`` a relayed rework ``B`` (sent 62) is delivered at 65, between the delivery and the rejection."""
    t0 = task(1)
    tasks = [t0]
    finals = [done(t0, 10)]
    if carry_over:
        r = task(30, source="relayed", revises=t0.id)
        tasks.append(r)
        finals.append(done(r, 40, SHARED))
    t = task(50, source="relayed" if relayed else source, body=f"Rework.\n\n{base}\n" if base else "Rework.", revises=tasks[-1].id, contract=contract)
    tasks.append(t)
    finals.append(done(t, 60, SHARED))
    if before:
        b = task(62, source="relayed", revises=t.id)
        tasks.append(b)
        finals.append(done(b, 65, "other.md"))
    verdicts = [rejection(t0, 20, kind="accept"), rejection(t, 70, links=links, link_source=link_source, words=words)]
    c = case_of(tasks, finals, *verdicts)
    results = latest_results(finals)
    (assertion,) = regressions([c])
    delivery = next(d for d in deliveries_of(c, results, {}) if d.task.id == t.id)
    return Escape(c, results, delivery, assertion)


# ------------------------------------------------------------------------------------------------------------------------ the rules, one by one


def test_the_vocabularies_are_the_closed_ones() -> None:
    assert CAUSES == ("relayed-error", "relayed-carry-over", "contract-gap", "reviewer-miss", "untyped")
    assert FAILURE_CLASSES == ("wrong", "missing", "off_spec", "unusable", "out_of_authority", "process_skipped", "wasteful")
    assert LASTING_WORDS == ("always", "never", "from now on")


def test_rule_1_a_rejected_relayed_delivery_is_relayed_error() -> None:
    e = escape(relayed=True)
    cause = e.cause()
    assert (cause.type, cause.rule, cause.detail, cause.rules, cause.also) == ("relayed-error", "relayed task", (e.delivery.task.id,), ("relayed task",), ())


def test_rule_2_a_shared_artifact_after_the_judged_delivery_is_relayed_carry_over() -> None:
    e = escape(carry_over=True)
    relayed = e.case.tasks[1]
    cause = e.cause()
    assert (cause.type, cause.rule, cause.detail) == ("relayed-carry-over", "carry-over", (relayed.id, SHARED))


def test_rule_2_does_not_match_with_the_delivered_base_heading() -> None:
    e = escape(carry_over=True, base=BASE_DELIVERED_HEADING)  # the lead was told to restore the version the client judged
    assert e.cause().type == "untyped"


@pytest.mark.parametrize("base", ["", BASE_LATEST_HEADING])
def test_rule_2_matches_with_the_latest_base_heading_or_no_base(base: str) -> None:
    assert escape(carry_over=True, base=base).cause().rule == "carry-over"


def test_rule_2_needs_the_relayed_rework_to_share_an_artifact() -> None:
    e = escape(carry_over=True)
    other = done(e.case.tasks[1], 40, "elsewhere.md")  # the relayed rework delivered another file
    results = {**e.results, e.case.tasks[1].id: other}
    assert cause_of(e.delivery, e.case, e.assertion, frozenset(), (), results).type == "untyped"


def test_rule_2_needs_the_relayed_rework_to_come_after_the_judged_delivery() -> None:
    t0 = task(1)
    r = task(5, source="relayed", revises=t0.id)  # sent before T0's delivery was judged (accepted at 20)... and answered before it
    t = task(50, revises=r.id)
    finals = [done(t0, 10, SHARED), done(r, 8, SHARED), done(t, 60, SHARED)]
    c = case_of([t0, r, t], finals, rejection(t0, 20, kind="accept"), rejection(t, 70))
    results = latest_results(finals)
    (a,) = regressions([c])
    d = next(x for x in deliveries_of(c, results, {}) if x.task.id == t.id)
    assert cause_of(d, c, a, frozenset(), (), results).type == "untyped"  # R (5) precedes the judged delivery's result (10)


def test_rule_3_a_carried_kept_named_criterion_is_reviewer_miss() -> None:
    e = escape(links=("C1",))
    cause = e.cause(frozenset({"C1", "C2"}))
    assert (cause.type, cause.rule, cause.detail, cause.rules, cause.also) == ("reviewer-miss", "link", (e.assertion.verdict.link_notes[0].id, "C1"), ("link",), ())


def test_rule_4_a_named_criterion_the_task_did_not_carry_is_contract_gap_by_answer() -> None:
    e = escape(links=("C9",))
    cause = e.cause(frozenset({"C1"}))
    assert (cause.type, cause.rule, cause.detail) == ("contract-gap", "answer", (e.assertion.verdict.link_notes[0].id, "C9"))


def test_rule_4_a_removal_only_answer_naming_a_carried_criterion_is_contract_gap_never_reviewer_miss() -> None:
    e = escape(links=("C6",))
    cause = e.cause(frozenset({"C6"}), ("C6",))  # C6 was carried, and the answering version takes it out of the contract
    assert (cause.type, cause.rule, cause.removes) == ("contract-gap", "answer", ("C6",))
    assert cause.rules == ("answer",)  # rule 3 does not match: the client did not say the criterion failed


def test_rule_5_a_lasting_word_is_contract_gap_by_words() -> None:
    e = escape(words="Always cite the source")
    cause = e.cause()
    assert (cause.type, cause.rule, cause.detail) == ("contract-gap", "words", ("always",))


def test_lasting_words_match_on_word_boundaries_and_phrases_in_any_case() -> None:
    assert escape(words="never mind the length").cause().detail == ("never",)
    assert escape(words="From Now On, three bullets").cause().detail == ("from now on",)
    assert escape(words="neverending story, the alwaysmore one").cause().type == "untyped"


def test_rule_6_nothing_matched_is_untyped() -> None:
    cause = escape().cause()
    assert (cause.type, cause.rule, cause.detail, cause.rules, cause.also) == ("untyped", "none", (), (), ())


def test_a_none_link_says_no_lasting_rule() -> None:
    cause = escape(links=("none",)).cause()
    assert (cause.type, cause.rule, cause.detail) == ("untyped", "none", ("the user said it is no lasting rule",))


# ------------------------------------------------------------------------------------------------------------------------ precedence, also, rules

RULE_NAMES = {"1": "relayed task", "2": "carry-over", "3": "link", "4": "answer", "5": "words"}
TYPE_OF = {"1": "relayed-error", "2": "relayed-carry-over", "3": "reviewer-miss", "4": "contract-gap", "5": "contract-gap"}


def with_rules(enabled: str) -> Escape:
    """A world in which exactly the rules named by the digits of ``enabled`` match (1 and 2 cannot match together: rule 2 needs a task that is not relayed)."""
    links = tuple(c for c, on in (("C1", "3" in enabled), ("C9", "4" in enabled)) if on)
    return escape(relayed="1" in enabled, carry_over="2" in enabled, links=links, words="Always cite" if "5" in enabled else "not good")


@pytest.mark.parametrize("enabled", ["13", "14", "15", "23", "24", "25", "34", "35", "45", "134", "245", "345", "1345", "2345"])
def test_every_precedence_pair_is_the_earlier_rule(enabled: str) -> None:
    cause = with_rules(enabled).cause(frozenset({"C1"}))
    matching = [RULE_NAMES[x] for x in enabled]
    assert cause.rule == matching[0] and cause.type == TYPE_OF[enabled[0]]
    assert cause.rules == tuple(matching)  # every rule that matches, the winner first


def test_a_mixed_link_is_reviewer_miss_with_contract_gap_in_also() -> None:
    e = escape(links=("C1", "C9"))  # C1 was carried and kept, C9 was not carried
    cause = e.cause(frozenset({"C1"}))
    assert (cause.type, cause.also, cause.rules, cause.detail[1:]) == ("reviewer-miss", ("contract-gap",), ("link", "answer"), ("C1",))


def test_also_lists_distinct_types_other_than_the_winner() -> None:
    cause = with_rules("2345").cause(frozenset({"C1"}))
    assert cause.type == "relayed-carry-over"
    assert cause.also == ("reviewer-miss", "contract-gap")  # contract-gap once, though rules 4 and 5 both match
    same = with_rules("45").cause(frozenset({"C1"}))
    assert same.rules == ("answer", "words") and same.also == ()  # a later rule of the winner's own type is in rules, not in also


def test_rules_lists_every_matching_rule_winner_first() -> None:
    assert with_rules("345").cause(frozenset({"C1"})).rules == ("link", "answer", "words")


def test_before_verdict_names_a_relayed_done_between_the_result_and_the_verdict() -> None:
    e = escape(before=True)
    assert e.cause().before_verdict == e.case.tasks[-1].id
    assert escape().cause().before_verdict == ""
    assert escape(relayed=True, before=True).cause().before_verdict != ""  # independent of the type


def test_legacy_reworks_without_source_never_match_the_relayed_rules() -> None:
    e = escape(carry_over=False, source=None)
    assert e.case.tasks[-1].source is None
    cause = e.cause()
    assert cause.type == "untyped" and "relayed task" not in cause.rules and "carry-over" not in cause.rules


def test_a_same_as_r_link_is_resolved_through_the_assertion() -> None:
    first_task, second_task = task(1), task(100)
    f1, f2 = done(first_task, 10), done(second_task, 110)
    first = case_of([first_task], [f1], rejection(first_task, 20, links=("C1",)), name="A")
    second = case_of([second_task], [f2], rejection(second_task, 120, links=("R1",)), name="B")
    assertions = regressions([first, second])
    assert assertions[1].about == ("C1",) and assertions[1].verdict.confirmed == ()
    results = latest_results([f1, f2])
    delivery = deliveries_of(second, results, {})[0]
    cause = cause_of(delivery, second, assertions[1], frozenset({"C1"}), (), results)
    assert (cause.type, cause.rule) == ("reviewer-miss", "link")
    assert cause.detail == (second.verdicts[0].link_notes[0].id, "C1")  # the link note that said "the same as R1"


def test_a_custom_lasting_vocabulary_is_used() -> None:
    e = escape(words="Henceforth cite the source, always")
    assert e.cause(lasting=("henceforth",)).detail == ("henceforth",)
    assert escape(words="Henceforth cite the source").cause().type == "untyped"  # the default vocabulary does not know it


def test_a_relayed_link_names_no_criterion_for_the_rules() -> None:
    e = escape(links=("C1",), link_source="relayed")
    assert e.assertion.link == "unconfirmed"
    cause = e.cause(frozenset({"C1"}))
    assert (cause.type, cause.rule) == ("untyped", "none")  # the assistant's reading is no evidence of the client's
    e2 = escape(links=("C9",), link_source="relayed", words="always")
    assert e2.cause(frozenset({"C1"})).rule == "words"


# ------------------------------------------------------------------------------------------------------------------------ unstored versions


def test_named_criteria_with_an_unstored_version_are_untyped_unreadable() -> None:
    e = escape(links=("C1",), contract=2, words="always")
    cause = e.cause(None)  # contract v2 is not among the stored versions
    assert (cause.type, cause.rule, cause.detail, cause.rules, cause.also) == ("untyped", "unreadable", ("contract v2 is not stored",), (), ())


def test_the_relayed_rules_still_run_before_the_unreadable_fallback() -> None:
    assert escape(relayed=True, links=("C1",)).cause(None).type == "relayed-error"
    assert escape(carry_over=True, links=("C1",)).cause(None).type == "relayed-carry-over"


def test_without_named_criteria_an_unstored_version_still_runs_rules_5_and_6() -> None:
    assert escape(words="always cite").cause(None).rule == "words"
    assert escape().cause(None).rule == "none"


# ------------------------------------------------------------------------------------------------------------------------ the renderer's fields (PC-4, DR3-2)


def test_an_id_the_answer_removes_is_listed_only_in_removes() -> None:
    e = escape(links=("C6", "C7"))  # C6 was carried and the answering version removes it; C7 the task did not have
    cause = e.cause(frozenset({"C6"}), ("C6",))
    assert (cause.type, cause.rule) == ("contract-gap", "answer")
    assert cause.removes == ("C6",)
    assert cause.detail[1:] == ("C6", "C7")  # the detail lists every id the rule read; the renderer splits them by ``removes``
    assert escape(links=("C9",)).cause(frozenset({"C1"})).removes == ()


def test_cause_carries_the_carried_and_answering_versions() -> None:
    e = escape(links=("C9",), contract=2)
    cause = e.cause(frozenset({"C1"}), answering=3)
    assert (cause.version, cause.answering) == (2, 3)  # the task's recorded version, and the answering one the caller passes
    assert e.cause(frozenset({"C1"}), version=5, answering=3).version == 5  # a legacy task: the caller gives the version in force
    assert escape(links=("C9",)).cause(frozenset({"C1"})).version == 0  # a task that recorded no version, none given


# ------------------------------------------------------------------------------------------------------------------------ attribution, failure class


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("reviewer-miss", "counted"), ("untyped", "counted"), ("contract-gap", "not its"), ("relayed-error", "not its"), ("relayed-carry-over", "not its")],
)
def test_attribution_counts_reviewer_miss_and_untyped_only(kind: str, expected: str) -> None:
    assert attribution(Cause(kind, "x")) == expected


def test_failure_class_is_off_spec_for_reviewer_miss_only() -> None:
    assert {kind: failure_class(Cause(kind, "x")) for kind in CAUSES} == {
        "relayed-error": None, "relayed-carry-over": None, "contract-gap": None, "reviewer-miss": "off_spec", "untyped": None,
    }
