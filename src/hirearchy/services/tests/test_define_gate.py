"""The gate of the acceptance criteria (design 5.2 steps 3.2, 3.3 and 3.6): root changes them only as the user's answer to a rejection or as a change
the user asked for on their own, and only once every delivery has its verdict. The record the definer is told about is the test's (``Basis``);
``reflection`` has the real one and ``tests/e2e/test_org_growth_0a2.py`` replays E4's sessions through both."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from ._support import amend, answer, define
from ._support import request as ask
from .test_define_answers import NOTE, RULE, YES, Basis, build, factory, meta, refusal, reject, version  # noqa: F401  (factory is a fixture)

WORDS_ALONE = "Add the rule, please."


def delivered(w: Any, basis: Basis, topic: str = "ai") -> str:
    """A delivery nobody has rated yet: the record says so."""
    task = ask(w, topic)
    answer(w, task)
    basis.unrated = (*basis.unrated, task.id)
    return task.id


def test_an_amendment_while_a_delivery_has_no_verdict_is_refused_whatever_else_is_passed(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    first, second = delivered(w, basis, "a"), delivered(w, basis, "b")
    text = (
        f"refused: 2 delivered request(s) of `weekly-brief` have no verdict yet: {first}, {second}. Record a verdict on each with feedback first: "
        "on a delivery the user saw, the user's own, a rejection then its one question (CLI: hirearchy feedback <task id> accept|reject --note ...); "
        'on a relayed rework the user never saw, your own, with source="relayed" (CLI: --source relayed), settles it. The contract changes only '
        "after the verdicts. Nothing was written."
    )
    for given in (
        {}, {"words": WORDS_ALONE}, {"words": "x" * 2000}, {"answers": found.note}, {"answers": found.note, "about": "C1", "words": YES},
        {"answers": "nonsense", "about": "C9", "words": NOTE},
    ):
        assert refusal(w, add_acceptance=[RULE], **given) == text
    assert version(w) == 1
    basis.unrated = (first,)
    assert refusal(w, add_acceptance=[RULE], words=WORDS_ALONE).startswith("refused: 1 delivered request(s) of `weekly-brief`")


def test_an_amendment_without_words_is_refused_with_both_forms(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    head = (
        "refused: a change of the acceptance criteria of `weekly-brief` records the user's words. If it answers a rejection, pass "
        "answers=<the rejection's message id>, about=<the C or R id your one question named> and words=<the user's answer, verbatim> "
        "(CLI: --answers, --about, --words), after they answered yes to that question{open}. If the user asked for this change on their own, outside "
        "any rejection, pass words=<their request, verbatim> alone (CLI: --words): it is recorded as user-initiated and never admits a playbook "
        "revision. Nothing was written."
    )
    assert refusal(w, add_acceptance=[RULE]) == head.format(open="")
    assert refusal(w, add_acceptance=[RULE], words="   ") == head.format(open="")
    first, second = reject(w, basis), reject(w, basis, "Another one entirely, please.", "b")
    waiting = f" (waiting for an answer: R1, message {first.note}; R2, message {second.note})"
    assert refusal(w, add_acceptance=[RULE]) == head.format(open=waiting)
    basis.rejections[0] = replace(first, answered="20261018T100000000099-root-0001")
    assert refusal(w, remove_acceptance=["At most 600 words"]) == head.format(open=f" (waiting for an answer: R2, message {second.note})")
    assert version(w) == 1


def test_words_alone_while_a_rejection_has_no_answer_is_refused(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    first = reject(w, basis)
    second = reject(w, basis, "Another one entirely, please.", "b")
    basis.rejections[0] = replace(first, question='About C1: add "<the rule, in their words>" as a lasting rule? Yes or no.')
    text = refusal(w, add_acceptance=[RULE], words=WORDS_ALONE)
    assert text == (
        f"refused: rejection R1 (message {first.note}) on task {first.task} has no answer yet, so this change is not one the user asked for on their "
        'own. Ask the user the one question first (About C1: add "<the rule, in their words>" as a lasting rule? Yes or no.). '
        f'On yes: define_service(owner="ceo", name="weekly-brief", ..., answers="{first.note}", about=<the id you asked about>, words=<their answer, '
        'verbatim>) (CLI: --answers, --about, --words). On no, a one-off or "as it is": '
        f'feedback(task_id="{first.task}", verdict="reject", confirms="{first.note}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", '
        "note=<their answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was written."
    )  # the oldest rejection is the one named
    assert second.note not in text and version(w) == 1
    amend(w, add_acceptance=[RULE], answers=first.note, about="C1", words=YES)  # answered by the contract: the next one is named
    assert f"rejection R2 (message {second.note})" in refusal(w, add_acceptance=["Another rule"], words=WORDS_ALONE)


def test_words_alone_with_every_delivery_rated_and_no_open_rejection_is_user_initiated(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    text = amend(w, add_acceptance=[RULE], words=WORDS_ALONE)
    assert version(w) == 2 and meta(w)["initiated"] == "user" and meta(w)["words"] == WORDS_ALONE
    assert 'Recorded as a change the user asked for on their own: "Add the rule, please.". C3 is user-initiated' in text
    assert basis.rejections == []


def test_a_rejection_answered_by_confirms_none_opens_the_user_path(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    assert "has no answer yet" in refusal(w, add_acceptance=[RULE], words=WORDS_ALONE)
    basis.rejections[0] = replace(found, answered="20261018T100000000099-root-0001")  # the user said "a one-off": the rejection has its answer
    amend(w, add_acceptance=[RULE], words=WORDS_ALONE)
    assert version(w) == 2


def test_a_pure_reordering_is_not_an_acceptance_amendment(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    reject(w, basis)
    delivered(w, basis)
    amend(w, acceptance=["Every factual claim has a source URL", "At most 600 words"])  # no words, an open rejection, an unrated delivery: not gated
    assert version(w) == 2 and "initiated" not in meta(w) and "answers" not in meta(w)


def test_an_agent_clients_amendment_is_not_gated(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    basis.unrated = ("a-delivery-nobody-rated",)
    define(w, owner="ceo/eng", name="inner", actor="ceo")
    amend(w, owner="ceo/eng", name="inner", actor="ceo", add_acceptance=["Brief"])  # the gate is for the human client's amendments only
    found = w.store.read_contract("ceo/eng", "inner")
    assert found is not None and found[0]["version"] == 2 and "initiated" not in found[0]
