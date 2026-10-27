# mypy: ignore-errors
# The tests that need the real record of a service (reflection's) use the full organization of testkit (untyped): not type-checked strictly.
"""Root retires a service only after its verdicts and answers (design 5.2a): the same basis as the gate of the criteria, so that the record a
retired copy keeps is complete at the moment it is retired. The definer is told the record by the test (``Basis``, as in ``test_define_gate``);
the last tests run over the real record (``reflection``'s), through the organization of ``testkit``."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from testkit.services_world import deliver, request, svc  # noqa: F401  (svc is a fixture)

from hirearchy.kernel import ROOT, OrgError

from ._support import amend, answer, define
from ._support import request as ask
from .test_define_answers import NOTE, RULE, YES, Basis, ask_after, build, factory, reject  # noqa: F401  (factory is a fixture)

SERVICE = "weekly-brief"
LINK = "20261018T100000000099-root-0001"


def retire(w: Any, actor: str = "root", owner: str = "ceo", name: str = SERVICE) -> str:
    return w.commands.retire_service(actor, owner, name, "not needed")


def refusal(w: Any, **kw: Any) -> str:
    with pytest.raises(OrgError) as info:
        retire(w, **kw)
    return str(info.value)


def untouched(w: Any) -> None:
    """A refusal retires nothing, tells nobody and emits no event."""
    assert w.catalog.service_names("ceo") == [SERVICE]
    assert all("retired" not in m.title for m in w.d.inbox("ceo"))
    assert not [e for e in w.events.events if e.kind == "service.retire"]


def delivered(w: Any, basis: Basis, topic: str = "ai") -> str:
    """A delivery nobody has rated yet: the record says so."""
    task = ask_after(w, basis, topic)
    answer(w, task)
    basis.unrated = (*basis.unrated, task.id)
    return task.id


def test_root_cannot_retire_a_service_with_an_unrated_delivery(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    first, second = delivered(w, basis, "a"), delivered(w, basis, "b")
    assert refusal(w) == (
        f"refused: 2 delivered request(s) of `weekly-brief` have no verdict yet: {first}, {second}. Record the user's verdict on each with feedback "
        "first (CLI: hirearchy feedback <task id> accept|reject --note ...); a service is retired only after its verdicts, so that its record stays "
        "complete. Nothing was retired."
    )
    untouched(w)
    basis.unrated = (first,)
    assert refusal(w).startswith("refused: 1 delivered request(s) of `weekly-brief` have no verdict yet: ")
    basis.unrated = ()
    assert "retired service `weekly-brief`" in retire(w)


def test_root_cannot_retire_a_service_with_an_unanswered_rejection(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    first = reject(w, basis)
    second = reject(w, basis, "Another one entirely, please.", "b")
    basis.rejections[0] = replace(first, question='About C1: add "<the rule, in their words>" as a lasting rule? Yes or no.')
    text = refusal(w)
    assert text == (
        f"refused: rejection R1 (message {first.note}) on task {first.task} of `weekly-brief` has no answer yet. Ask the user the one question "
        'first (About C1: add "<the rule, in their words>" as a lasting rule? Yes or no.) and record the answer: '
        f'define_service(..., answers="{first.note}", about=<the id you asked about>, words=<their answer, verbatim>) on yes '
        "(CLI: --answers, --about, --words), "
        f'feedback(task_id="{first.task}", verdict="reject", confirms="{first.note}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", '
        "note=<their answer, verbatim>) otherwise (CLI: --confirms, --criterion, --source human, --note). A service is retired only after its "
        "rejections are answered. Nothing was retired."
    )  # the oldest rejection is the one named
    assert second.note not in text
    untouched(w)
    amend(w, add_acceptance=[RULE], answers=first.note, about="C1", words=YES)  # answered by a contract version: the next one is named
    assert f"rejection R2 (message {second.note})" in refusal(w)
    untouched(w)


def test_an_unreadable_basis_fails_closed_for_retirement(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    for error in (OSError("disk gone"), OrgError("mailbox broken")):
        basis.error = error
        assert refusal(w) == (
            f"refused: the record of `weekly-brief` cannot be read ({error}), so the service was not retired. Try again; if it persists, tell the user."
        )
        untouched(w)
    basis.error = None
    assert "retired service `weekly-brief`" in retire(w)


def test_after_every_verdict_and_answer_the_retirement_is_admitted(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    first = reject(w, basis)
    second = reject(w, basis, "Another one entirely, please.", "b")
    delivered(w, basis)
    assert "have no verdict yet" in refusal(w)
    basis.unrated = ()  # the user's verdict is in
    assert "rejection R1" in refusal(w)
    amend(w, add_acceptance=[RULE], answers=first.note, about="C1", words=YES)  # R1: answered by a contract version
    assert "rejection R2" in refusal(w)
    basis.rejections[1] = replace(second, answered=LINK)  # R2: answered by a link ("a one-off")
    assert "retired service `weekly-brief` of ceo" in retire(w)
    assert w.catalog.service_names("ceo") == [] and [e.kind for e in w.events.events][-1] == "service.retire"
    (note,) = [m for m in w.d.inbox("ceo") if m.title == "service weekly-brief retired"]
    assert note.wake is False


def test_a_relayed_accept_counts_as_a_verdict(svc) -> None:
    """The user drops the delivery: root records a relayed accept, which is a verdict (rated by any tier), and the service can be retired."""
    task = request(svc)
    deliver(svc, "ceo", task)
    with pytest.raises(OrgError, match="have no verdict yet"):
        svc.retire_service(ROOT, "ceo", SERVICE, "done")
    svc.feedback(ROOT, task.id, "accept", "dropped", source="relayed")
    assert "retired service `weekly-brief` of ceo" in svc.retire_service(ROOT, "ceo", SERVICE, "done")


def test_confirms_none_answers_a_rejection_for_retirement(svc) -> None:
    """A rejection is answered by a human link with ``none`` ("a one-off", "as it is"), which is the way out the refusal names."""
    task = request(svc)
    deliver(svc, "ceo", task)
    no = svc.feedback(ROOT, task.id, "reject", NOTE, source="human")
    with pytest.raises(OrgError, match="rejection R1 .* has no answer yet"):
        svc.retire_service(ROOT, "ceo", SERVICE, "done")
    svc.feedback(ROOT, task.id, "reject", "No, a one-off.", source="human", criterion=["none"], confirms=no.id)
    assert "retired service `weekly-brief` of ceo" in svc.retire_service(ROOT, "ceo", SERVICE, "done")


def test_an_agent_retiring_its_reports_service_is_not_gated(factory: Any, tmp_path: Path) -> None:
    """The gate is for the human client (root); an agent client retires its report's service as before, whatever the record says."""
    w, basis = build(factory, tmp_path)
    reject(w, basis)
    delivered(w, basis)
    basis.error = OSError("the record of weekly-brief is unreadable, but nobody asks")
    define(w, owner="ceo/eng", name="inner", actor="ceo")
    assert "retired service `inner` of ceo/eng" in w.commands.retire_service("ceo", "ceo/eng", "inner", "done")
    assert w.catalog.service_names("ceo/eng") == []


def test_a_service_with_only_open_requests_retires_as_today(svc) -> None:
    """No result yet means no delivery to rate and no rejection: n = 0, the gate has nothing to say (a request still open is the declared facet)."""
    request(svc)
    assert "retired service `weekly-brief` of ceo" in svc.retire_service(ROOT, "ceo", SERVICE, "redo")
