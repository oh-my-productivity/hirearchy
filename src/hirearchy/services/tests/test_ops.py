"""``RuleItemReviser``: ``revise_playbook`` changes one item per call (design 5): first, add, edit and retire, the order of its checks, its refusals
word for word, the migration of a free-text playbook, the replies and the client's note. The gate is the admitting stand-in (the real one is judged in
``reflection``); the refusing one makes a gated change fail."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import Message, OrgError, split_frontmatter
from hirearchy.services import PlaybookChange, PlaybookItem, PlaybookRace, ServiceCommands, playbook_reply
from hirearchy.services._items import checked_body
from hirearchy.services.testing import RefusingServiceEvidence, ServicesWorld, fs_world, memory_world

from ._support import answer, define, populated, request

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


def test_a_criterions_own_words_are_exempt_from_the_keyword_bracket_and_length_rules(w: ServicesWorld) -> None:
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
