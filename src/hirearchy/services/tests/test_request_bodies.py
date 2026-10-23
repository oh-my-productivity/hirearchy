"""``TextRequestBodies``: the body of a request, as markdown."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from hirearchy.kernel import RENDER_BODY_CHARS, Message
from hirearchy.services import BASE_HEADING, Contract, JudgedBase, number_criteria
from hirearchy.services._request import TextRequestBodies

BODIES = TextRequestBodies()


def body(c: Contract, given: Mapping[str, str], extra: Sequence[str], note: str) -> str:
    """The body of a request for ``c``, whose criteria carry the ids of a contract that never changed (C1, C2, ...)."""
    return BODIES.body(c, number_criteria([(1, "root", c.acceptance)]), given, extra, note)


def contract(**over: object) -> Contract:
    base: dict[str, object] = dict(
        name="brief", owner="ceo", description="A brief.", inputs=[{"name": "topic", "description": "t", "required": True}, {"name": "week", "description": "", "required": False}],
        acceptance=["Short"], deliverable={"description": "one file"},
    )
    return Contract(**{**base, **over})  # type: ignore[arg-type]


def test_the_body_has_a_goal_the_request_the_criteria_and_the_deliverable() -> None:
    assert body(contract(), {"topic": "ai"}, [], "") == (
        "## Goal\nDeliver the service `brief`: A brief.\n\n## Request\n- topic: ai\n\n## Acceptance criteria\n- C1: Short\n\n## Deliverable\none file"
    )


def test_the_inputs_follow_the_order_of_the_contract_and_only_those_given_are_listed() -> None:
    both = body(contract(), {"week": "10", "topic": "ai"}, [], "")
    assert "## Request\n- topic: ai\n- week: 10\n\n" in both
    assert "## Request\n- week: 10\n\n" in body(contract(), {"week": "10"}, [], "")


def test_a_value_of_several_lines_is_indented_under_its_item() -> None:
    assert "- topic: a\n  b\n  c\n" in body(contract(), {"topic": "a\nb\nc"}, [], "")


def test_without_inputs_it_says_so() -> None:
    assert "## Request\n(no inputs)\n\n" in body(contract(), {}, [], "")


def test_the_extra_criteria_come_after_the_contracts() -> None:
    assert "## Acceptance criteria\n- C1: Short\n- this request only: More\n- this request only: Even more\n\n" in body(contract(), {}, ["More", "Even more"], "")


def test_the_deliverable_lists_its_format_size_and_path_in_that_order() -> None:
    deliverable = {"description": "a report", "path": "/o.pdf", "max_words": 10, "format": "pdf"}
    assert body(contract(deliverable=deliverable), {}, [], "").endswith("## Deliverable\na report (format: pdf; at most 10 words; path: /o.pdf)")
    assert body(contract(deliverable={"description": "a report", "path": "/o.pdf"}), {}, [], "").endswith("a report (path: /o.pdf)")


def test_the_note_of_the_requester_comes_last_stripped_and_only_when_there_is_one() -> None:
    assert body(contract(), {}, [], "  Be quick.\n").endswith("## Deliverable\none file\n\n## Note from the requester\nBe quick.")
    assert "Note from the requester" not in body(contract(), {}, [], "   ")


def test_the_request_body_lists_contract_criteria_with_ids_and_extras_without() -> None:
    c = contract(acceptance=["B", "D"])
    history = number_criteria([(1, "root", ["A", "B", "C"]), (2, "root", ["B", "D"])])  # A and C were removed; B kept C2, D is C4
    text = BODIES.body(c, [x for x in history if x.current], {}, ["only now"], "")
    assert "## Acceptance criteria\n- C2: B\n- C4: D\n- this request only: only now\n\n## Deliverable" in text
    assert "C1" not in text and "C3" not in text


# ------------------------------------------------------------------------------ the base of a human rework (P4, design 7.3)

TASK, RESULT, RELAYED = "20261010T100000000001-root-f230", "20261010T101000000002-lead-5314", "20261012T100000000003-root-43b8"
PATH = "lead/writer/work/2026-10-05-memo.md"
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def judged(**over: object) -> JudgedBase:
    fields: dict[str, object] = dict(
        task=TASK, result=RESULT, commit=COMMIT, relayed=(RELAYED,), changed=(PATH,), texts=((PATH, "| Marta | 2026-10-14 |"),),
    )
    return JudgedBase(**{**fields, **over})  # type: ignore[arg-type]


def based(base: str, found: JudgedBase | None, note: str = "Fix the date.", extra: Sequence[str] = (), c: Contract | None = None) -> str:
    c = c or contract()
    return BODIES.body(c, number_criteria([(1, "root", c.acceptance)]), {"topic": "ai"}, extra, note, base=(base, found))


def test_base_delivered_is_last_with_the_goal_sentence_and_fenced_texts() -> None:
    text = based("delivered", judged())
    assert BASE_HEADING == "## Base: "
    assert text.startswith(
        "## Goal\nDeliver the service `brief`: A brief. The client's corrections apply to the version they judged: see \"## Base\" at the end of this task.\n\n"
    )
    assert "## Note from the requester\nFix the date.\n\n## Base: the version the client judged\n" in text
    assert text.endswith(
        "## Base: the version the client judged\n"
        f"The client's corrections apply to the version they judged: the delivery of task {TASK} (result {RESULT}, org-git commit {COMMIT[:12]}). "
        f"Relayed rework {RELAYED} (the assistant's own reading, not the client's) changed {PATH} after it. Start from that version: restore each "
        "file below to it, then make only the changes this request asks for.\n\n"
        f"### {PATH}, as the client judged it\n```\n| Marta | 2026-10-14 |\n```"
    )
    assert text.count("## Base: ") == 1


def test_the_base_follows_the_deliverable_when_there_is_no_note() -> None:
    text = based("delivered", judged(), note="")
    assert "## Deliverable\none file\n\n## Base: the version the client judged\n" in text and "Note from the requester" not in text


def test_the_fence_is_longer_than_any_backtick_run() -> None:
    text = based("delivered", judged(texts=((PATH, "a\n````\nb\n``` x\n"),)))
    assert f"### {PATH}, as the client judged it\n`````\na\n````\nb\n``` x\n\n`````" in text
    assert "\n```\n" not in text.replace("``` x", "")


def test_a_path_without_text_says_why() -> None:
    other = "lead/writer/work/other.md"
    text = based("delivered", judged(changed=(PATH, other), texts=((PATH, "kept"),)))
    assert f"### {other}: not included (the judged texts here are limited to 6000 bytes); it is in the organization's git history at commit {COMMIT[:12]}." in text
    nothing = based("delivered", judged(commit="", texts=()))
    assert f"### {PATH}: not included (no org history)." in nothing and "org-git commit" not in nothing
    assert f"(result {RESULT})." in nothing


def test_base_latest_section() -> None:
    text = based("latest", judged(relayed=(RELAYED, "20261012T110000000004-root-aaaa"), changed=(PATH, "x/y.md")))
    assert text.startswith("## Goal\nDeliver the service `brief`: A brief. The client's corrections apply to the current version: see \"## Base\" at the end of this task.\n")
    assert text.endswith(
        "## Base: the current version\n"
        f"The client's corrections apply to the current version, which keeps the changes relayed rework {RELAYED}, 20261012T110000000004-root-aaaa "
        f"(the assistant's own reading, not the client's) made to {PATH}, x/y.md after the delivery they judged (task {TASK}). "
        "Keep those changes unless this request says otherwise."
    )
    assert "as the client judged it" not in text


def test_without_a_judged_base_or_a_base_the_body_is_as_before() -> None:
    plain = body(contract(), {"topic": "ai"}, [], "N")
    assert based("delivered", None, note="N") == plain and based("latest", None, note="N") == plain
    assert BODIES.body(contract(), number_criteria([(1, "root", ["Short"])]), {"topic": "ai"}, [], "N", base=None) == plain


def test_long_criteria_and_note_stay_inside_the_rendered_prompt_and_the_cut_points_to_the_task_file() -> None:
    criteria = [f"Criterion {k}: " + "c" * 90 for k in range(36)]  # about 4 000 characters
    note = "Corrections: " + "n" * 2600
    c = contract(acceptance=criteria)
    text = based("delivered", judged(texts=((PATH, "j" * 5990),)), note=note, c=c)
    first_base = text.index("## Base: ")
    assert 6500 < first_base < 7300 and len(text) > RENDER_BODY_CHARS
    shown = Message(sender="root", to="lead", type="task", body=text, id="20261022T100000000001-root-1234").render()
    assert all(f"- C{k + 1}: {criterion}" in shown for k, criterion in enumerate(criteria))
    assert note in shown and 'see "## Base" at the end of this task.' in shown
    assert "## Base: the version the client judged" in shown and "[... message cut: " in shown
    assert 'Read the rest with read(path="lead/<box>/20261022T100000000001-root-1234.md")' in shown
