"""``RuleAcknowledger``: the parent's acknowledgement of a playbook change (design 9.2): who may write one, the checks in their order, the quiet note it
writes (its title, its ``acknowledges`` header, its words), the refusals word for word, the hash of a new text and the reply.

The coverage of an item comes from the gate's watch: the admitting stand-in is given the ``ItemWatch`` of the items the world says cover something."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import Message, OrgError
from hirearchy.services import ItemWatch, acknowledge_reply
from hirearchy.services._acknowledge import text_hash
from hirearchy.services.testing import AdmittingServiceEvidence, ServicesWorld, fs_world, memory_world

from ._support import STEPS, define, populated

SERVICE = "weekly-brief"
WATCH = (
    ItemWatch("P1", "step", "kept", 1, coverage=("C1",)),
    ItemWatch("P2", "step", "new", 1, coverage=("C2", "R1")),
    ItemWatch("P3", "step", "kept", 1),
)
HASH = "0123456789ab"


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def factory(request: pytest.FixtureRequest) -> Callable[..., ServicesWorld]:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture
def w(factory: Callable[..., ServicesWorld], tmp_path: Path) -> ServicesWorld:
    """Root defined ``weekly-brief`` for ceo, who wrote v1 (P1-P3); P1 and P2 cover something, P3 nothing. Root also defined ``notes`` for ceo/eng."""
    world = populated(factory(tmp_path, AdmittingServiceEvidence(watch=WATCH)))
    define(world)
    world.commands.revise_playbook("ceo", SERVICE, "first", "the first steps", [], text=STEPS)
    define(world, owner="ceo/eng", name="notes", actor="ceo")
    world.commands.revise_playbook("ceo/eng", "notes", "first", "the first steps", [], text=STEPS)
    return world


def ack(w: ServicesWorld, op: str = "retire", item: str = "P1", *, actor: str = "root", owner: str = "ceo", service: str = SERVICE, **kw: Any) -> Message:
    if actor == "root" and "words" not in kw:
        kw["words"] = "Yes, do it."
    return w.commands.acknowledge_playbook(actor, owner, service, item, op, **kw)


def acks(w: ServicesWorld, addr: str) -> list[Message]:
    """The acknowledgements in ``addr``'s inbox (it also holds the client's notes on the playbook changes of the services it defined)."""
    return [m for m in w.d.inbox(addr) if m.acknowledges]


def refusal(w: ServicesWorld, *args: Any, **kw: Any) -> str:
    with pytest.raises(OrgError) as refused:
        ack(w, *args, **kw)
    return str(refused.value)


# ============================================================================================== the note it writes


def test_root_acknowledges_a_retire_with_the_users_words(w: ServicesWorld) -> None:
    note = ack(w, "retire", "P1", words="  Yes, retire it.  ")
    assert (note.sender, note.to, note.type, note.wake) == ("root", "ceo", "note", False)
    assert note.title == "playbook acknowledgement: retire P1 of weekly-brief"
    assert note.acknowledges == "weekly-brief retire P1"
    assert (note.source, note.body, note.feedback, note.criterion) == ("human", "Yes, retire it.", None, None)
    assert [(m.id, m.acknowledges) for m in acks(w, "ceo")] == [(note.id, "weekly-brief retire P1")]


def test_an_edit_is_acknowledged_for_one_text_hash(w: ServicesWorld) -> None:
    note = ack(w, "edit", "p2", text_hash=HASH, words="Yes, change it.")
    assert note.title == "playbook acknowledgement: edit P2 of weekly-brief"
    assert note.acknowledges == f"weekly-brief edit P2 {HASH}"
    assert [m.acknowledges for m in acks(w, "ceo")] == [f"weekly-brief edit P2 {HASH}"]


def test_a_manager_acknowledges_without_words_and_its_body_reads_acknowledged(w: ServicesWorld) -> None:
    note = ack(w, "retire", "P1", actor="ceo", owner="eng", service="notes")  # the short name of a direct report is enough for a manager
    assert (note.sender, note.to, note.type, note.wake, note.source) == ("ceo", "ceo/eng", "note", False, None)
    assert note.body == "Acknowledged." and note.acknowledges == "notes retire P1"
    assert note.title == "playbook acknowledgement: retire P1 of notes"
    assert [m.acknowledges for m in acks(w, "ceo/eng")] == ["notes retire P1"]
    edit = ack(w, "edit", "P2", actor="ceo", owner="ceo/eng", service="notes", text_hash=HASH)
    assert edit.acknowledges == f"notes edit P2 {HASH}"


def test_an_acknowledgement_costs_no_run_and_wakes_nobody(w: ServicesWorld) -> None:
    ack(w, "retire", "P1")
    assert all(not m.wake and m.budget == 0 for m in acks(w, "ceo"))


def test_words_of_exactly_1000_characters_are_accepted(w: ServicesWorld) -> None:
    assert ack(w, "retire", "P1", words="y" * 1000).body == "y" * 1000


# ============================================================================================== the refusals, word for word and in order

NOT_YOURS = "refused: {owner} is not your direct report: only its parent acknowledges a change of its playbook. Nothing was written."


def test_each_refusal_word_for_word(w: ServicesWorld) -> None:
    assert refusal(w, owner="ceo/eng", service="notes") == NOT_YOURS.format(owner="ceo/eng")  # root is not the parent of ceo/eng
    assert refusal(w, actor="ops", owner="ceo") == NOT_YOURS.format(owner="ceo")
    assert refusal(w, owner="nobody") == NOT_YOURS.format(owner="nobody")
    assert refusal(w, service="nope") == "refused: ceo offers no service `nope`. Its services: weekly-brief. Nothing was written."
    assert refusal(w, "retire", "P9") == "refused: `weekly-brief` of ceo has no live item P9. Its items: P1, P2, P3. Nothing was written."
    assert refusal(w, "restore") == (
        "refused: op is retire or edit (CLI: retire|edit; a restore is acknowledged as edit): restore. Nothing was written."
    )
    assert refusal(w, "retire", "P1", text_hash=HASH) == (
        'refused: text_hash goes with op="edit" only (CLI: --text-hash): a retire is acknowledged for the item, whatever its text. Nothing was written.'
    )
    assert refusal(w, "edit", "P1") == (
        'refused: an edit is acknowledged for one new text: pass text_hash="<the 12 hex digits ceo\'s request named>" (CLI: --text-hash). '
        "Nothing was written."
    )
    assert refusal(w, "retire", "P3") == (
        "refused: P3 covers no current criterion or confirmed assertion, so ceo needs no acknowledgement to retire it. Nothing was written."
    )
    assert refusal(w, "edit", "P3", text_hash=HASH) == (
        "refused: P3 covers no current criterion or confirmed assertion, so ceo needs no acknowledgement to edit it. Nothing was written."
    )
    assert acks(w, "ceo") == [] and acks(w, "ceo/eng") == []


@pytest.mark.parametrize("bad", ["", " ", "xyz", "0123456789a", "0123456789abc", "0123456789AB", "0123456789ag", "sha:0123456789"])
def test_a_missing_or_malformed_hash_is_ack_hash(w: ServicesWorld, bad: str) -> None:
    assert refusal(w, "edit", "P1", text_hash=bad).startswith("refused: an edit is acknowledged for one new text: pass text_hash=")


def test_a_hash_of_12_lower_case_hex_digits_is_accepted(w: ServicesWorld) -> None:
    assert ack(w, "edit", "P1", text_hash="abcdef012345").acknowledges == "weekly-brief edit P1 abcdef012345"


def test_ack_words_when_root_gives_none_or_blank_or_too_many(w: ServicesWorld) -> None:
    head = "refused: an acknowledgement from root records the user's yes: pass words=<their answer, verbatim> (CLI: --words), after they answered yes to ceo's request"
    for words in (None, "", "   \n"):
        with pytest.raises(OrgError) as refused:
            w.commands.acknowledge_playbook("root", "ceo", SERVICE, "P1", "retire", words=words)
        assert str(refused.value) == f"{head}. Nothing was written."
    assert refusal(w, "retire", "P1", words="y" * 1001) == f"{head}; words has 1001 characters, the limit is 1000. Nothing was written."
    assert refusal(w, "retire", "P1", words=" " + "y" * 1500 + " ") == f"{head}; words has 1500 characters, the limit is 1000. Nothing was written."
    assert acks(w, "ceo") == []


def test_ack_agent_words_when_a_manager_passes_words(w: ServicesWorld) -> None:
    text = "refused: words= records the user's own yes, so only root passes it; acknowledge without it. Nothing was written."
    assert refusal(w, "retire", "P1", actor="ceo", owner="eng", service="notes", words="yes") == text
    assert refusal(w, "retire", "P1", actor="ceo", owner="eng", service="notes", words="") == text
    assert acks(w, "ceo/eng") == []


def test_the_checks_run_in_the_order_of_the_design(w: ServicesWorld) -> None:
    # owner, service, item, op, hash, coverage, words: each failure hides the ones after it
    assert refusal(w, "bogus", "P9", service="nope").startswith("refused: ceo offers no service `nope`")
    assert refusal(w, "bogus", "P9").startswith("refused: `weekly-brief` of ceo has no live item P9")
    assert refusal(w, "bogus", "P1", text_hash=HASH).startswith("refused: op is retire or edit")
    assert refusal(w, "edit", "P3", words=None).startswith("refused: an edit is acknowledged for one new text")
    assert refusal(w, "retire", "P3", words=None).startswith("refused: P3 covers no current criterion")
    assert refusal(w, "retire", "P1", words=None).startswith("refused: an acknowledgement from root records the user's yes")
    assert refusal(w, "retire", "P1", actor="ceo", owner="eng", service="notes", words="yes").startswith("refused: words= records")


def test_a_retired_item_is_not_live(w: ServicesWorld) -> None:
    w.commands.revise_playbook("ceo", SERVICE, "retire", "not needed", [], item="P3")
    assert refusal(w, "retire", "P3") == "refused: `weekly-brief` of ceo has no live item P3. Its items: P1, P2. Nothing was written."


def test_a_service_without_items_has_none_to_acknowledge(factory: Callable[..., ServicesWorld], tmp_path: Path) -> None:
    world = populated(factory(tmp_path, AdmittingServiceEvidence(watch=WATCH)))
    define(world)  # no playbook yet
    assert refusal(world, "retire", "P1") == "refused: `weekly-brief` of ceo has no live item P1. Its items: none. Nothing was written."


def test_an_owner_without_services_lists_none(w: ServicesWorld) -> None:
    assert refusal(w, owner="ops") == "refused: ops offers no service `weekly-brief`. Its services: none. Nothing was written."


# ============================================================================================== the hash of a new text (9.2)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def test_the_text_hash_of_a_step_is_the_first_12_digits_of_the_sha256_of_its_stripped_text() -> None:
    assert text_hash("step", "  Check every claim.  ") == sha("Check every claim.")
    assert text_hash("step", "Check every claim.\n") == text_hash("step", "Check every claim.")
    assert text_hash("step", "é ✓") == sha("é ✓")  # UTF-8
    assert len(text_hash("step", "x")) == 12 and text_hash("step", "x") != text_hash("step", "y")


def test_the_text_hash_of_a_rule_is_when_newline_then_each_stripped() -> None:
    assert text_hash("rule", " Send it. ", " the user asks ") == sha("the user asks\nSend it.")


def test_the_text_hash_of_a_rule_with_when_absent_empty_or_always_is_equal() -> None:
    expected = sha("always\nSend it.")
    for when in (None, "", "   ", "always", "ALWAYS", " Always "):
        assert text_hash("rule", "Send it.", when) == expected
    assert text_hash("rule", "Send it.", "sometimes") != expected


def test_a_step_and_a_rule_with_the_same_words_hash_apart() -> None:
    assert text_hash("step", "Send it.") != text_hash("rule", "Send it.")


# ============================================================================================== the reply


def test_the_reply_names_the_note_and_how_the_owner_applies_it(w: ServicesWorld) -> None:
    note = ack(w, "retire", "P1")
    assert acknowledge_reply("retire", "P1", SERVICE, "ceo", note.id) == (
        f"Acknowledged retire of P1 (weekly-brief): note {note.id}. ceo applies it at its next run by making the refused change again with "
        f'acknowledged="{note.id}".'
    )
    assert acknowledge_reply("edit", "P2", "notes", "ceo/eng", "N1").startswith("Acknowledged edit of P2 (notes): note N1. ceo/eng applies it")
