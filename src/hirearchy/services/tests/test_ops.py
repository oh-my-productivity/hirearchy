"""``RuleItemReviser``: ``revise_playbook`` changes one item per call (design 5): first, add, edit and retire, the order of its checks, its refusals
word for word, the migration of a free-text playbook, the replies and the client's note. The gate is the admitting stand-in (the real one is judged in
``reflection``); the refusing one makes a gated change fail."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from testkit.services_world import svc  # noqa: F401  (a fixture: the wired application with ceo offering weekly-brief)

from hirearchy.kernel import Message, OrgError, split_frontmatter
from hirearchy.services import Admission, ItemWatch, PlaybookChange, PlaybookItem, PlaybookRace, ServiceCommands, normalize_evidence, playbook_reply
from hirearchy.services._items import checked_body
from hirearchy.services.testing import AdmittingServiceEvidence, RefusingServiceEvidence, ServicesWorld, fs_world, memory_world

from ._support import STEPS, answer, define, populated, request

SERVICE = "weekly-brief"
PLAYBOOK = f"ceo/services/{SERVICE}/PLAYBOOK.md"
HISTORY = f"ceo/services/{SERVICE}/history/PLAYBOOK.v{{}}.md"
FIRST = "## Steps\n1. Search.\n2. Write.\n3. Check every claim."
PB_FORM = (
    "refused: revise_playbook changes one item of the playbook per call; it no longer takes the whole text (`content`). Use op=\"add\" (kind "
    "\"step\" with text and after, or kind \"rule\" with when and then), \"edit\" (item and the new text), \"retire\" (item), \"restore\" (item, "
    "version) or \"move\" (item, after). Your playbook's items and their ids are in your prompt under \"# Playbook\". Nothing was written."
)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    return populated(request.param(tmp_path))


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def refusing(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    return populated(request.param(tmp_path, RefusingServiceEvidence("refused by the stand-in for the gate")))


def revise(w: ServicesWorld, op: str | None, evidence: tuple[str, ...] = (), *, reason: str = "because", actor: str = "ceo", **kw: Any) -> PlaybookChange:
    return w.commands.revise_playbook(actor, SERVICE, op, reason, evidence, **kw)


def refusal(w: ServicesWorld, op: str | None, evidence: tuple[str, ...] = (), *, reason: str = "because", actor: str = "ceo", **kw: Any) -> str:
    with pytest.raises(OrgError) as e:
        revise(w, op, evidence, reason=reason, actor=actor, **kw)
    return str(e.value)


def meta_of(w: ServicesWorld, rel: str = PLAYBOOK) -> tuple[dict[str, Any], str]:
    text = w.text(rel)
    assert text is not None, rel
    meta, body = split_frontmatter(text)
    return dict(meta), body.strip()


def seeded(w: ServicesWorld, text: str = FIRST) -> ServicesWorld:
    """The service is defined and its owner has written v1 (three steps, P1-P3)."""
    define(w)
    revise(w, "first", text=text)
    return w


def legacy(w: ServicesWorld, body: str, version: int = 1, by: str = "ceo") -> None:
    """A free-text playbook as it was written before Phase 1 (no `items_max`)."""
    meta = {"service": SERVICE, "version": version, "revised": "2026-01-01T00:00:00+00:00", "by": by, "reason": "earlier"}
    w.store.write_playbook("ceo", SERVICE, version, meta, body, version - 1 or None)


def delivered(w: ServicesWorld) -> Message:
    task = request(w)
    answer(w, task)
    return task


# ============================================================================================== the order of the checks (5.1 step 1)


def test_content_or_no_op_is_pb_form(w: ServicesWorld) -> None:
    define(w)
    assert refusal(w, "add", content="## Steps\n1. Search.", kind="step", text="x") == PB_FORM
    assert refusal(w, None) == PB_FORM
    assert refusal(w, None, content="## Steps") == PB_FORM
    assert refusal(w, "add", actor="ops", content="x") == PB_FORM  # judged first: before the owner check
    assert w.text(PLAYBOOK) is None


def test_a_locked_contract_is_refused_as_today(w: ServicesWorld) -> None:
    define(w, locked=True)
    assert refusal(w, "first", text=FIRST) == (
        "the contract of `weekly-brief` is locked by root: you may not revise its playbook. Follow the current one, and if you think it must change, "
        "tell root (`send`)."
    )
    assert w.text(PLAYBOOK) is None


def test_only_the_owner_revises(w: ServicesWorld) -> None:
    define(w)
    assert "do not own a service called `weekly-brief`. Services you own: none." in refusal(w, "first", actor="ops", text=FIRST)
    with pytest.raises(OrgError, match="do not own a service called `nope`.*weekly-brief"):
        w.commands.revise_playbook("ceo", "nope", "first", "r", [], text=FIRST)
    with pytest.raises(OrgError, match="do not own"):
        w.commands.revise_playbook("root", SERVICE, "first", "r", [], text=FIRST)


def test_the_reason_is_1_to_400_characters(w: ServicesWorld) -> None:
    define(w)
    for reason in (" ", "r" * 401):
        assert refusal(w, "first", reason=reason, text=FIRST).startswith("reason is 1-400 characters: say what changed")
    revise(w, "first", reason="r" * 400, text=FIRST)


def test_the_evidence_is_a_list_of_at_most_20_ids(w: ServicesWorld) -> None:
    define(w)
    assert refusal(w, "first", evidence="not a list", text=FIRST).startswith("evidence is a list of at most 20 ids")  # type: ignore[arg-type]


def test_pb_op_names_the_value_it_was_given(w: ServicesWorld) -> None:
    define(w)
    assert refusal(w, "replace", text="x") == "refused: op is one of first, add, edit, retire, restore, move: replace. Nothing was written."


ADD = 'kind ("step" with text, or "rule" with then), and optionally when (a rule) and after (an item id)'
EDIT = "item and the new text (a step: text; a rule: then and/or when), and optionally acknowledged"
FIRST_NEEDED = "text (the whole first version, in markdown)"
ARGS = [
    ("first", {}, FIRST_NEEDED, "text is missing"),
    ("first", {"text": "x", "item": "P1"}, FIRST_NEEDED, 'item does not go with op="first"'),
    ("first", {"text": "x", "kind": "step", "after": "P1"}, FIRST_NEEDED, 'kind does not go with op="first"; after does not go with op="first"'),
    ("add", {}, ADD, "kind is missing"),
    ("add", {"kind": "thing", "text": "x"}, ADD, 'kind is "thing", not "step" or "rule"'),
    ("add", {"kind": "step"}, ADD, "text is missing"),
    ("add", {"kind": "step", "text": "x", "then": "y"}, ADD, 'then does not go with op="add"'),
    ("add", {"kind": "step", "text": "x", "when": "y"}, ADD, 'when does not go with op="add"'),
    ("add", {"kind": "rule"}, ADD, "then is missing"),
    ("add", {"kind": "rule", "then": "y", "text": "x"}, ADD, 'text does not go with op="add"'),
    ("add", {"kind": "step", "text": "x", "item": "P1"}, ADD, 'item does not go with op="add"'),
    ("add", {"kind": "step", "text": "x", "version": 2}, ADD, 'version does not go with op="add"'),
    ("add", {"kind": "step", "text": "x", "acknowledged": "a"}, ADD, 'acknowledged does not go with op="add"'),
    ("edit", {}, EDIT, "item is missing; text is missing"),
    ("edit", {"item": "P1"}, EDIT, "text is missing"),
    ("edit", {"item": "P1", "text": "x", "kind": "step"}, EDIT, 'kind does not go with op="edit"'),
    ("edit", {"item": "P1", "text": "x", "after": "P2"}, EDIT, 'after does not go with op="edit"'),
    ("edit", {"item": "P1", "text": "x", "version": 1}, EDIT, 'version does not go with op="edit"'),
    ("retire", {}, "item, and optionally acknowledged", "item is missing"),
    ("retire", {"item": "P1", "text": "x"}, "item, and optionally acknowledged", 'text does not go with op="retire"'),
    ("retire", {"item": "P1", "kind": "step", "version": 1}, "item, and optionally acknowledged", 'kind does not go with op="retire"; version does not go with op="retire"'),
]


@pytest.mark.parametrize(("op", "kw", "needed", "wrong"), ARGS)
def test_pb_args_names_what_the_op_takes_and_what_is_wrong(w: ServicesWorld, op: str, kw: dict[str, Any], needed: str, wrong: str) -> None:
    define(w)
    assert refusal(w, op, **kw) == f'refused: op="{op}" takes {needed}; {wrong}. Nothing was written.'
    assert w.text(PLAYBOOK) is None


TEXTS = [
    ({"kind": "step", "text": "   "}, "text is empty"),
    ({"kind": "step", "text": "a\nb"}, "text has more than one line (2 lines)"),
    ({"kind": "step", "text": "x" * 1201}, "text has more than 1200 characters (1201)"),
    ({"kind": "step", "text": " ".join(["w"] * 151)}, "text and then have more than 150 words with when (151)"),
    ({"kind": "step", "text": "see [P3] first"}, "text has an item id in brackets ([P3]): ids are the runtime's"),
    ({"kind": "step", "text": "see [p12] first"}, "text has an item id in brackets ([p12]): ids are the runtime's"),
    ({"kind": "step", "text": "# Heading"}, 'text starts with "#": a heading is no item'),
    ({"kind": "rule", "then": " "}, "then is empty"),
    ({"kind": "rule", "then": "x" * 601}, "then has more than 600 characters (601)"),
    ({"kind": "rule", "then": "a\nb"}, "then has more than one line (2 lines)"),
    ({"kind": "rule", "then": "see [P1]"}, "then has an item id in brackets ([P1]): ids are the runtime's"),
    ({"kind": "rule", "then": "do it", "when": "x" * 301}, "when has more than 300 characters (301)"),
    ({"kind": "rule", "then": "do it", "when": "a\nb"}, "when has more than one line (2 lines)"),
    ({"kind": "rule", "then": "do it", "when": "see [P2]"}, "when has an item id in brackets ([P2]): ids are the runtime's"),
    ({"kind": "rule", "then": " ".join(["t"] * 80), "when": " ".join(["w"] * 71)}, "text and then have more than 150 words with when (151)"),
]


@pytest.mark.parametrize(("kw", "rule"), TEXTS)
def test_pb_text_rules(w: ServicesWorld, kw: dict[str, Any], rule: str) -> None:
    define(w)
    assert refusal(w, "add", ("R1",), **kw) == f"refused: {rule}. Nothing was written."
    assert w.text(PLAYBOOK) is None


def test_then_in_capitals_in_when_is_refused(w: ServicesWorld) -> None:
    define(w)
    assert refusal(w, "add", ("R1",), kind="rule", when="a date THEN b", then="do it") == (
        'refused: when has the word "THEN" in capitals: it would split the rule there; write the condition without it. Nothing was written.'
    )
    assert revise(w, "add", ("R1",), kind="rule", when="a date then b, thence c", then="do it").item == "P1"  # lower case and other words are fine


def test_a_criterions_own_words_are_exempt_from_the_keyword_bracket_and_length_rules(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path, CAdmitting()))  # a criterion's words are admitted by rule (c), which the 30% rule does not split
    long = "Every claim ends with a bracketed reference like [P1]. " + "It names its source in full. " * 45
    define(w, acceptance=["At most 600 words", long.strip(), "# Heading first"])
    assert len(long.strip()) > 1200
    assert revise(w, "add", ("R1",), kind="step", text=long.strip()).item == "P1"  # over the length, with a bracket: the criterion's own words
    assert revise(w, "add", ("R1",), kind="rule", then=long.strip()).item == "P2"  # a rule's then is over its 600 too
    assert revise(w, "add", ("R1",), kind="step", text="# Heading first").item == "P3"  # starts with "#"
    assert refusal(w, "add", ("R1",), kind="step", text="# Another heading").endswith('text starts with "#": a heading is no item. Nothing was written.')
    assert "ids are the runtime's" in refusal(w, "add", ("R1",), kind="step", text="Every claim ends with a bracketed reference like [P2].")


def test_the_first_texts_rules(w: ServicesWorld) -> None:
    define(w)
    assert refusal(w, "first", text="  ") == "refused: text is empty. Nothing was written."
    assert refusal(w, "first", text="---\nx: 1\n---\n") == "refused: text is empty. Nothing was written."
    assert refusal(w, "first", text="word " * 1001) == "refused: text has 1001 words; the limit is 1000 (playbook_max_words). Nothing was written."
    assert revise(w, "first", text="word " * 1000).version == 1


# ============================================================================================== first


def test_first_writes_v1_in_item_form_and_the_reply_names_its_sections(w: ServicesWorld) -> None:
    define(w)
    change = revise(w, "first", reason="the procedure of the first request", text="---\nversion: 99\n---\n# Weekly brief\n\n## Steps\n1. Search.\n2. Write.\n\n## Budget plan\n- 12 runs.")
    assert (change.version, change.op, change.item, change.kind, change.items, change.migrated) == (1, "first", "", "", 3, None)
    assert change.admission.rule == "first" and change.client == "root" and change.sections == ("Weekly brief", "Steps", "Budget plan")
    meta, body = meta_of(w)
    assert body == "# Weekly brief\n\n## Steps\n1. [P1] Search.\n2. [P2] Write.\n\n## Budget plan\n- [P3] 12 runs."
    assert playbook_reply(SERVICE, change) == (
        "playbook of weekly-brief is now v1: wrote playbook v1: 3 items (Weekly brief, Steps, Budget plan). root was told without being woken."
    )
    assert (meta["version"], meta["by"], meta["reason"], meta["service"]) == (1, "ceo", "the procedure of the first request", SERVICE)


def test_first_for_a_body_without_headings_says_none(w: ServicesWorld) -> None:
    define(w)
    change = revise(w, "first", text="Search, then write.")
    assert change.sections == () and playbook_reply(SERVICE, change).endswith("wrote playbook v1: 1 items (none). root was told without being woken.")


def test_pb_first_exists(w: ServicesWorld) -> None:
    seeded(w)
    assert refusal(w, "first", text="## Steps\n1. Other.") == (
        "refused: `weekly-brief` already has playbook v1: op=\"first\" writes only the first version. Change it one item at a time "
        '(op="add", "edit", "retire", "restore" or "move"). Nothing was written.'
    )


def test_a_v1_after_any_verdict_or_rework_is_pb_first_late(w: ServicesWorld) -> None:
    define(w)
    task = delivered(w)
    w.commands.feedback("root", task.id, "accept")
    message = refusal(w, "first", text=FIRST)
    assert message == (
        f"refused: `weekly-brief` already has evidence (a verdict on {task.id}), so its playbook is built one item at a time: op=\"add\" with "
        "evidence (your Reflect section says what is admitted). The first version is only for the procedure of the first request. Nothing was written."
    )
    assert w.text(PLAYBOOK) is None


def test_a_rework_alone_makes_a_v1_late_and_the_oldest_record_is_named(w: ServicesWorld) -> None:
    define(w)
    first = delivered(w)
    rework = request(w, revises=first.id)
    assert refusal(w, "first", text=FIRST).startswith(f"refused: `weekly-brief` already has evidence (a rework {rework.id}), so its playbook is")
    w.commands.feedback("root", first.id, "reject", "Too long.")
    assert f"(a rework {rework.id})" in refusal(w, "first", text=FIRST)  # the oldest of the records by message id: the rework came before the verdict
    assert w.text(PLAYBOOK) is None


def test_a_first_request_alone_leaves_a_v1_free(w: ServicesWorld) -> None:
    define(w)
    request(w)
    assert revise(w, "first", text=FIRST).version == 1


# ============================================================================================== add


def test_add_on_version_0_writes_v1_in_item_form(w: ServicesWorld) -> None:
    define(w)
    change = revise(w, "add", ("R1", "R2"), kind="step", text="Cite every claim.")
    meta, body = meta_of(w)
    assert (change.version, change.item, change.kind, change.items) == (1, "P1", "step", 1) and change.admission.rule == "b"
    assert body == "## Steps\n1. [P1] Cite every claim. (WHY R1, R2)"
    assert (meta["items_max"], meta["rules"], meta["why"], meta["op"], meta["item"], meta["admitted"], meta["evidence"]) == (
        1, [], {"P1": ["R1", "R2"]}, "add", "P1", "b", ["R1", "R2"],
    )
    rule = revise(w, "add", ("R3",), kind="rule", when="a claim has no source", then="say so in the review task")
    _, body = meta_of(w)
    assert rule.item == "P2" and body == (
        "## Steps\n1. [P1] Cite every claim. (WHY R1, R2)\n\n## Rules\n- [P2] WHEN a claim has no source THEN say so in the review task WHY R3"
    )


def test_a_rule_on_version_0_writes_its_own_rules_section(w: ServicesWorld) -> None:
    define(w)
    revise(w, "add", ("R1",), kind="rule", then="cite every claim")
    meta, body = meta_of(w)
    assert body == "## Rules\n- [P1] WHEN always THEN cite every claim WHY R1" and meta["rules"] == ["P1"]


def test_a_gated_add_writes_its_why_from_the_admission_never_from_the_owner(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "add", ("R1",), kind="step", text="Check dates. (WHY R9; C9)")  # a WHY in the owner's words stays words
    meta, body = meta_of(w)
    assert meta["why"] == {"P4": ["R1"]} and body.splitlines()[-1] == "4. [P4] Check dates. (WHY R9; C9) (WHY R1)"
    found = w.catalog.read_playbook("ceo", SERVICE)
    assert found.items is not None and found.items[-1].text == "Check dates. (WHY R9; C9)" and found.items[-1].why == ("R1",)


def test_add_goes_where_the_placement_rule_says(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "add", ("R1",), kind="step", text="Publish.", after="P1")
    assert meta_of(w)[1] == "## Steps\n1. [P1] Search.\n2. [P4] Publish. (WHY R1)\n3. [P2] Write.\n4. [P3] Check every claim."
    revise(w, "add", ("R1",), kind="rule", then="a rule")
    assert refusal(w, "add", ("R1",), kind="step", text="x", after="P5").endswith(
        "after=P5 is a rule: a step goes after a step (or leave after out). Nothing was written."
    )


def test_pb_args_for_an_after_that_places_nothing(w: ServicesWorld) -> None:
    seeded(w)
    assert refusal(w, "add", ("R1",), kind="step", text="x", after="P9") == (
        'refused: op="add" takes kind ("step" with text, or "rule" with then), and optionally when (a rule) and after (an item id); '
        "after=P9 is not a live item. Nothing was written."
    )
    assert refusal(w, "add", ("R1",), kind="rule", then="x", after="P1").endswith("after=P1 is not a live rule. Nothing was written.")


def test_a_refused_gate_writes_nothing(refusing: ServicesWorld) -> None:
    w = seeded(refusing)
    before = w.text(PLAYBOOK)
    assert refusal(w, "add", ("R1",), kind="step", text="x") == "refused by the stand-in for the gate"
    assert w.text(PLAYBOOK) == before and w.text(HISTORY.format(1)) is None
    assert [m.title for m in w.d.inbox("root")] == [f"playbook of {SERVICE} revised to v1"]  # the first version's note only


# ============================================================================================== edit


def test_an_edit_with_the_same_text_is_pb_same(w: ServicesWorld) -> None:
    seeded(w)
    assert refusal(w, "edit", ("R1",), item="P2", text="Write.") == (
        "refused: no change: P2 already reads so. Change an item only when the evidence calls for a different way of working. Nothing was written."
    )
    assert w.catalog.read_playbook("ceo", SERVICE).version == 1


def test_pb_item_lists_the_live_and_retired_ids(w: ServicesWorld) -> None:
    seeded(w)
    assert refusal(w, "edit", ("R1",), item="P9", text="x") == "refused: `weekly-brief` has no live item P9. Its items: P1, P2, P3. Nothing was written."
    revise(w, "retire", item="p2")
    assert refusal(w, "edit", ("R1",), item="P2", text="x") == (
        "refused: `weekly-brief` has no live item P2. Its items: P1, P3; retired: P2 (op=\"restore\" brings one back). Nothing was written."
    )
    revise(w, "retire", item="P1")
    revise(w, "retire", item="P3")
    assert refusal(w, "retire", item="P3") == (
        "refused: `weekly-brief` has no live item P3. Its items: none yet; retired: P1, P2, P3 (op=\"restore\" brings one back). Nothing was written."
    )
    define(w, name="other")  # a service with no playbook at all
    with pytest.raises(OrgError, match="has no live item P1. Its items: none yet. Nothing was written"):
        w.commands.revise_playbook("ceo", "other", "retire", "r", [], item="P1")


def test_edit_of_the_wrong_kind_of_text_is_pb_args(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "add", ("R1",), kind="rule", when="a claim has no source", then="say so")
    assert refusal(w, "edit", ("R1",), item="P1", then="x").endswith("P1 is a step: pass text. Nothing was written.")
    assert refusal(w, "edit", ("R1",), item="P4", text="x").endswith("P4 is a rule: pass then and/or when. Nothing was written.")


def test_a_gated_edit_replaces_the_why(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "add", ("R1",), kind="step", text="Cite every claim.")
    assert meta_of(w)[0]["why"] == {"P4": ["R1"]}
    change = revise(w, "edit", ("R2", "C2"), item="P4", text="Cite every claim with its source URL.")
    meta, body = meta_of(w)
    assert (change.formatting, change.admission.rule) == (False, "b") and meta["why"] == {"P4": ["R2", "C2"]}  # replaced, never merged with R1
    assert body.splitlines()[-1] == "4. [P4] Cite every claim with its source URL. (WHY R2; C2)"
    assert (meta["op"], meta["item"], meta["evidence"]) == ("edit", "P4", ["R2", "C2"])


def test_a_gated_edit_of_a_rule_changes_its_then_or_its_when(w: ServicesWorld) -> None:
    define(w)
    revise(w, "add", ("R1",), kind="rule", when="a claim has no source", then="say so")
    revise(w, "edit", ("R1",), item="P1", then="say so in the review task")
    assert meta_of(w)[1] == "## Rules\n- [P1] WHEN a claim has no source THEN say so in the review task WHY R1"
    revise(w, "edit", ("R1",), item="P1", when="always")
    assert meta_of(w)[1] == "## Rules\n- [P1] WHEN always THEN say so in the review task WHY R1"
    assert refusal(w, "edit", ("R1",), item="P1", when="ALWAYS").startswith("refused: no change: P1 already reads so.")  # `always` in any case is one value


def test_a_formatting_edit_is_exempt_and_keeps_the_why(refusing: ServicesWorld) -> None:
    w = refusing
    define(w)
    meta = {"service": SERVICE, "version": 1, "revised": "2026-01-01T00:00:00+00:00", "by": "ceo", "reason": "earlier", "items_max": 1, "rules": [],
            "why": {"P1": ["R1", "C2"]}, "op": "add", "item": "P1", "admitted": "b", "evidence": ["R1"]}
    w.store.write_playbook("ceo", SERVICE, 1, meta, "## Steps\n1. [P1] Cite every claim. (WHY R1; C2)", None)
    change = revise(w, "edit", item="P1", text="**Cite** every claim")  # the same tokens: no gate (the refusing stand-in would refuse a gated one)
    new, body = meta_of(w)
    assert change.formatting is True and change.admission.rule == "exempt" and new["admitted"] == "exempt" and new["why"] == {"P1": ["R1", "C2"]}
    assert body == "## Steps\n1. [P1] **Cite** every claim (WHY R1; C2)" and "evidence" not in new
    assert refusal(w, "edit", item="P1", text="Cite every claim twice") == "refused by the stand-in for the gate"  # one more word is gated


# ============================================================================================== retire


def test_retire_removes_the_item_from_the_body_and_keeps_its_text_in_history(w: ServicesWorld) -> None:
    seeded(w)
    change = revise(w, "retire", reason="the step is wrong", item="P2")
    meta, body = meta_of(w)
    assert body == "## Steps\n1. [P1] Search.\n2. [P3] Check every claim." and (change.items, change.admission.rule) == (2, "exempt")
    assert (meta["op"], meta["item"], meta["admitted"], meta["items_max"]) == ("retire", "P2", "exempt", 3)
    assert "[P2] Write." in (w.text(HISTORY.format(1)) or "")


def test_retiring_the_last_item_leaves_an_empty_item_list(w: ServicesWorld) -> None:
    seeded(w, "Only step.")
    change = revise(w, "retire", item="P1")
    meta, body = meta_of(w)
    assert body == "" and meta["items_max"] == 1 and change.items == 0
    found = w.catalog.read_playbook("ceo", SERVICE)
    assert found.items == () and found.parse_error == "" and found.version == 2
    assert playbook_reply(SERVICE, change).endswith(
        'root was told without being woken. The playbook has no items now: add one (op="add") when the evidence calls for it.'
    )
    assert revise(w, "add", ("R1",), kind="step", text="Again.").item == "P2"  # an id is never reused


def test_retiring_the_last_rule_drops_the_rules_section(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "add", ("R1",), kind="rule", then="a rule")
    revise(w, "retire", item="P4")
    meta, body = meta_of(w)
    assert body == "## Steps\n1. [P1] Search.\n2. [P2] Write.\n3. [P3] Check every claim." and meta["rules"] == []


# ============================================================================================== the migration (4.4)


def test_the_first_change_of_a_legacy_playbook_migrates_it_first_and_the_reply_says_so(w: ServicesWorld) -> None:
    define(w)
    legacy(w, "## Steps\n1. Search.\n2. Write.\n\n## Pitfalls\nnone yet")
    change = revise(w, "add", ("R1",), kind="step", text="Cite every claim.")
    assert (change.version, change.migrated, change.item) == (3, 2, "P4")
    migrated, mbody = meta_of(w, HISTORY.format(2))
    assert (migrated["op"], migrated["admitted"], migrated["by"], migrated["items_max"], migrated["version"]) == ("migrate", "migrate", "runtime (migration)", 3, 2)
    assert migrated["reason"] == "the free-text v1 as 3 items (no change of words)" and mbody == "## Steps\n1. [P1] Search.\n2. [P2] Write.\n\n## Pitfalls\n- [P3] none yet"
    assert meta_of(w, HISTORY.format(1))[1] == "## Steps\n1. Search.\n2. Write.\n\n## Pitfalls\nnone yet"  # the legacy file, byte for byte
    assert playbook_reply(SERVICE, change).startswith(
        "playbook v2 is the free-text v1 as 3 items (P1-P3, no change of words). playbook of weekly-brief is now v3: added P4 (step), admitted (b) on R1."
    )
    note = [m.body for m in w.d.inbox("root")][-1]
    assert note.startswith("Playbook v2 is the free text of v1 as 3 items (P1-P3), no change of words.\n")
    assert [e.fields["by"] for e in w.events.events if e.kind == "service.revise"] == ["runtime (migration)", "ceo"]
    assert [e.actor for e in w.events.events if e.kind == "service.revise"] == ["runtime", "ceo"]


def test_a_refused_op_leaves_the_migration_written_with_its_own_note(refusing: ServicesWorld) -> None:
    w = refusing
    define(w)
    legacy(w, "## Steps\n1. Search.\n2. Write.")
    assert refusal(w, "add", ("R1",), kind="step", text="x") == "refused by the stand-in for the gate"
    found = w.catalog.read_playbook("ceo", SERVICE)
    assert found.version == 2 and found.op == "migrate" and found.items is not None and [i.id for i in found.items] == ["P1", "P2"]
    (note,) = [m for m in w.d.inbox("root")]
    assert note.title == "playbook of weekly-brief: v2 (items)"
    assert note.body == "The free text of v1 as 2 items (P1-P2), no change of words. Nothing else changed."
    assert refusal(w, "add", ("R1",), kind="step", text="x") == "refused by the stand-in for the gate"  # the second refusal migrates nothing again
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2 and len(w.d.inbox("root")) == 1


def test_a_refusal_before_the_migration_writes_nothing(w: ServicesWorld) -> None:
    define(w)
    legacy(w, "## Steps\n1. Search.")
    assert refusal(w, "add", kind="step", text="") == "refused: text is empty. Nothing was written."  # the argument checks come first
    assert w.catalog.read_playbook("ceo", SERVICE).version == 1
    assert refusal(w, "retire", item="P7").startswith("refused: `weekly-brief` has no live item P7. Its items: P1.")  # the ids exist after the migration
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2


def test_an_empty_legacy_body_migrates_to_no_items(w: ServicesWorld) -> None:
    define(w)
    legacy(w, "")
    change = revise(w, "add", ("R1",), kind="step", text="First.")
    assert (change.migrated, change.item, change.version) == (2, "P1", 3)
    assert meta_of(w, HISTORY.format(2))[0]["reason"] == "the free-text v1 as 0 items (no change of words)"


# ============================================================================================== the repair of a hand-broken item file (4.4)

BROKEN = "## Steps\n1. [P1] Search.\n2. [P2] Write.\nhand-written words"
PARSE_ERROR = "line 4: not a heading, an item (`<n>. [P<k>] ` or `- [P<k>] `) or a line indented by 3 spaces under one"


def test_a_hand_broken_item_file_is_repaired_word_for_word(w: ServicesWorld) -> None:
    define(w)
    owner_wrote(w, 1, BROKEN, 2)
    assert w.catalog.read_playbook("ceo", SERVICE).parse_error == PARSE_ERROR
    change = revise(w, "add", ("R1",), kind="step", text="Publish.")
    repaired, body = meta_of(w, HISTORY.format(2))
    assert (change.version, change.migrated, change.item) == (3, 2, "P5")  # new ids start at items_max + 1; none is reused
    assert (repaired["op"], repaired["admitted"], repaired["by"], repaired["items_max"], repaired["rules"], repaired["why"]) == (
        "migrate", "migrate", "runtime (migration)", 4, [], {},
    )
    assert repaired["reason"] == (
        f"v1 was changed outside revise_playbook and is not in item form ({PARSE_ERROR}); its text as 2 items P3-P4 (no change of words)"
    )
    assert body == "## Steps\n1. [P3] [P1] Search.\n2. [P4] [P2] Write.\n   hand-written words"  # every word of the file, the old markers as words
    assert meta_of(w, HISTORY.format(1))[1] == BROKEN  # the file as it was, byte for byte
    assert playbook_reply(SERVICE, change).startswith(
        "playbook v2 is v1, which was changed outside revise_playbook, as 2 new items (P3-P4, no change of words). playbook of weekly-brief is now v3: added P5 (step)"
    )
    note = [m.body for m in w.d.inbox("root")][-1]
    assert note.startswith(f"Playbook v2 is v1, which was changed outside revise_playbook ({PARSE_ERROR}), as 2 new items (P3-P4), no change of words.\n")
    assert [e.fields["by"] for e in w.events.events if e.kind == "service.revise"] == ["runtime (migration)", "ceo"]


def test_the_old_ids_read_retired_and_the_new_items_are_kept(w: ServicesWorld) -> None:
    define(w)
    owner_wrote(w, 1, BROKEN, 2)
    revise(w, "add", ("R1",), kind="step", text="Publish.")
    found = w.catalog.read_playbook("ceo", SERVICE)
    assert found.parse_error == "" and found.items is not None and [i.id for i in found.items] == ["P3", "P4", "P5"] and found.items_max == 5
    assert refusal(w, "edit", ("R1",), item="P1", text="x") == (
        "refused: `weekly-brief` has no live item P1. Its items: P3, P4, P5; retired: P1, P2 (op=\"restore\" brings one back). Nothing was written."
    )
    assert all(i.why == () for i in found.items[:2])  # a repaired item has no WHY: it was never gated


def test_a_refused_op_leaves_the_repair_written_with_its_own_note(refusing: ServicesWorld) -> None:
    w = refusing
    define(w)
    owner_wrote(w, 1, BROKEN, 2)
    assert refusal(w, "add", ("R1",), kind="step", text="x") == "refused by the stand-in for the gate"
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2
    (note,) = w.d.inbox("root")
    assert note.title == "playbook of weekly-brief: v2 (items)"
    assert note.body == f"v1 was changed outside revise_playbook and is not in item form ({PARSE_ERROR}); its text as 2 items (P3-P4), no change of words. Nothing else changed."


def test_the_repair_keeps_the_fallbacks_of_4_4(tmp_path: Path) -> None:
    from hirearchy.services._items import FALLBACK_SECTIONS, split_sections, split_whole
    from hirearchy.services._ops import RuleItemReviser
    from hirearchy.services._texts import CappedPlaybookTexts, EventedPlaybookWriter
    from hirearchy.dispatch.testing import PostedDelivery

    w = populated(fs_world(tmp_path))
    define(w)
    owner_wrote(w, 1, BROKEN, 2)

    def lossy(body: str) -> Any:  # a per-block split that drops every line: the loss check refuses it and the next split is tried
        return (), ()

    reviser = RuleItemReviser(
        w.d.agents, w.catalog, CappedPlaybookTexts(w.d.settings), EventedPlaybookWriter(w.store, w.d.clock, w.events), PostedDelivery(w.d.post),
        AdmittingServiceEvidence(), w.d.mail, splitters=(lossy, split_sections, split_whole),
    )
    change = reviser.revise_playbook("ceo", SERVICE, "add", "why", ["R1"], kind="step", text="Publish.")
    repaired, body = meta_of(w, HISTORY.format(2))
    assert repaired["reason"].endswith(f"its text as 1 items P3-P3 (no change of words){FALLBACK_SECTIONS}")
    assert change.migration == (
        f"playbook v2 is v1, which was changed outside revise_playbook, as 1 new items (P3-P3, no change of words{FALLBACK_SECTIONS}). "
    )
    assert body == "## Steps\n- [P3] 1. [P1] Search.\n   2. [P2] Write.\n   hand-written words"  # one item for the section, its lines verbatim


def test_a_warned_rule_whose_line_was_untouched_stays_warning_after_the_repair(svc: Any) -> None:
    """Carried watch (ii): a hand edit of the file must not clear a warning. The real gate and the real watch, through the application."""
    from testkit.services_world import confirmed_amendment, deliver
    from testkit.services_world import request as ask

    org = svc
    week = "Names the week it covers"
    c3 = confirmed_amendment(org, week)  # type: ignore[no-untyped-call]  # R1 is answered and C3 is the user's
    org.revise_playbook("ceo", SERVICE, "add", "the client's rule", [c3], kind="rule", then=week)  # (c): P1, WHY R1; C3
    task = ask(org, "again")  # type: ignore[no-untyped-call]
    deliver(org, "ceo", task)  # type: ignore[no-untyped-call]
    no = org.feedback("root", task.id, "reject", "No week.", source="human")
    org.feedback("root", task.id, "reject", "Yes, C3.", source="human", criterion=["C3"], confirms=no.id)
    org.revise_playbook("ceo", SERVICE, "edit", "format it", [], item="P1", then=week.upper())  # exempt (the same tokens): v2 holds the rule, and it is parseable
    before = {i.id: i for i in org.runtime.service_evidence.watch("ceo", SERVICE)}
    assert (before["P1"].state, before["P1"].related) == ("warning", ("R2",))
    path = org.dir("ceo") / "services" / SERVICE / "PLAYBOOK.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nhand-written words\n", encoding="utf-8")  # a hand edit that leaves the rule's line alone
    assert org.runtime.service_catalog.read_playbook("ceo", SERVICE).parse_error
    with pytest.raises(OrgError, match="has no live item P9"):
        org.revise_playbook("ceo", SERVICE, "edit", "after the hand edit", [c3], item="P9", text="x")  # refused, but the repair is written first
    after = {i.id: i for i in org.runtime.service_evidence.watch("ceo", SERVICE)}
    assert after["P1"].state == "retired"  # the old id is no longer live
    repaired = after["P2"]  # the rule's line, now the words of a step
    assert (repaired.state, repaired.carried, repaired.related, repaired.watch_start) == ("warning", "P1", ("R2",), before["P1"].watch_start)


# ============================================================================================== the frontmatter, the write and the note


def test_the_frontmatter_after_each_op(w: ServicesWorld) -> None:
    define(w)
    revise(w, "first", ("C1", "r2"), reason="one", text="## Steps\n1. Search.")
    meta, _ = meta_of(w)
    assert {k: meta[k] for k in ("version", "by", "reason", "evidence", "admitted", "items_max", "rules", "why", "op")} == {
        "version": 1, "by": "ceo", "reason": "one", "evidence": ["C1", "R2"], "admitted": "first", "items_max": 1, "rules": [], "why": {}, "op": "first",
    } and "item" not in meta
    revise(w, "add", ("R1", "R2"), reason="two", kind="rule", when="a claim has no source", then="say so")
    meta, _ = meta_of(w)
    assert list(meta) == ["service", "version", "revised", "by", "reason", "evidence", "admitted", "item", "items_max", "rules", "why", "op"]
    assert (meta["version"], meta["evidence"], meta["admitted"], meta["item"], meta["items_max"], meta["rules"], meta["why"], meta["op"]) == (
        2, ["R1", "R2"], "b", "P2", 2, ["P2"], {"P2": ["R1", "R2"]}, "add",
    )
    revise(w, "edit", ("R1",), reason="three", item="P1", text="Search twice.")
    meta, _ = meta_of(w)
    assert (meta["version"], meta["op"], meta["item"], meta["admitted"], meta["evidence"], meta["items_max"], meta["rules"]) == (
        3, "edit", "P1", "b", ["R1"], 2, ["P2"],
    ) and meta["why"] == {"P1": ["R1"], "P2": ["R1", "R2"]}
    revise(w, "retire", reason="four", item="P2")
    meta, _ = meta_of(w)
    assert (meta["version"], meta["op"], meta["item"], meta["admitted"], meta["items_max"], meta["rules"], meta["why"]) == (
        4, "retire", "P2", "exempt", 2, [], {"P1": ["R1"]},
    ) and "evidence" not in meta and "restores" not in meta and "acknowledged" not in meta


def test_the_versions_are_archived_and_the_client_is_told_quietly(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "add", ("R1",), kind="step", text="Publish.")
    assert "[P3] Check every claim." in (w.text(HISTORY.format(1)) or "") and meta_of(w)[0]["version"] == 2
    notes = [m for m in w.d.inbox("root") if m.sender == "runtime"]
    assert [n.title for n in notes] == [f"playbook of {SERVICE} revised to v1", f"playbook of {SERVICE} revised to v2"] and all(n.wake is False for n in notes)


def test_roots_note_names_ids_only_and_an_agent_clients_keeps_the_text(w: ServicesWorld) -> None:
    """D12: an item is an instruction written for the team, so the note to the human client carries ids, not the item's words."""
    define(w)
    revise(w, "add", ("R1", "R2"), reason="the rejections", kind="step", text="Cite every claim with its source URL.")
    (note,) = [m for m in w.d.inbox("root") if m.sender == "runtime"]
    assert note.body == (
        "ceo revised the playbook of service `weekly-brief` to v1: added P1 (step).\nReason: the rejections\n"
        "Evidence: R1, R2; admitted: admitted by the stand-in for the gate\nFile: ceo/services/weekly-brief/PLAYBOOK.md"
    )
    assert "Cite every claim" not in note.body
    define(w, owner="ceo/eng", name="inner", actor="ceo")
    w.commands.revise_playbook("ceo/eng", "inner", "add", "for the agent", ["R1"], kind="step", text="Cite every claim with its source URL.")
    (told,) = [m for m in w.d.inbox("ceo") if m.sender == "runtime"]
    assert "Text: Cite every claim with its source URL." in told.body and "added P1 (step)" in told.body


