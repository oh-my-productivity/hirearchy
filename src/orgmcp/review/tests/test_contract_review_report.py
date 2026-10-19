"""Contract of ``ReviewReport``: what a review says of itself. ``Review`` is its only implementation (it is data with one derived view: pure)."""

from __future__ import annotations

from datetime import datetime, timezone

from orgmcp.review import Note, Review, ReviewReport

AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def review(*notes: Note, flagged: int = 0) -> Review:
    return Review(at=AT, runs=0, flagged=flagged, notes=list(notes))


def test_a_review_is_a_report() -> None:
    assert isinstance(review(), ReviewReport)


def test_a_review_without_notes_has_nothing_to_send() -> None:
    assert review(flagged=3).render() == "3 flagged agent(s); nothing to send"
    assert review(flagged=0).render(dry_run=True) == "0 flagged agent(s); nothing to send"


def test_the_notes_are_listed_with_their_recipient_and_title_and_indented() -> None:
    text = review(Note("ceo", "health review: 1 new problem(s)", "line one\n\n  line three"), Note("root", "t2", "b2"), flagged=2).render()
    assert text == (
        "2 flagged agent(s); sent 2 note(s)\n"
        "\n-> ceo: health review: 1 new problem(s)\n   line one\n\n     line three\n"
        "\n-> root: t2\n   b2"
    )


def test_a_dry_run_says_would_send() -> None:
    assert review(Note("root", "t", "b"), flagged=1).render(dry_run=True).splitlines()[0] == "1 flagged agent(s); would send 1 note(s)"


def test_the_lines_of_a_body_lose_their_trailing_spaces() -> None:
    assert review(Note("root", "t", "a  \n  \nb")).render().endswith("\n   a\n\n   b")
