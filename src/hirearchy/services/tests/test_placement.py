"""Where an added or restored item goes (design 4.1, "Placement").

``build`` takes ``(heading, numbered, ids)`` per section, the ids written ``P1 P2 R:P9`` (a leading ``R:`` makes the item a rule)."""

from __future__ import annotations

import pytest

from hirearchy.services import PlaybookItem, PlaybookSection
from hirearchy.services._items import PlacementError, default_numbered, parse_items, place_add, place_restore, render_items

def build(*spec: tuple[str, bool | None, str]) -> tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]:
    items: list[PlaybookItem] = []
    sections: list[PlaybookSection] = []
    for heading, numbered, ids in spec:
        names = ids.split()
        for name in names:
            rule = name.startswith("R:")
            items.append(PlaybookItem(name[2:] if rule else name, "rule" if rule else "step", heading, f"text of {name}", "always" if rule else ""))
        sections.append(PlaybookSection(heading, default_numbered(heading) if numbered is None else numbered, tuple(n.removeprefix("R:") for n in names)))
    return tuple(items), tuple(sections)


def step(n: int) -> PlaybookItem:
    return PlaybookItem(f"P{n}", "step", "", f"new step {n}")


def rule(n: int) -> PlaybookItem:
    return PlaybookItem(f"P{n}", "rule", "", f"new rule {n}", "always")


def where(result: tuple[tuple[PlaybookItem, ...], tuple[PlaybookSection, ...]]) -> list[tuple[str, tuple[str, ...]]]:
    """(heading, ids) of every section; the items are in body order and each carries its section's heading."""
    items, sections = result
    assert [i.id for i in items] == [i for s in sections for i in s.ids]
    assert all(i.section == s.heading for s in sections for i in items if i.id in s.ids)
    back = parse_items(render_items(items, sections), {"items_max": 99, "rules": [i.id for i in items if i.kind == "rule"]})
    assert (back.error, back.items, back.sections) == ("", items, sections)  # what is placed renders and parses back exactly
    return [(s.heading, s.ids) for s in sections]


def test_a_step_add_goes_after_the_last_item_of_the_first_steps_section() -> None:
    items, sections = build(("# T", None, ""), ("## Steps", True, "P1 P2"), ("## Budget plan", False, "P3"), ("## Steps", True, "P4"))
    got = place_add(items, sections, step(5))
    assert where(got) == [("# T", ()), ("## Steps", ("P1", "P2", "P5")), ("## Budget plan", ("P3",)), ("## Steps", ("P4",))]
    assert got[1][1].numbered is True and got[0][2].section == "## Steps"
    assert render_items(*got).splitlines()[4:6] == ["2. [P2] text of P2", "3. [P5] new step 5"]


def test_a_step_add_into_an_emptied_steps_section_goes_first_in_it() -> None:
    items, sections = build(("## Steps", None, ""), ("## Other", False, "P1"))
    got = place_add(items, sections, step(2))
    assert where(got) == [("## Steps", ("P2",)), ("## Other", ("P1",))] and got[1][0].numbered is True


def test_else_after_the_first_numbered_section_else_into_a_new_steps_section_first() -> None:
    items, sections = build(("", False, "P1"), ("## Plan", False, "P2"), ("## Do", True, "P3 P4"), ("## Later", True, "P5"))
    assert where(place_add(items, sections, step(6))) == [("", ("P1",)), ("## Plan", ("P2",)), ("## Do", ("P3", "P4", "P6")), ("## Later", ("P5",))]
    items, sections = build(("", False, "P1"), ("## Plan", False, "P2"))
    got = place_add(items, sections, step(3))  # nothing numbered: a new `## Steps` section, first (after the text before the first heading)
    assert where(got) == [("", ("P1",)), ("## Steps", ("P3",)), ("## Plan", ("P2",))] and got[1][1].numbered is True
    items, sections = build(("## Plan", False, "P1"))
    assert where(place_add(items, sections, step(2))) == [("## Steps", ("P2",)), ("## Plan", ("P1",))]
    assert where(place_add((), (), step(1))) == [("## Steps", ("P1",))]
    assert where(place_add(*build(("## Rules", False, "R:P1")), step(2)))[0] == ("## Steps", ("P2",))


def test_a_step_after_a_live_step_lands_in_its_section() -> None:
    items, sections = build(("## Steps", True, "P1 P2"), ("## Budget plan", False, "P3 P4"), ("## Rules", False, "R:P5"))
    assert where(place_add(items, sections, step(6), "P3")) == [
        ("## Steps", ("P1", "P2")), ("## Budget plan", ("P3", "P6", "P4")), ("## Rules", ("P5",)),
    ]
    assert where(place_add(items, sections, step(6), "p1"))[0] == ("## Steps", ("P1", "P6", "P2"))  # ids are compared upper-case


def test_a_step_after_a_rule_is_refused_with_its_pb_args_clause() -> None:
    items, sections = build(("## Steps", True, "P1"), ("## Rules", False, "R:P9"))
    with pytest.raises(PlacementError) as refused:
        place_add(items, sections, step(10), "P9")
    assert str(refused.value) == "after=P9 is a rule: a step goes after a step (or leave after out)"
    with pytest.raises(PlacementError) as unknown:
        place_add(items, sections, step(10), "P99")
    assert str(unknown.value) == "after=P99 is not a live item"


