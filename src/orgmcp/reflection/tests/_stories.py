"""The stories the tests tell in a world: who asked for what, what was delivered, what the client said. Each returns the messages it made."""

from __future__ import annotations

from dataclasses import dataclass, field

from orgmcp.kernel import Message
from orgmcp.reflection.testing import ReflectionWorld

from collections.abc import Callable

from ._support import STEPS, ask, define, deliver, rate, read_inbox, revise, rework

LONG = "x" * 100


@dataclass
class Story:
    """The requests of a story in the order they were made, and the results and notes the client and the owner exchanged."""

    asks: list[Message] = field(default_factory=list)
    results: list[Message] = field(default_factory=list)
    notes: list[Message] = field(default_factory=list)


def delivered_and_accepted(w: ReflectionWorld) -> Story:
    """One request, delivered in two runs with two lines of lessons, accepted with a word."""
    define(w)
    first = ask(w, "ai")
    result = deliver(w, first, runs=2, lessons="Search first.\nTwo runs.")
    note = rate(w, first, "accept", "good")
    return Story([first], [result], [note])


def rejected_then_accepted(w: ReflectionWorld) -> Story:
    """A request delivered and rejected, sent back, delivered again and accepted."""
    define(w)
    first = ask(w, "ai")
    one = deliver(w, first, runs=2, lessons="Clean run; no issues.")
    no = rate(w, first, "reject", "Sam's 'before Friday' needs a date.")
    w.s.d.clock.advance(1)
    again = rework(w, first, budget=6)
    two = deliver(w, again, runs=3, lessons="Applied the date rule.")
    w.s.d.clock.advance(1)
    yes = rate(w, again, "accept", "this version is right")
    return Story([first, again], [one, two], [no, yes])


def three_playbook_versions(w: ReflectionWorld) -> Story:
    """A case delivered before any playbook, one under v1 and one under v2 (a fourth is open)."""
    define(w)
    story = Story()
    for topic, text in (("ai", None), ("chips", "v1"), ("bio", "v2")):
        if text:
            revise(w, STEPS + (f"\n4. {text}" if text == "v2" else ""), reason=f"playbook {text}")
        task = ask(w, topic)
        story.asks.append(task)
        story.results.append(deliver(w, task, runs=1, lessons=f"Lesson about {topic}."))
        w.s.d.clock.advance(1)
    story.asks.append(ask(w, "open"))
    return story


def eight_long_cases(w: ReflectionWorld) -> Story:
    """Eight delivered requests with lessons so long that the digest has to drop cases to stay within its limit."""
    define(w)
    story = Story()
    for i in range(8):
        task = ask(w, f"topic {i}")
        story.asks.append(task)
        story.results.append(deliver(w, task, runs=1, lessons=f"Case {i}: " + LONG * 3))
        w.s.d.clock.advance(1)
    return story


# ------------------------------------------------------------------------------ what the owner is shown before a run


def owner_without_requests(w: ReflectionWorld) -> Story:
    define(w)
    return Story()


def new_request_without_history(w: ReflectionWorld) -> Story:
    define(w)
    return Story([ask(w)])


def history_then_new_request(w: ReflectionWorld) -> Story:
    """A rejected-then-accepted case, and a new request in the batch; there is no playbook."""
    story = rejected_then_accepted(w)
    story.asks.append(ask(w, "chips"))
    return story


def locked_history_then_new_request(w: ReflectionWorld) -> Story:
    """The contract is locked: the owner cannot write a playbook."""
    define(w, locked=True)
    first = ask(w)
    result = deliver(w, first, runs=1, lessons="L.")
    return Story([first, ask(w, "chips")], [result])


def playbook_and_rejection(w: ReflectionWorld) -> Story:
    """Playbook v1 exists; the batch holds the client's rejection of a delivery made under it."""
    define(w)
    revise(w, STEPS, "start")
    first = ask(w)
    result = deliver(w, first, runs=1, lessons="L.")
    w.s.d.clock.advance(1)
    return Story([first], [result], [rate(w, first, "reject", "Too long.")])


def locked_and_rejection(w: ReflectionWorld) -> Story:
    define(w, locked=True)
    first = ask(w)
    result = deliver(w, first, runs=1, lessons="L.")
    w.s.d.clock.advance(1)
    return Story([first], [result], [rate(w, first, "reject", "Too long.")])


def second_playbook_and_new_request(w: ReflectionWorld) -> Story:
    """Playbook v2 exists, a case was delivered under it, and a new request arrives."""
    story = Story()
    define(w)
    for topic, text, reason in (("ai", None, ""), ("chips", STEPS, "one"), ("bio", STEPS + "\n4. More.", "two")):
        if text:
            revise(w, text, reason)
        task = ask(w, topic)
        story.asks.append(task)
        story.results.append(deliver(w, task, runs=1, lessons=f"Lesson about {topic}."))
    story.asks.append(ask(w, "last"))
    return story


def rejection_and_rework(w: ReflectionWorld) -> Story:
    """The owner has read everything; the batch holds only the client's rejection of the latest delivery and the rework that came with it."""
    define(w)
    first = ask(w)
    deliver(w, first, runs=1, lessons="L1.")
    revise(w, STEPS, "one")
    second = ask(w, "chips")
    result = deliver(w, second, runs=2, lessons="L2.")
    read_inbox(w)
    w.s.d.clock.advance(1)
    note = rate(w, second, "reject", "Add dates.")
    return Story([first, second, rework(w, second, budget=3)], [result], [note])


SECTIONS: dict[str, Callable[[ReflectionWorld], Story]] = {
    "owner_without_requests": owner_without_requests,
    "new_request_without_history": new_request_without_history,
    "history_then_new_request": history_then_new_request,
    "locked_history_then_new_request": locked_history_then_new_request,
    "playbook_and_rejection": playbook_and_rejection,
    "locked_and_rejection": locked_and_rejection,
    "second_playbook_and_new_request": second_playbook_and_new_request,
    "rejection_and_rework": rejection_and_rework,
}
LISTINGS: dict[str, Callable[[ReflectionWorld], Story]] = {
    "delivered_and_accepted": delivered_and_accepted,
    "rejected_then_accepted": rejected_then_accepted,
    "three_playbook_versions": three_playbook_versions,
    "eight_long_cases": eight_long_cases,
}