def test_the_round_trip_is_asserted_before_every_write(w: ServicesWorld) -> None:
    rule = PlaybookItem("P1", "rule", "## Rules", "then", "a THEN b")  # a `when` with the separator in it would read back as another rule
    from hirearchy.services import PlaybookSection

    with pytest.raises(AssertionError, match="does not parse back as written"):
        checked_body([rule], [PlaybookSection("## Rules", False, ("P1",))], {"items_max": 1, "rules": ["P1"]})


class Racing:
    """A writer that finds the playbook at another version when it writes (the watch settler in the other process)."""

    def __init__(self, inner: Any, now: int) -> None:
        self._inner = inner
        self._now = now

    def write(self, *args: Any, **kw: Any) -> str:
        raise PlaybookRace(self._now)


def test_a_concurrent_write_is_pb_race(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path, playbooks=lambda inner: Racing(inner, 5)))
    define(w)
    assert refusal(w, "first", text=FIRST) == (
        "refused: the playbook of `weekly-brief` changed while this call ran (now v5), so this change was not written: call again."
    )
    assert w.text(PLAYBOOK) is None


# ============================================================================================== restore (5.1: an item's earlier text comes back)


def owner_wrote(w: ServicesWorld, version: int, body: str, items_max: int, rules: tuple[str, ...] = (), why: dict[str, list[str]] | None = None, by: str = "ceo") -> None:
    """The files hold an item-form version that `by` wrote (a change admitted earlier), whatever the gate says now."""
    meta = {
        "service": SERVICE, "version": version, "revised": f"2026-01-0{version}T00:00:00+00:00", "by": by, "reason": "earlier", "items_max": items_max,
        "rules": list(rules), "why": why or {}, "op": "edit", "admitted": "b" if by == "ceo" else "first",
    }
    w.store.write_playbook("ceo", SERVICE, version, meta, body, version - 1 or None)


