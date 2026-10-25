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
    the one question is the yes, and it is recorded with `confirms` or `answers`. The 0a.1 needle "never pass `criterion` on the rejection
    itself" is replaced on purpose (design 8.2, B9): since 0a.1 a criterion on the rejection is relayed, and since 0a.2 an amendment in the
    reject turn is refused, so naming the reading on the rejection only gives the reply its id (your reading, not their yes)."""
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    for needle in ('"always ..." is not their yes: ask the item first', "with `criterion` on the rejection itself (your reading, not their yes)"):
        assert needle in text, needle
    assert "never pass `criterion` on the rejection itself" not in text


def test_the_skill_records_the_answer_with_define_service_and_names_the_base():
    """K4 (design 8.2, DR-46): the yes is recorded with define_service(answers=, about=, words=), a change the user asks for on their own with
    words= alone, and the reading goes on the rejection in MCP feedback (at the terminal --criterion on a reject records the answer)."""
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    for needle in (
        "`answers=<the rejection's message id>`",
        "`words=<their answer, verbatim>`",
        "`words=` alone",
        "with `criterion` on the rejection itself (your reading, not their yes)",
        "the reply then gives the exact question",
        "at the terminal, `--criterion` on a reject records the answer",
        "withholds the path",  # K2 (design 8.2, C2): progress withholds the artifact path while the client's questions are open
        "did not deliver as checked",  # K3 (design 8.2, C5): progress, status and whoami name the files there the team did not deliver as checked
        'base="delivered"',  # K1 (design 8.2, D3): a human rework after a relayed one names the version the user judged
        'base="latest"',
        "request(service, inputs, revises=<task id>)",
        "`define_service(owner, name, add_acceptance=[<the new criterion>])`",
        "the resulting criteria",
        "never edit service.md or playbook.md yourself",
    ):
        assert needle in text, needle


def test_the_skill_asks_before_the_copy_and_never_answers_a_question_with_a_rework():
    """E3: root copied a deliverable whose questions for the client were still open, and once answered one with a rework. Item 3 asks first,
    `progress` flags the questions, and nothing is copied until they are answered."""
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    for needle in (
        "`progress` flags them",
        "copy nothing until they are answered",
        "never answer one with a rework",
        "tell the user it was your decision and what it cost",
        "4. then copy the deliverable",
    ):
        assert needle in text, needle


def test_the_skill_passes_the_notes_on_with_the_delivery_and_asks_only_the_others_first():
    """D-E6-1 (A2): `progress` lists the items that name no criterion as notes and withholds nothing for them, so item 3 asks the others in plain words
    before the copy and only passes the notes on with the delivery. The file stays at 125 lines."""
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    for needle in (
        "the ones it lists as notes, with no criterion, you only pass on with the delivery): ask the others in plain words",
        "`progress` flags them and withholds the path; the ones it lists as notes",
        "with any question from item 2, in one message before you deliver",
        "copy nothing until they are answered",
        "never answer one with a rework",
    ):
        assert needle in text, needle
    assert "withholds the path): ask them in plain words" not in text


def test_the_delivery_report_shows_the_assistants_relayed_runs_apart_as_its_own():
    """DR-0a3-8 (D-E5-1): the case total of a delivery report names root's relayed runs apart, as the assistant's own, and keeps the approved-runs example."""
    text = flat()
    assert "your relayed runs apart, as yours" in text
    assert '"19 runs of the 15 approved per request"' in text  # the needle of test_round_g_assistant stays


def test_the_skill_records_the_users_keep_as_is_as_their_accept_on_its_task():
    """L-ASIS (D-E5-5): when the user keeps the version they have as it is, even after a reject, root records that as their accept with their words;
    "deliver as is" and "I'll read it myself" stay no accept. F-E6-6 (D-E6-5) narrows it deliberately: only a delivered version the user kept after
    seeing it; a "keep it" about one part of it, or one given before they saw it, is no accept. The file stays at 125 lines."""
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    for needle in (
        'when they keep a delivered version as it is after seeing it ("i\'ll take it as it is"), record that accept on its task',
        'a "keep it" about one part of it, or before they saw it, is no accept',
        "with their words, also after a reject",
        '"deliver as is" or "i\'ll read it myself" is not an accept: ask, or record nothing yet',
    ):
        assert needle in text, needle


def test_the_skill_asks_the_spend_of_a_rework_in_the_message_of_the_question_that_needs_it():
    """D-E6-5 (7.3): E6's s2 lost two turns asking a rework's spend a turn after the question or the yes/no item that needs the rework. Line 72 asks it
    in the same message, with the number, and keeps the needles of the budget rules. The file stays at 125 lines."""
    assert len(SKILL.read_text().splitlines()) <= 125
    text = flat()
    for needle in (
        "in the same message as the question or yes/no item that needs the rework",
        "per-request budget, ask the user, with the number",
        "a rework needs about 2 runs per delegation it requires + 1",
        "ask the user once, with that number",
        "ask at the first budget request",
        "never wait until the reserve",
    ):
        assert needle in text, needle
