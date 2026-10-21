"""What an agent can hand down, and how that is said (pure; the derived query and the fixed fake both use it)."""

from __future__ import annotations


def most_delegable(budget: int, outstanding: int) -> int:
    """The most an agent with ``budget`` runs and ``outstanding`` delegations can hand down with one more delegation: one run is kept per
    outstanding delegation to process its result, one for the new delegation's own result; never below 0."""
    return max(0, budget - outstanding - 1)


def grant_hint_text(addr: str, budget: int, outstanding: int) -> str:
    """What ``addr`` can do with its budget now, in words (shown to whoever just granted it runs)."""
    most = most_delegable(budget, outstanding)
    head = f"`{addr}` now has {budget} run(s) and {outstanding} outstanding delegation(s)"
    if most > 0:
        return f"{head}; with one more delegation it can hand down at most {most} run(s)."
    need = outstanding + 2  # budget - out - 1 >= 1
    return (
        f"{head}: with {budget} run(s) and {outstanding} outstanding delegation(s) it cannot delegate anything; it can "
        f"only process results or work itself - grant at least {max(0, need - budget)} more (a budget of {need}) "
        "to allow one delegation of 1 run."
    )