def test_restore_brings_back_an_items_earlier_text_placed_by_4_1(w: ServicesWorld) -> None:
    seeded(w)  # P1-P3, written by the owner
    revise(w, "retire", item="P2")
    change = revise(w, "restore", ("R1",), item="P2")
    meta, body = meta_of(w)
    assert body == "## Steps\n1. [P1] Search.\n2. [P2] Write. (WHY R1)\n3. [P3] Check every claim."  # back after its nearest live predecessor
    assert (change.version, change.op, change.item, change.kind, change.restored_from, change.items) == (3, "restore", "P2", "step", 1, 3)
    assert (meta["op"], meta["item"], meta["restores"], meta["admitted"], meta["evidence"], meta["why"], meta["items_max"]) == (
        "restore", "P2", 1, "b", ["R1"], {"P2": ["R1"]}, 3,
    )
    revise(w, "edit", ("R1",), item="P1", text="Search twice.")
    again = revise(w, "restore", ("R2",), item="P1")  # a live item: its latest text before the current one comes back, in place
    assert again.restored_from == 3 and meta_of(w)[1].splitlines()[1] == "1. [P1] Search. (WHY R2)"  # v3 is the latest version that held it


def test_restore_of_a_retired_item_takes_its_last_live_text(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "edit", ("R1",), item="P1", text="Search twice.")
    revise(w, "edit", ("R1",), item="P1", text="Search three times.")
    revise(w, "retire", item="P1")
    change = revise(w, "restore", ("R1",), item="p1")
    assert change.restored_from == 3 and meta_of(w)[1].splitlines()[1] == "1. [P1] Search three times. (WHY R1)"
    assert change.item == "P1" and change.items == 3


