"""``CreditingThrottles``: the credit of a run that ended on a model-service throttle before any tool effect (phase 0a.2, design 9.2, DR-44)."""

from __future__ import annotations

from hirearchy.delivery import MessageDelivery
from hirearchy.kernel import OrgError, credited_stems, is_run_credit, run_credit_title
from hirearchy.kernel import Message
from hirearchy.scheduler._throttle import CreditingThrottles
from hirearchy.scheduler.testing import LifecycleWorld, lifecycle_world

from ._support import a_run

STEM = "20260101T000000000000"  # the log of ``a_run``
MARK = "# kiro: throttled by the model service (retryErrorType THROTTLING); tool effects: none"
THROTTLE_ERROR = '[run error] prompt: high traffic (code -32000): {"errorType":"ModelThrottleError","retryErrorType":"THROTTLING"}'
THROTTLED = f"# kiro: run started (engine v3)\n[tool ok] Read File /x\n{THROTTLE_ERROR}\n{MARK}\n\n# exit 75 after 3s\n"


class RaisingDelivery(MessageDelivery):
    def deliver(self, msg: Message) -> Message:
        raise OrgError("the mailbox is full")

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        raise OrgError("the mailbox is full")


def world(transcript: str = THROTTLED) -> tuple[LifecycleWorld, CreditingThrottles]:
    w = lifecycle_world()
    w.hire("ceo")
    w.runs_store.put_log("ceo", f"{STEM}.log", transcript)
    return w, CreditingThrottles(w.runs_store, w.box, w.delivery, w.console)


def credits(w: LifecycleWorld) -> list[Message]:
    return [m for m in w.delivery.messages if is_run_credit(m)]


def test_a_throttled_first_run_is_a_free_credit() -> None:
    w, throttles = world()
    assert throttles.credit(a_run(w.table, w.clock, "ceo")) == "free"
    (note,) = credits(w)
    assert (note.to, note.budget, note.wake, note.title) == ("ceo", 1, False, run_credit_title("ceo", STEM)) and w.console.lines == []


def test_a_throttle_after_a_credited_previous_run_is_counted() -> None:
    w, throttles = world()
    w.runs_store.put_log("ceo", "20251231T000000000000.log", THROTTLED)
    w.box.store(Message(sender="runtime", to="ceo", type="note", budget=1, wake=False, title=run_credit_title("ceo", "20251231T000000000000"), body="b",
                        id="20251231T000001000000-runtime-aaaa"))
    assert credited_stems(w.box.received("ceo")) == {"20251231T000000000000"}
    assert throttles.credit(a_run(w.table, w.clock, "ceo")) == "counted" and len(credits(w)) == 1
    w.runs_store.put_log("ceo", "20251231T120000000000.log", "# exit 0 after 3s\n")  # a run between them that was not credited: the next one is free again
    assert throttles.credit(a_run(w.table, w.clock, "ceo")) == "free"


def test_a_message_sent_during_the_run_means_no_credit() -> None:
    w, throttles = world()
    w.box.store(Message(sender="ceo", to="root", type="note", title="hello", body="b", id=f"{STEM[:20]}1-ceo-aaaa"))
    assert throttles.credit(a_run(w.table, w.clock, "ceo")) == "" and credits(w) == [] and w.console.lines == []
    quiet, again = world()
    quiet.box.store(Message(sender="ceo", to="root", type="note", title="before", body="b", id="20251231T235959999999-ceo-aaaa"))  # sent before the run began
    assert again.credit(a_run(quiet.table, quiet.clock, "ceo")) == "free"


def test_no_mark_means_no_credit() -> None:
    for transcript in (THROTTLED.replace(MARK + "\n", ""), THROTTLED.replace("none", "2"), THROTTLED.replace(THROTTLE_ERROR + "\n", ""), "# exit 75 after 3s\n"):
        w, throttles = world(transcript)
        assert throttles.credit(a_run(w.table, w.clock, "ceo")) == "" and credits(w) == []


def test_an_unreadable_log_gives_no_credit_and_a_console_line() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    throttles = CreditingThrottles(w.runs_store, w.box, w.delivery, w.console)  # the log of the run was never written
    assert throttles.credit(a_run(w.table, w.clock, "ceo")) == "" and credits(w) == []
    assert len(w.console.lines) == 1 and w.console.lines[0].startswith("ceo: throttle credit not given: ")


def test_a_delivery_that_raises_gives_no_credit_and_no_note() -> None:
    w, _ = world()
    throttles = CreditingThrottles(w.runs_store, w.box, RaisingDelivery(), w.console)
    assert throttles.credit(a_run(w.table, w.clock, "ceo")) == ""
    assert w.console.lines == ["ceo: throttle credit not given: the mailbox is full"] and credited_stems(w.box.received("ceo")) == set() and credits(w) == []


def test_a_log_missing_from_the_listing_is_free() -> None:
    w, _ = world()
    run = a_run(w.table, w.clock, "ceo")
    hidden = run.log.with_name(f".{STEM}.log")  # readable, but the listing of the visible logs does not show it
    w.runs_store.put_log("ceo", hidden.name, THROTTLED)
    run.log = hidden
    assert [f.path for f in w.runs_store.files("ceo")] == [w.runs_store.files("ceo")[0].path] and hidden not in [f.path for f in w.runs_store.files("ceo")]
    assert CreditingThrottles(w.runs_store, w.box, w.delivery, w.console).credit(run) == "free"
