"""``CreditingEffortStops``: the credit of a run the launcher stopped because kiro-cli did not set its effort (batch 1.1, design 2.4)."""

from __future__ import annotations

from hirearchy.budget import effort_credit
from hirearchy.kernel import Message, credited_stems, is_run_credit, run_credit_title
from hirearchy.kiro import EffortStop
from hirearchy.scheduler._effort import CreditingEffortStops, effort_text
from hirearchy.scheduler._run import RunTable
from hirearchy.scheduler.testing import LifecycleWorld, lifecycle_world

from ._support import a_run
from .test_throttle import STEM, THROTTLED, RaisingDelivery

QUOTED = "failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels"
WARNING = f"[warn] {QUOTED}"
MARK = f"# kiro: effort not set, run stopped (kiro-cli: {QUOTED}); tool effects: none"
STOPPED = f"# kiro: run started (engine v3)\n{WARNING}\n{MARK}\n\n# exit -9 after 11s\n"


def world(transcript: str = STOPPED) -> tuple[LifecycleWorld, CreditingEffortStops]:
    w = lifecycle_world()
    w.hire("ceo")
    w.runs_store.put_log("ceo", f"{STEM}.log", transcript)
    return w, CreditingEffortStops(w.runs_store, w.box, w.delivery, w.console)


def credits(w: LifecycleWorld) -> list[Message]:
    return [m for m in w.delivery.messages if is_run_credit(m)]


def test_stop_of_reads_the_launchers_stop_at_the_end_of_the_log() -> None:
    w, efforts = world()
    assert efforts.stop_of(a_run(w.table, w.clock, "ceo")) == EffortStop(QUOTED, 0)
    w, efforts = world(STOPPED.replace("tool effects: none", "tool effects: 2"))
    assert efforts.stop_of(a_run(w.table, w.clock, "ceo")) == EffortStop(QUOTED, 2)


def test_stop_of_is_none_without_the_launchers_mark() -> None:
    gave_up = "# kiro: gave up after 1s: kiro-cli did not start the run (no \"runStarted\" event)\n\n# exit -9 after 1s\n"
    for transcript in (THROTTLED, gave_up, "# exit -9 after 3s\n"):
        w, efforts = world(transcript)
        assert efforts.stop_of(a_run(w.table, w.clock, "ceo")) is None and w.console.lines == []


def test_a_warning_out_of_the_tail_is_no_stop() -> None:
    w, efforts = world(f"{WARNING}\n" + "x" * 60 + "\n" * 1 + ("x" * 60 + "\n") * 99 + f"{MARK}\n\n# exit -9 after 11s\n")
    assert efforts.stop_of(a_run(w.table, w.clock, "ceo")) is None


def test_an_unreadable_log_is_no_stop_and_says_so() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    efforts = CreditingEffortStops(w.runs_store, w.box, w.delivery, w.console)  # the log of the run was never written
    assert efforts.stop_of(a_run(w.table, w.clock, "ceo")) is None
    assert len(w.console.lines) == 1 and w.console.lines[0].startswith("ceo: run log not read for the effort check: ")


def test_a_first_stop_is_a_free_credit_with_note_c() -> None:
    w, efforts = world()
    assert efforts.credit(a_run(w.table, w.clock, "ceo"), EffortStop(QUOTED, 0)) == "free"
    (note,) = credits(w)
    assert (note.to, note.budget, note.wake, note.title) == ("ceo", 1, False, run_credit_title("ceo", STEM))
    assert note.body == effort_credit("ceo", STEM).body and w.console.lines == []


def test_a_stop_after_a_credited_run_is_counted() -> None:
    w, efforts = world()
    w.runs_store.put_log("ceo", "20251231T000000000000.log", STOPPED)
    w.box.store(Message(sender="runtime", to="ceo", type="note", budget=1, wake=False, title=run_credit_title("ceo", "20251231T000000000000"), body="b",
                        id="20251231T000001000000-runtime-aaaa"))
    assert credited_stems(w.box.received("ceo")) == {"20251231T000000000000"}
    stop = EffortStop(QUOTED, 0)
    assert efforts.credit(a_run(w.table, w.clock, "ceo"), stop) == "counted" and len(credits(w)) == 1
    w.runs_store.put_log("ceo", "20251231T120000000000.log", "# exit 0 after 3s\n")  # a run between them that was not credited: the next one is free again
    assert efforts.credit(a_run(w.table, w.clock, "ceo"), stop) == "free"


def test_a_stop_with_tool_effects_gets_no_credit() -> None:
    w, efforts = world()
    assert efforts.credit(a_run(w.table, w.clock, "ceo"), EffortStop(QUOTED, 2)) == "" and credits(w) == [] and w.console.lines == []


def test_a_message_sent_during_the_run_means_no_credit() -> None:
    w, efforts = world()
    w.box.store(Message(sender="ceo", to="root", type="note", title="hello", body="b", id=f"{STEM[:20]}1-ceo-aaaa"))
    assert efforts.credit(a_run(w.table, w.clock, "ceo"), EffortStop(QUOTED, 0)) == "" and credits(w) == [] and w.console.lines == []
    quiet, again = world()
    quiet.box.store(Message(sender="ceo", to="root", type="note", title="before", body="b", id="20251231T235959999999-ceo-aaaa"))  # sent before the run began
    assert again.credit(a_run(quiet.table, quiet.clock, "ceo"), EffortStop(QUOTED, 0)) == "free"


def test_a_delivery_that_raises_gives_no_credit_and_says_so() -> None:
    w, _ = world()
    efforts = CreditingEffortStops(w.runs_store, w.box, RaisingDelivery(), w.console)
    assert efforts.credit(a_run(w.table, w.clock, "ceo"), EffortStop(QUOTED, 0)) == ""
    assert w.console.lines == ["ceo: effort credit not given: the mailbox is full"] and credited_stems(w.box.received("ceo")) == set() and credits(w) == []


def test_effort_text_puts_the_outcome_before_kiros_quote() -> None:
    stop = EffortStop(QUOTED, 0)
    assert effort_text(stop, "free") == f"effort not set: run stopped, not charged, relaunched (kiro-cli: {QUOTED}; tool effects: none)"
    assert effort_text(stop, "counted") == f"effort not set: run stopped, not charged, counted as a failure (kiro-cli: {QUOTED}; tool effects: none)"
    assert effort_text(stop, "") == f"effort not set: run stopped, charged as a failed run (kiro-cli: {QUOTED}; tool effects: none)"
    assert effort_text(EffortStop(QUOTED, 2), "") == f"effort not set: run stopped, charged as a failed run (kiro-cli: {QUOTED}; tool effects: 2)"


def test_the_assembled_lifecycle_credits_an_effort_stop() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    w.mail_to("ceo")
    w.table.will_exit(-9, output=f"{WARNING}\n{MARK}\n")
    runs: RunTable = {}
    assert w.lifecycle.starter.launch(runs, set(), None) == 1
    stem = runs["ceo"].log.stem
    w.lifecycle.reaper.reap(runs)
    (end,) = w.events_of("run.end")
    assert end["error"] == f"effort not set: run stopped, not charged, relaunched (kiro-cli: {QUOTED}; tool effects: none)"
    (note,) = credits(w)
    assert note.to == "ceo" and note.body == effort_credit("ceo", stem).body
    assert w.console.lines[-1] == "ceo: run stopped because kiro-cli did not set its effort: not charged, relaunched"
    assert w.events_of("agent.failure") == [] and w.box.messages("ceo", "inbox") != []