def test_restore_of_a_client_written_text_is_exempt_and_of_any_other_is_gated(refusing: ServicesWorld) -> None:
    w = refusing
    define(w, playbook=STEPS)  # v1 is root's: P1-P3
    owner_wrote(w, 2, "## Steps\n1. [P1] Search.\n2. [P2] Write twice.\n3. [P3] Check every claim.", 3)
    owner_wrote(w, 3, "## Steps\n1. [P1] Search.\n2. [P2] Write three times.\n3. [P3] Check every claim.", 3)
    assert refusal(w, "restore", item="P2", version=2) == "refused by the stand-in for the gate"  # the owner's own text goes to the gate
    change = revise(w, "restore", item="P2", version=1)  # the client's: no evidence needed
    meta, body = meta_of(w)
    assert (change.admission.rule, change.restored_from, meta["admitted"], meta["restores"]) == ("restore", 1, "restore", 1)
    assert "evidence" not in meta and body.splitlines()[2] == "2. [P2] Write." and meta["version"] == 4
    assert playbook_reply(SERVICE, change) == (
        "playbook of weekly-brief is now v4: restored P2 to the text of v1 (written by root: no evidence needed). root was told without being woken."
    )
    (note,) = [m.body for m in w.d.inbox("root") if m.title == "playbook of weekly-brief revised to v4"]
    assert "restored P2 to the text of v1.\nReason: because\nEvidence: none; restores the text of v1, which you wrote (no evidence needed)" in note


