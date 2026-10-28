"""The run credit: the note with which the runtime returns a run it does not charge (phase 0a.2, design 9.2)."""

from __future__ import annotations

from hirearchy.budget.api import effort_credit, run_credit
from hirearchy.kernel import RUNTIME, credited_stems, is_run_credit, run_credit_title


def test_run_credit_is_a_runtime_note_returning_one_run() -> None:
    note = run_credit("ceo/eng", "20261022T202454859379")
    assert (note.sender, note.to, note.type, note.budget, note.wake) == (RUNTIME, "ceo/eng", "note", 1, False)
    assert note.title == run_credit_title("ceo/eng", "20261022T202454859379")
    assert note.body == (
        "Your run ceo/eng@20261022T202454859379 ended on a model-service throttle (retryErrorType THROTTLING) before any tool effect, "
        "so it is not charged: this note returns its run. Your messages are back in your inbox; the run is started again."
    )
    assert is_run_credit(note) and credited_stems([note]) == {"20261022T202454859379"}


def test_effort_credit_is_a_runtime_note_returning_one_run() -> None:
    note = effort_credit("ceo/eng", "20261028T040906023860")
    assert (note.sender, note.to, note.type, note.budget, note.wake) == (RUNTIME, "ceo/eng", "note", 1, False)
    assert note.title == run_credit_title("ceo/eng", "20261028T040906023860")
    assert note.body == (
        "Your run ceo/eng@20261028T040906023860 was stopped before any tool effect because kiro-cli did not set the effort this "
        "organization asks for, so it is not charged: this note returns its run. Your messages are back in your inbox; the run is started again."
    )
    assert is_run_credit(note) and credited_stems([note]) == {"20261028T040906023860"}
