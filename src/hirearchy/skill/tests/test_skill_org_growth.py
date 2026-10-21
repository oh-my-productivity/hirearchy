# mypy: ignore-errors
# Org growth phase 0a: what SKILL.md tells the assistant about provenance, the contract question, ambiguous items and consistency.

import testkit

SKILL = testkit.REPO / "skills" / "hirearchy" / "SKILL.md"


def flat() -> str:
    return " ".join(SKILL.read_text().lower().split())


def test_the_skill_handles_phase_0a_feedback_within_its_line_limit():
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    needles = (
        'pass source="human" only on a rework the user asked for',  # block F: one rule for every rework root sends
        "your own reading is relayed (the default)",
        "read the criteria as a set",  # block D: the consistency question
        '"questions for the client:"',  # block G: the verifier's ambiguous items
        "with any question from item 2, in one message before you deliver",
        "confirms=<the rejection's message id>",  # block H: the link
        "only your one item per reject asks one",
        "an owner's note with a question for the client is no new question",
        "as one yes/no question",
        "read it with `inbox`, go on, and never reply to it or mention it",
        "make the item the clarification that settles both",
    )
    for needle in needles:
        assert needle in text, needle


def test_an_owner_note_is_never_a_second_question():
    assert "an owner's note asking if a rejection is lasting" not in flat()


def test_the_example_item_is_one_yes_no_question():
    assert "a new criterion, c6 clarified as" not in flat()


def test_the_trigger_words_are_gone():
    assert '("always", "never", "from now on")' not in flat()


def test_always_is_not_the_users_yes():
    """E3 turn 5: the assistant took "always" in the rejection for the yes and passed `criterion` on the rejection itself. Only the answer to
    the one question is the yes, and it is recorded with `confirms`."""
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    for needle in ('"always ..." is not their yes: ask the item first', "never pass `criterion` on the rejection itself"):
        assert needle in text, needle