def test_restore_writes_the_why_the_text_had_when_it_was_live(refusing: ServicesWorld) -> None:
    w = refusing
    define(w)
    owner_wrote(w, 1, "## Steps\n1. [P1] Search. (WHY R1, R2; C2)", 1, why={"P1": ["R1", "R2", "C2"]}, by="root")  # a client-written version with its WHY
    owner_wrote(w, 2, "## Steps\n1. [P1] Search twice.", 1)
    change = revise(w, "restore", item="P1")
    meta, body = meta_of(w)
    assert change.restored_from == 1 and meta["why"] == {"P1": ["R1", "R2", "C2"]} and body == "## Steps\n1. [P1] Search. (WHY R1, R2; C2)"


def test_a_gated_restore_writes_the_why_of_its_own_admission(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "edit", ("R1",), item="P2", text="Write twice.")
    revise(w, "restore", ("R5", "C2"), item="P2")
    assert meta_of(w)[0]["why"] == {"P2": ["R5", "C2"]}


def test_restore_without_an_earlier_text_is_pb_args(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "edit", ("R1",), item="P3", text="Check twice.")
    needed = "item, and optionally version and acknowledged"
    assert refusal(w, "restore", item="P1") == (
        f'refused: op="restore" takes {needed}; P1 has no earlier text: it has read so since v1, so there is nothing to restore. Nothing was written.'
    )
    assert refusal(w, "restore", item="P3", version=2).endswith("P3 already reads so. Change an item only when the evidence calls for a different way of working. Nothing was written.")


def test_a_version_that_does_not_hold_the_item_is_pb_args(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "add", ("R1",), kind="step", text="Publish.")
    needed = "item, and optionally version and acknowledged"
    assert refusal(w, "restore", item="P4", version=1) == f'refused: op="restore" takes {needed}; version=1 does not hold P4. Nothing was written.'
    assert refusal(w, "restore", item="P1", version=9) == f'refused: op="restore" takes {needed}; version=9 does not hold P1. Nothing was written.'


def test_a_restore_to_the_current_text_is_pb_same(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "edit", ("R1",), item="P3", text="Check twice.")
    assert refusal(w, "restore", item="P2", version=1) == (
        "refused: no change: P2 already reads so. Change an item only when the evidence calls for a different way of working. Nothing was written."
    )


def test_restore_of_an_id_that_never_existed_is_pb_item(w: ServicesWorld) -> None:
    seeded(w)
    assert refusal(w, "restore", item="P9") == "refused: `weekly-brief` has no live item P9. Its items: P1, P2, P3. Nothing was written."


def test_restore_of_a_rule_goes_back_to_the_rules_section(w: ServicesWorld) -> None:
    define(w)
    revise(w, "add", ("R1",), kind="rule", when="a claim has no source", then="say so")
    revise(w, "retire", item="P1")
    assert meta_of(w)[1] == ""
    revise(w, "restore", ("R1",), item="P1")
    meta, body = meta_of(w)
    assert body == "## Rules\n- [P1] WHEN a claim has no source THEN say so WHY R1" and meta["rules"] == ["P1"]


