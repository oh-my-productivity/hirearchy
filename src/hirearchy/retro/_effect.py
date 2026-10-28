"""Did past changes hold (design 4.4; pure): the outcome of a change is read from the cases where it was exercised and the rejections that came after it.

The outcome is one of, in this order: ``recurred in case {case} ({R})`` (the first later related rejection; for a playbook item in warning, retired or restored, Phase 1's
state with its R ids); ``not recurred in {n} cases where it was exercised`` once ``n`` reaches the window; ``INCONCLUSIVE ({n} of {window} exercised cases)`` below it; or
``no target recorded: not evaluated`` for a change that is the effect of no item and has no criterion of its own. Only the user's own (human-tier) verdicts count: a relayed or
an agent verdict weighs 0."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from ._views import Occasion, Tracked

_NEVER = datetime.min.replace(tzinfo=timezone.utc)  # sorts an undated change after the dated ones, which the first key of the sort already does
HUMAN = "human"
NOT_EVALUATED = "no target recorded: not evaluated"
RECURRED_STATES = ("warning", "retired", "restored")  # the watch states of Phase 1 that say a playbook item's change recurred


@dataclass(frozen=True)
class Evaluated:
    """A change with its outcome. ``final`` is false while the outcome is INCONCLUSIVE; ``changed`` is when the outcome last changed (the first recurrence, or the case
    that reached the window), None when it has not or cannot."""

    text: str
    kind: str
    when: datetime | None
    outcome: str
    final: bool
    changed: datetime | None = None


def _human(occasions: Sequence[Occasion]) -> list[Occasion]:
    return [o for o in occasions if o.tier == HUMAN]


def _ordered(occasions: Sequence[Occasion]) -> list[Occasion]:
    return sorted(occasions, key=lambda o: (o.when is None, o.when or _NEVER, o.case))


def evaluate(change: Tracked, window: int) -> Evaluated:
    """The outcome of ``change`` with the ``window`` of exercised cases that settles it (a playbook item uses its own ``k``)."""
    done = (change.text, change.kind, change.when)
    if not change.has_target and change.watch is None:
        return Evaluated(*done, NOT_EVALUATED, True)
    if (watch := change.watch) is not None:
        if watch.state in RECURRED_STATES:
            return Evaluated(*done, f"recurred: {watch.state} ({', '.join(watch.related)})" if watch.related else f"recurred: {watch.state}", True)
        return _counted(done, watch.clean, watch.k, None)
    if again := _ordered(_human(change.recurred)):
        first = again[0]
        return Evaluated(*done, f"recurred in case {first.case}" + (f" ({first.ref})" if first.ref else ""), True, first.when)
    exercised = _ordered(_human(change.exercised))
    reached = exercised[window - 1].when if len(exercised) >= window else None
    return _counted(done, len(exercised), window, reached)


def _counted(done: tuple[str, str, datetime | None], n: int, window: int, reached: datetime | None) -> Evaluated:
    if n >= window:
        return Evaluated(*done, f"not recurred in {n} cases where it was exercised", True, reached)
    return Evaluated(*done, f"INCONCLUSIVE ({n} of {window} exercised cases)", False)


def listed(changes: Sequence[Evaluated], since: datetime | None, carry_since: datetime | None) -> list[Evaluated]:
    """The changes D7 lists, oldest first: those made after ``since``, those whose outcome changed after it (they reached their window or recurred), and those still
    INCONCLUSIVE and made after ``carry_since`` (the ``since`` of the brief ``carry`` briefs back; None: since the organization started)."""
    def after(when: datetime | None, bound: datetime | None) -> bool:
        return when is not None and (bound is None or when > bound)

    kept = [
        c for c in changes
        if since is None or after(c.when, since) or after(c.changed, since) or (not c.final and (carry_since is None or after(c.when, carry_since)))
    ]
    return sorted(kept, key=lambda c: (c.when is None, c.when or _NEVER, c.text))