def test_a_rule_add_goes_to_the_end_of_the_rules_section_created_last() -> None:
    items, sections = build(("## Steps", True, "P1"), ("## Rules", False, "R:P2 R:P3"))
    got = place_add(items, sections, rule(4))
    assert where(got) == [("## Steps", ("P1",)), ("## Rules", ("P2", "P3", "P4"))] and got[0][3].kind == "rule" and got[0][3].section == "## Rules"
    # no rule live: the section is created as the last one, even next to a legacy section headed the same
    items, sections = build(("## Steps", True, "P1"), ("## Rules", False, "P2"))
    got = place_add(items, sections, rule(3))
    assert where(got) == [("## Steps", ("P1",)), ("## Rules", ("P2",)), ("## Rules", ("P3",))] and got[1][2].numbered is False
    assert where(place_add((), (), rule(1))) == [("## Rules", ("P1",))]


def test_a_rule_after_a_live_rule() -> None:
    items, sections = build(("## Steps", True, "P1"), ("## Rules", False, "R:P2 R:P3"))
    assert where(place_add(items, sections, rule(4), "P2"))[1] == ("## Rules", ("P2", "P4", "P3"))
    for after in ("P1", "P7"):
        with pytest.raises(PlacementError) as refused:
            place_add(items, sections, rule(4), after)
        assert str(refused.value) == f"after={after} is not a live rule"


def test_a_restored_item_goes_back_after_its_nearest_live_predecessor_else_first() -> None:
    earlier_items, earlier = build(("## Steps", True, "P1 P2 P3 P4"), ("## Other", False, "P5 P6"))
    items, sections = build(("## Steps", True, "P1 P4"), ("## Other", False, "P6"))
    restored = PlaybookItem("P3", "step", "## Steps", "back")
    assert where(place_restore(items, sections, restored, earlier)) == [("## Steps", ("P1", "P3", "P4")), ("## Other", ("P6",))]
    # P2 and P1 both live: the nearest preceding one is P2
    items, sections = build(("## Steps", True, "P1 P2 P4"), ("## Other", False, "P6"))
    assert where(place_restore(items, sections, restored, earlier))[0] == ("## Steps", ("P1", "P2", "P3", "P4"))
    # no predecessor live: first in the section
    items, sections = build(("## Steps", True, "P4"), ("## Other", False, "P6"))
    assert where(place_restore(items, sections, restored, earlier))[0] == ("## Steps", ("P3", "P4"))
    other = PlaybookItem("P5", "step", "## Other", "back")
    assert where(place_restore(items, sections, other, earlier))[1] == ("## Other", ("P5", "P6"))
    # the section is found again by its heading and its occurrence among headings with the same line
    two_earlier = build(("## A", False, "P1 P2"), ("## A", False, "P3 P4"))[1]
    items, sections = build(("## A", False, "P1"), ("## A", False, "P4"))
    got = place_restore(items, sections, PlaybookItem("P3", "step", "## A", "back"), two_earlier)
    assert where(got) == [("## A", ("P1",)), ("## A", ("P3", "P4"))]


def test_a_restored_rule_goes_after_the_nearest_preceding_rule_that_is_still_live() -> None:
    earlier = build(("## Steps", True, "P1"), ("## Rules", False, "R:P2 R:P3 R:P4"))[1]
    restored = PlaybookItem("P4", "rule", "## Rules", "back", "always")
    items, sections = build(("## Steps", True, "P1"), ("## Rules", False, "R:P2"))
    assert where(place_restore(items, sections, restored, earlier))[1] == ("## Rules", ("P2", "P4"))
    items, sections = build(("## Steps", True, "P1"), ("## Rules", False, "R:P5"))
    assert where(place_restore(items, sections, restored, earlier))[1] == ("## Rules", ("P4", "P5"))
    items, sections = build(("## Steps", True, "P1"))  # no rule live: the rules section is created last
    assert where(place_restore(items, sections, restored, earlier)) == [("## Steps", ("P1",)), ("## Rules", ("P4",))]


def test_a_restore_into_an_emptied_section_and_into_the_text_before_the_first_heading() -> None:
    earlier = build(("", False, "P1"), ("## Steps", True, "P2 P3"), ("## Other", False, "P4"))[1]
    items, sections = build(("## Steps", True, "P2 P3"), ("## Other", None, ""))
    # the text before the first heading: its section is recreated first, in the style it had
    got = place_restore(items, sections, PlaybookItem("P1", "step", "", "back"), earlier)
    assert where(got) == [("", ("P1",)), ("## Steps", ("P2", "P3")), ("## Other", ())] and got[1][0].numbered is False
    # an emptied section keeps its heading and takes the item as its first
    got = place_restore(items, sections, PlaybookItem("P4", "step", "## Other", "back"), earlier)
    assert where(got)[1] == ("## Other", ("P4",)) and got[1][1].numbered is False
    items, sections = build(("", False, "P1"), ("## Steps", None, ""), ("## Other", False, "P4"))
    assert where(place_restore(items, sections, PlaybookItem("P2", "step", "## Steps", "back"), earlier))[1] == ("## Steps", ("P2",))
    assert place_restore(items, sections, PlaybookItem("P2", "step", "## Steps", "back"), earlier)[1][1].numbered is True


def test_a_restore_whose_section_is_gone_is_placed_like_an_add() -> None:
    earlier = build(("## Gone", False, "P1"))[1]
    items, sections = build(("## Steps", True, "P2"))
    assert where(place_restore(items, sections, PlaybookItem("P1", "step", "## Gone", "back"), earlier)) == [("## Steps", ("P2", "P1"))]
    assert where(place_restore(items, sections, PlaybookItem("P7", "step", "## Steps", "back"), earlier)) == [("## Steps", ("P2", "P7"))]