def test_restore_after_a_migration_restores_a_migrated_items_text(w: ServicesWorld) -> None:
    define(w, playbook="## Steps\n1. Search.\n2. Write.")  # root's v1: items P1, P2 (by root)
    revise(w, "edit", ("R1",), item="P1", text="Search twice.")
    change = revise(w, "restore", item="P1")  # the text root wrote: exempt
    assert change.admission.rule == "restore" and meta_of(w)[1].splitlines()[1] == "1. [P1] Search."


# ============================================================================================== move


def test_move_reorders_within_the_section_and_needs_no_evidence(refusing: ServicesWorld) -> None:
    w = refusing
    define(w, playbook=STEPS)
    change = revise(w, "move", item="P3", after="P1")
    meta, body = meta_of(w)
    assert body == "## Steps\n1. [P1] Search.\n2. [P3] Check every claim.\n3. [P2] Write."
    assert (change.op, change.item, change.after, change.admission.rule, meta["op"], meta["item"], meta["admitted"]) == ("move", "P3", "P1", "exempt", "move", "P3", "exempt")
    assert "evidence" not in meta and playbook_reply(SERVICE, change) == (
        "playbook of weekly-brief is now v2: moved P3 after P1 (no evidence needed). root was told without being woken."
    )
    revise(w, "move", item="P2", after="start")
    assert meta_of(w)[1] == "## Steps\n1. [P2] Write.\n2. [P1] Search.\n3. [P3] Check every claim."
    assert meta_of(w)[0]["items_max"] == 3 and meta_of(w)[0]["version"] == 3


def test_a_move_inside_the_rules_section(w: ServicesWorld) -> None:
    define(w)
    revise(w, "add", ("R1",), kind="rule", then="one")
    revise(w, "add", ("R1",), kind="rule", then="two")
    revise(w, "move", item="P2", after="start")
    assert meta_of(w)[1] == "## Rules\n- [P2] WHEN always THEN two WHY R1\n- [P1] WHEN always THEN one WHY R1" and meta_of(w)[0]["rules"] == ["P2", "P1"]


def test_a_no_op_move_is_pb_same(w: ServicesWorld) -> None:
    seeded(w)
    same = "Change an item only when the evidence calls for a different way of working. Nothing was written."
    assert refusal(w, "move", item="P2", after="P1") == f"refused: no change: P2 already comes after P1. {same}"
    assert refusal(w, "move", item="P1", after="start") == f"refused: no change: P1 is already first in its section. {same}"
    assert refusal(w, "move", item="P2", after="P2") == f"refused: no change: P2 already comes after P2. {same}"
    assert w.catalog.read_playbook("ceo", SERVICE).version == 1


def test_move_after_an_item_of_another_section_is_pb_args(w: ServicesWorld) -> None:
    define(w, playbook="## Steps\n1. Search.\n\n## Budget plan\n- 12 runs.")
    needed = 'item and after (an item id of its section, or "start")'
    assert refusal(w, "move", item="P1", after="P2") == f'refused: op="move" takes {needed}; after=P2 is not an item of P1\'s section. Nothing was written.'
    assert refusal(w, "move", item="P1", after="P9") == f'refused: op="move" takes {needed}; after=P9 is not an item of P1\'s section. Nothing was written.'


MOVE_ARGS = [
    ("move", {"item": "P1"}, 'item and after (an item id of its section, or "start")', "after is missing"),
    ("move", {"after": "P2"}, 'item and after (an item id of its section, or "start")', "item is missing"),
    ("move", {"item": "P1", "after": "P2", "text": "x"}, 'item and after (an item id of its section, or "start")', 'text does not go with op="move"'),
    ("restore", {}, "item, and optionally version and acknowledged", "item is missing"),
    ("restore", {"item": "P1", "after": "P2"}, "item, and optionally version and acknowledged", 'after does not go with op="restore"'),
    ("restore", {"item": "P1", "text": "x", "kind": "step"}, "item, and optionally version and acknowledged", 'kind does not go with op="restore"; text does not go with op="restore"'),
]


@pytest.mark.parametrize(("op", "kw", "needed", "wrong"), MOVE_ARGS)
def test_pb_args_of_restore_and_move(w: ServicesWorld, op: str, kw: dict[str, Any], needed: str, wrong: str) -> None:
    seeded(w)
    assert refusal(w, op, **kw) == f'refused: op="{op}" takes {needed}; {wrong}. Nothing was written.'
    assert w.catalog.read_playbook("ceo", SERVICE).version == 1


def test_an_unneeded_acknowledged_is_ignored_for_a_restore_too(w: ServicesWorld) -> None:
    seeded(w)
    revise(w, "edit", ("R1",), item="P2", text="Write twice.")
    ack = "20261024T000000000001-root-ab12"
    change = revise(w, "restore", ("R1",), item="P2", acknowledged=ack)
    assert change.ack_ignored == ack and "(acknowledged=" + ack + " was not needed for this change and is not recorded.)" in playbook_reply(SERVICE, change)


# ============================================================================================== the 30% rule (7) and the cap (10)


def words(n: int, tag: str = "") -> str:
    """``n`` distinct words made of letters only (a number or a symbol would be a token of its own)."""
    return " ".join(f"{tag}{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(n))


class CAdmitting(AdmittingServiceEvidence):
    """A gate that admits every item by rule (c): the words of a confirmed criterion are not split by the 30% rule (7)."""

    def admit_item(self, owner: str, service: str, evidence: Sequence[str], reason: str, *, kind: str, text: str, when: str | None) -> Admission:
        return Admission("c", normalize_evidence(evidence), "cites C3", why=("R1", "C3"))


def big(w: ServicesWorld, n: int = 100) -> ServicesWorld:
    """The service is defined and its owner has written v1: one step of ``n`` words (``n + 1`` tokens with the heading)."""
    define(w)
    revise(w, "first", text=f"## Steps\n1. {words(n)}")
    return w


def test_a_gated_add_edit_or_restore_above_the_limit_is_pb_split(w: ServicesWorld) -> None:
    big(w)  # base 101: the limit is the floor of 50
    revise(w, "add", ("R1",), kind="step", text=words(50, "n"))  # exactly 50 words touched: allowed
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2
    message = refusal(w, "add", ("R1",), kind="step", text=words(61, "m"))  # base 151: still the floor
    assert message == (
        "refused: this change touches 61 of the playbook's 151 words, more than about 30% (50): make it as smaller changes (one item, or part of an "
        "item, per call), each with its own reason and evidence, so each one is judged and watched on its own. Nothing was written."
    )
    old = words(100).split()
    swapped = " ".join([*old[:50], *words(50, "z").split()])  # 50 words gone and 50 new: 100 touched
    assert refusal(w, "edit", ("R1",), item="P1", text=swapped).startswith("refused: this change touches 100 of the playbook's 151 words")
    revise(w, "edit", ("R1",), item="P1", text=" ".join([*old[:97], "xxx", "yyy", "zzz"]))  # six words touched: allowed
    assert w.catalog.read_playbook("ceo", SERVICE).version == 3


def test_a_gated_restore_and_an_exempt_restore_of_the_clients_text_take_the_rule_too(refusing: ServicesWorld) -> None:
    w = refusing
    define(w, playbook=f"## Steps\n1. {words(100)}")  # root's v1: base 101
    owner_wrote(w, 2, f"## Steps\n1. [P1] {words(100, 'o')}", 1)  # the owner's text
    owner_wrote(w, 3, f"## Steps\n1. [P1] {words(100, 'p')}", 1)
    assert refusal(w, "restore", item="P1", version=1).startswith("refused: this change touches 200 of the playbook's 101 words, more than about 30% (50)")
    assert refusal(w, "restore", item="P1", version=2) == "refused by the stand-in for the gate"  # the gate comes before the split


def test_a_c_admission_takes_no_split_check(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path, CAdmitting()))
    big(w)
    change = revise(w, "add", ("C3",), kind="step", text=words(120, "c"))  # 120 words touched, over the floor of 50: a criterion's words cannot be split
    assert change.admission.rule == "c" and change.version == 2


def test_formatting_fixes_retires_and_moves_take_no_split_check(refusing: ServicesWorld) -> None:
    w = refusing
    define(w, playbook=f"## Steps\n1. {words(100)}\n2. {words(100, 'q')}")
    revise(w, "move", item="P2", after="start")
    revise(w, "edit", item="P1", text=words(100).upper())  # the same tokens
    revise(w, "retire", item="P2")  # 100 words gone
    assert w.catalog.read_playbook("ceo", SERVICE).version == 4


def test_an_add_over_playbook_max_words_is_pb_cap_with_its_lists(w: ServicesWorld) -> None:
    big(w, 30)  # content words: the heading's two and 30
    w.d.configure("---\nmission: test\nplaybook_max_words: 41\n---\nrules\n")
    revise(w, "add", ("R1",), kind="step", text=words(9, "a"))  # 41 words: at the cap
    assert refusal(w, "add", ("R1",), kind="step", text="one two") == (
        "refused: the playbook would have 43 words; the limit is 41 (playbook_max_words). Retire an item first. "
        "Items that cover no criterion or assertion (no acknowledgement needed): P1 (since v1), P2 (since v2). "
        'Or shorten an item (op="edit"). Nothing was written.'
    )
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2


def test_the_cap_names_new_items_whose_watch_rests_on_no_regression_assertion(tmp_path: Path) -> None:
    watch = (ItemWatch("P1", "step", "kept", 1, coverage=("C1",)), ItemWatch("P2", "step", "new", 1, coverage=("C2",)), ItemWatch("P3", "step", "kept", 1))
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(watch=watch)))
    define(w)
    owner_wrote(w, 1, "## Steps\n1. [P1] one\n2. [P2] two (WHY C2)\n3. [P3] three", 3, why={"P2": ["C2"]})  # P2's watch rests on C2 alone: no R id
    w.d.configure("---\nmission: test\nplaybook_max_words: 5\n---\nrules\n")
    assert refusal(w, "add", ("R1",), kind="step", text="four five") == (
        "refused: the playbook would have 7 words; the limit is 5 (playbook_max_words). Retire an item first. "
        "Candidates, oldest first (new items whose watch rests on no regression assertion): P2 (since v1; cites C2: retiring it needs root's acknowledgement). "
        "Items that cover no criterion or assertion (no acknowledgement needed): P3 (since v1). "
        'Or shorten an item (op="edit"). Nothing was written.'
    )


def test_a_playbook_over_the_cap_where_every_item_covers_something_says_retire_one_yourself(tmp_path: Path) -> None:
    watch = (ItemWatch("P1", "step", "kept", 1, coverage=("C1",)),)
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(watch=watch)))
    define(w)
    revise(w, "first", text="## Steps\n1. one two three")
    w.d.configure("---\nmission: test\nplaybook_max_words: 5\n---\nrules\n")
    assert refusal(w, "add", ("R1",), kind="step", text="four") == (
        "refused: the playbook would have 6 words; the limit is 5 (playbook_max_words). Retire an item first. Every item covers a criterion or an "
        "assertion: retire one yourself (it needs root's acknowledgement), or shorten one. Nothing was written."
    )


def test_a_playbook_over_the_cap_still_takes_retires_moves_and_formatting_fixes(w: ServicesWorld) -> None:
    seeded(w)  # content words: the heading's two, "Search.", "Write." and "Check every claim." = 7
    w.d.configure("---\nmission: test\nplaybook_max_words: 3\n---\nrules\n")
    revise(w, "move", item="P3", after="start")
    revise(w, "edit", item="P2", text="WRITE.")
    assert refusal(w, "add", ("R1",), kind="step", text="more").startswith("refused: the playbook would have 8 words; the limit is 3")
    assert refusal(w, "edit", ("R1",), item="P1", text="Search all of it twice.").startswith("refused: the playbook would have 11 words; the limit is 3")
    revise(w, "retire", item="P1")
    assert w.catalog.read_playbook("ceo", SERVICE).version == 4


def test_the_cap_counts_content_words_not_markers(w: ServicesWorld) -> None:
    define(w)
    revise(w, "add", ("R1",), kind="rule", when="a b", then="c d")  # content: the heading's two, then 2 and when 2 = 6; the body has twice as many words
    assert len(w.catalog.read_playbook("ceo", SERVICE).body.split()) == 12
    w.d.configure("---\nmission: test\nplaybook_max_words: 8\n---\nrules\n")
    revise(w, "add", ("R1",), kind="rule", then="e f")  # 6 + 2 (an `always` when counts none) = 8: at the cap
    assert refusal(w, "add", ("R1",), kind="rule", then="g").startswith("refused: the playbook would have 9 words; the limit is 8")


def test_a_legacy_playbook_over_the_cap_migrates_first_and_still_takes_a_retire(w: ServicesWorld) -> None:
    define(w)
    legacy(w, "## Steps\n1. " + words(30) + "\n2. " + words(30, "z"))
    w.d.configure("---\nmission: test\nplaybook_max_words: 10\n---\nrules\n")
    assert refusal(w, "add", ("R1",), kind="step", text="more").startswith("refused: the playbook would have 63 words; the limit is 10")
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2  # the migration stays written
    revise(w, "retire", item="P2")
    assert w.catalog.read_playbook("ceo", SERVICE).version == 3


# ============================================================================================== a watch-retired text stays out (8.6, B2) and a carried watch says so (5.2)

OUT_RULE = "cite every claim"


class FailingWatch(AdmittingServiceEvidence):
    """A gate whose watch cannot be read: the change stands, and the reply says where the states are (19.1)."""

    def watch(self, owner: str, service: str) -> tuple[ItemWatch, ...]:
        raise OrgError("the record cannot be read")


class AfterWrite(AdmittingServiceEvidence):
    """A gate that admits by rule (c) on a criterion the user confirmed at ``confirmed`` (a link note id), as the real one reports it."""

    def __init__(self, confirmed_at: str, watch: Sequence[ItemWatch] = ()) -> None:
        super().__init__(watch=watch)
        self._at = confirmed_at

    def admit_item(self, owner: str, service: str, evidence: Sequence[str], reason: str, *, kind: str, text: str, when: str | None) -> Admission:
        return Admission("c", normalize_evidence(evidence), "cites C3", why=("R1", "C3"), confirmed=self._at)


def watch_retired(
    w: ServicesWorld, *, by: str = "runtime (watch)", op: str = "watch", related: tuple[str, ...] = ("R4", "R6"), restores: int = 0,
) -> None:
    """v1 is the owner's (a step, and the rule P2 with its WHY); v2 removes P2 as the watch's retire (or as the owner's, `op="retire"`) would write it."""
    define(w)
    owner_wrote(w, 1, f"## Steps\n1. [P1] Search.\n\n## Rules\n- [P2] WHEN always THEN {OUT_RULE} WHY R1, R2; C2", 2, rules=("P2",), why={"P2": ["R1", "R2", "C2"]})
    meta: dict[str, object] = {
        "service": SERVICE, "version": 2, "revised": "2026-01-02T00:00:00+00:00", "by": by, "reason": "retired", "items_max": 2, "rules": [], "why": {},
        "op": op, "item": "P2", "admitted": "watch" if op == "watch" else "exempt", **({"related": list(related)} if op == "watch" else {}),
    }
    w.store.write_playbook("ceo", SERVICE, 2, meta, "## Steps\n1. [P1] Search.", 1)


def out_world(tmp_path: Path, watch: Sequence[ItemWatch] | None = None, gate: AdmittingServiceEvidence | None = None) -> ServicesWorld:
    given = (ItemWatch("P1", "step", "kept", 1), ItemWatch("P2", "rule", "retired", 1, related=("R4", "R6"))) if watch is None else tuple(watch)
    tmp_path.mkdir(parents=True, exist_ok=True)
    return populated(fs_world(tmp_path, gate or AdmittingServiceEvidence(watch=given)))


WATCHED_OUT = (
    "refused: this text is P2's text that the watch retired in v2, because the client rejected R4 and R6 on what it cited (R1, R2, C2). It comes back "
    "only as the own words of a criterion the client confirms after that (rule (c)). Nothing was written. If you think the client wants it, send root "
    "(`send`) this question once: \"Your rejections R4 and R6 retired this from how we deliver weekly-brief: cite every claim. Do you want it back "
    "from now on? If yes, please add it to the contract as a criterion.\""
)


def test_pb_watched_out_word_for_word(tmp_path: Path) -> None:
    w = out_world(tmp_path)
    watch_retired(w)
    assert refusal(w, "add", ("R1",), kind="step", text=OUT_RULE) == WATCHED_OUT
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2


def test_an_add_or_restore_of_a_watch_retired_text_is_pb_watched_out(tmp_path: Path) -> None:
    w = out_world(tmp_path)
    watch_retired(w)
    assert refusal(w, "add", ("R1",), kind="step", text="Cite every claim.") == WATCHED_OUT  # the lenient key: punctuation and case do not matter
    assert refusal(w, "add", ("R1",), kind="rule", then="CITE every claim", when="a claim has no source") == WATCHED_OUT  # a rule too: its then
    assert refusal(w, "restore", ("R1",), item="P2") == WATCHED_OUT  # the retired item's last live text
    assert w.catalog.read_playbook("ceo", SERVICE).version == 2
    assert revise(w, "add", ("R1",), kind="step", text="Cite every source twice.").version == 3  # other words are not caught


def test_a_gated_edit_of_another_item_into_a_watch_retired_text_is_pb_watched_out(tmp_path: Path) -> None:
    """B2: the edit would carry the warned text back under another id."""
    w = out_world(tmp_path)
    watch_retired(w)
    assert refusal(w, "edit", ("R1",), item="P1", text=OUT_RULE) == WATCHED_OUT
    assert meta_of(w)[1] == "## Steps\n1. [P1] Search."
    assert revise(w, "edit", item="P1", text="SEARCH.").formatting is True  # a formatting edit is exempt and carries no text over


def test_a_rule_re_added_as_a_step_with_its_thens_words_is_caught(tmp_path: Path) -> None:
    w = out_world(tmp_path)
    watch_retired(w)
    assert refusal(w, "add", ("R1",), kind="step", text="cite  every   CLAIM!") == WATCHED_OUT
    assert refusal(w, "add", ("R1",), kind="rule", then="cite every claim", when="the memo is long") == WATCHED_OUT  # the when is not part of the text key


def test_a_text_its_owner_retired_while_its_retire_was_due_is_pb_watched_out(tmp_path: Path) -> None:
    w = out_world(tmp_path)
    watch_retired(w, by="ceo", op="retire")
    assert refusal(w, "add", ("R1",), kind="step", text=OUT_RULE) == WATCHED_OUT.replace("that the watch retired in v2", "that you retired while the watch's retire of it was due in v2")
    quiet = out_world(tmp_path / "quiet", watch=(ItemWatch("P2", "rule", "retired", 1, related=("R4",)),))  # one related rejection: it was not due
    watch_retired(quiet, by="ceo", op="retire")
    assert revise(quiet, "add", ("R1",), kind="step", text=OUT_RULE).version == 3


def test_a_c_admission_by_a_criterion_confirmed_after_the_retire_passes(tmp_path: Path) -> None:
    after = "20260103T000000000000-root-ab12"  # the user's link, a day after v2 (2026-01-02)
    w = out_world(tmp_path, gate=AfterWrite(after, (ItemWatch("P2", "rule", "retired", 1, related=("R4", "R6")),)))
    watch_retired(w)
    change = revise(w, "add", ("C3",), kind="step", text=OUT_RULE)  # the client made it the contract
    assert change.admission.rule == "c" and change.version == 3
    before = out_world(tmp_path / "before", gate=AfterWrite("20260101T000000000000-root-ab12", (ItemWatch("P2", "rule", "retired", 1, related=("R4", "R6")),)))
    watch_retired(before)
    assert refusal(before, "add", ("C3",), kind="step", text=OUT_RULE) == WATCHED_OUT  # a criterion confirmed before the retire does not bring it back


def test_fewer_than_2_still_related_lets_it_back_as_a_gated_change(tmp_path: Path) -> None:
    """L9: a user's corrected link can undo the relation; with fewer than two of the retire's rejections still related, the text is a gated change."""
    w = out_world(tmp_path, watch=(ItemWatch("P2", "rule", "retired", 1, related=("R4",)),))  # R6 is related no more
    watch_retired(w)
    change = revise(w, "add", ("R7", "R8"), kind="step", text=OUT_RULE)
    assert change.admission.rule == "b" and change.version == 3 and change.item == "P3"


def test_a_text_the_watch_replaced_by_its_previous_one_stays_out(tmp_path: Path) -> None:
    """A watch retire that put the previous text back: the watched text is still out; the restored one is live and takes no refusal."""
    w = out_world(tmp_path)
    define(w)
    owner_wrote(w, 1, "## Steps\n1. [P1] Search.\n2. [P2] older words", 2)
    owner_wrote(w, 2, f"## Steps\n1. [P1] Search.\n2. [P2] {OUT_RULE} (WHY R1, R2; C2)", 2, why={"P2": ["R1", "R2", "C2"]})
    meta: dict[str, object] = {
        "service": SERVICE, "version": 3, "revised": "2026-01-03T00:00:00+00:00", "by": "runtime (watch)", "reason": "retired", "items_max": 2, "rules": [],
        "why": {}, "op": "watch", "item": "P2", "admitted": "watch", "related": ["R4", "R6"], "restores": 1,
    }
    w.store.write_playbook("ceo", SERVICE, 3, meta, "## Steps\n1. [P1] Search.\n2. [P2] older words", 2)
    assert refusal(w, "edit", ("R1",), item="P1", text=OUT_RULE).startswith("refused: this text is P2's text that the watch retired in v3")


def test_a_carried_add_restore_or_edit_reply_names_the_old_id_and_its_rejections(tmp_path: Path) -> None:
    told = "root was told without being woken."
    warned = ItemWatch("P2", "step", "warning", 1, related=("R4", "R6"))
    carried_add = ItemWatch("P3", "step", "warning", 3, related=("R4", "R6"), carried="P2")
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(watch=(warned, carried_add))))
    define(w)
    owner_wrote(w, 1, "## Steps\n1. [P1] Search.\n2. [P2] Write.", 2)
    added = revise(w, "add", ("R1",), kind="step", text="Write.")  # an add with the text of an item its owner retired in warning: P3 continues P2's watch
    assert (added.carried, added.related, added.item) == ("P2", ("R4", "R6"), "P3")
    assert playbook_reply(SERVICE, added) == (
        "playbook of weekly-brief is now v2: added P3 (step), admitted (b) on R1. It continues the watch of P2: warning (R4, R6); one more related "
        f"rejection retires it. {told}"
    )
    edited_watch = ItemWatch("P1", "step", "warning", 3, related=("R2", "R4", "R6"), carried="P2")  # B2: the edited item keeps its own R2 as well
    w2 = out_world(tmp_path / "edit", gate=AdmittingServiceEvidence(watch=(ItemWatch("P1", "step", "warning", 1, related=("R2",)), warned, edited_watch)))
    define(w2)
    owner_wrote(w2, 1, "## Steps\n1. [P1] Search.\n2. [P2] Write.", 2)
    edited = revise(w2, "edit", ("R1",), item="P1", text="Write twice.")
    assert (edited.carried, edited.related, edited.carried_related) == ("P2", ("R2", "R4", "R6"), ("R4", "R6"))
    assert playbook_reply(SERVICE, edited) == (
        "playbook of weekly-brief is now v2: edited P1, admitted (b) on R1. Its watch starts again; its warning stays (R2): one more related rejection "
        f"retires it; it continues the watch of P2: warning (R4, R6), one more related rejection retires it. {told}"
    )
    own = ItemWatch("P1", "step", "warning", 2, related=("R2",))  # an edit of a warned item with no carried watch keeps its own warning
    w3 = out_world(tmp_path / "own", gate=AdmittingServiceEvidence(watch=(own,)))
    define(w3)
    owner_wrote(w3, 1, "## Steps\n1. [P1] Search.", 1)
    kept = revise(w3, "edit", ("R1",), item="P1", text="Search twice.")
    assert playbook_reply(SERVICE, kept) == (
        f"playbook of weekly-brief is now v2: edited P1, admitted (b) on R1. Its watch starts again; its warning stays (R2): one more related rejection retires it. {told}"
    )
    restored_watch = ItemWatch("P1", "step", "warning", 3, related=("R4", "R6"), carried="P1")
    w4 = out_world(tmp_path / "restore", gate=AdmittingServiceEvidence(watch=(restored_watch,)))
    define(w4)
    owner_wrote(w4, 1, "## Steps\n1. [P1] Search.", 1)
    owner_wrote(w4, 2, "## Steps", 1)  # P1 was retired
    back = revise(w4, "restore", ("R1",), item="P1")
    assert playbook_reply(SERVICE, back) == (
        "playbook of weekly-brief is now v3: restored P1 to the text of v1, admitted (b) on R1; it continues the watch of P1: warning (R4, R6), "
        f"one more related rejection retires it. {told}"
    )


def test_a_failed_watch_read_after_the_write_gives_the_fixed_sentence(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path, FailingWatch()))
    define(w)
    add = revise(w, "add", ("R1",), kind="step", text="Cite every claim.")  # the write stands
    assert add.watch_unread is True and w.catalog.read_playbook("ceo", SERVICE).version == 1
    assert playbook_reply(SERVICE, add) == (
        "playbook of weekly-brief is now v1: added P1 (step), admitted (b) on R1. Its watch state is in your prompt's playbook section. "
        "root was told without being woken."
    )
    edit = revise(w, "edit", ("R2",), item="P1", text="Cite every source twice.")
    assert playbook_reply(SERVICE, edit).endswith("edited P1, admitted (b) on R2. Its watch state is in your prompt's playbook section. root was told without being woken.")
    assert playbook_reply(SERVICE, revise(w, "retire", item="P1")) == "playbook of weekly-brief is now v3: retired P1. root was told without being woken. The playbook has no items now: add one (op=\"add\") when the evidence calls for it."


# ============================================================================================== the replies of 5.2


def test_the_replies_of_5_2(w: ServicesWorld) -> None:
    seeded(w)
    told = "root was told without being woken."
    add = revise(w, "add", ("R1",), kind="step", text="Cite every claim.")
    assert playbook_reply(SERVICE, add) == (
        f"playbook of weekly-brief is now v2: added P4 (step), admitted (b) on R1. It starts new and is watched: a related client rejection warns "
        f"it, a second retires it. {told}"
    )
    rule = revise(w, "add", ("R1", "C2"), kind="rule", then="say so")
    assert playbook_reply(SERVICE, rule) == (
        f"playbook of weekly-brief is now v3: added P5 (rule), admitted (b) on R1, C2. It starts new and is watched: a related client rejection "
        f"warns it, a second retires it. {told}"
    )
    gated = revise(w, "edit", ("R2",), item="P4", text="Cite every claim twice.")
    assert playbook_reply(SERVICE, gated) == f"playbook of weekly-brief is now v4: edited P4, admitted (b) on R2. Its watch starts again. {told}"
    fixed = revise(w, "edit", item="P4", text="cite every CLAIM twice")
    assert fixed.formatting is True and playbook_reply(SERVICE, fixed) == (
        f"playbook of weekly-brief is now v5: fixed the formatting of P4 (no evidence needed; its state is unchanged). {told}"
    )
    gone = revise(w, "retire", item="P5")
    assert playbook_reply(SERVICE, gone) == f"playbook of weekly-brief is now v6: retired P5. {told}"
    back = revise(w, "restore", ("R3",), item="P4", version=2)
    assert playbook_reply(SERVICE, back) == f"playbook of weekly-brief is now v7: restored P4 to the text of v2, admitted (b) on R3. {told}"
    moved = revise(w, "move", item="P4", after="start")
    assert playbook_reply(SERVICE, moved) == f"playbook of weekly-brief is now v8: moved P4 after start (no evidence needed). {told}"


def test_an_unneeded_acknowledged_is_ignored_and_the_reply_says_so(w: ServicesWorld) -> None:
    seeded(w)
    ack = "20261024T000000000001-root-ab12"
    gone = revise(w, "retire", item="P2", acknowledged=ack)
    assert (gone.ack_ignored, gone.acknowledged) == (ack, "") and "acknowledged" not in meta_of(w)[0]
    assert playbook_reply(SERVICE, gone) == (
        f"playbook of weekly-brief is now v2: retired P2. (acknowledged={ack} was not needed for this change and is not recorded.) "
        "root was told without being woken."
    )
    edit = revise(w, "edit", ("R1",), item="P1", text="Search twice.", acknowledged=ack)
    assert edit.ack_ignored == ack and "(acknowledged=" in playbook_reply(SERVICE, edit)
