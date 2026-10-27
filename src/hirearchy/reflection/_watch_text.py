"""The words of one item's watch in root's views (design 14.3, 14.4): the ``services`` listing and the ``quality`` view.

Pure. An entry carries ids, states, counts and rejection ids only, never an item's words: what an agent wrote stays out of root's text views. Both views
build their lines from ``watch_entry``, so they say one thing about one item (design 20, "one derivation path")."""

from __future__ import annotations

from ..services import ItemWatch

CLEAN = "{clean} of {k} clean cases, k {k}"
WAITING = "waiting for the client's verdict on {n} {cases}"
PENDING = "waiting for the user's answer to {rejections}"
CARRIED = "carried from {old}"
NEXT_RETIRES = "the next related rejection retires it"
RETIRE_DUE = "retire due"
RESTORED = "the text of v{k}"


def watch_entry(w: ItemWatch) -> str:
    """``P9 new (1 of 3 clean cases, k 3; waiting for the client's verdict on 1 case)``, ``P12 warning (R4; the next related rejection retires it)``,
    ``P2 restored (the text of v1)``, ``P12 retired (R4, R6)`` or ``P3 kept``: one item of the watch."""
    related = ", ".join(w.related)
    if w.state == "new":
        parts = [CLEAN.format(clean=w.clean, k=w.k)]
        if w.waiting:
            parts.append(WAITING.format(n=w.waiting, cases="case" if w.waiting == 1 else "cases"))
        if w.pending:
            parts.append(PENDING.format(rejections=", ".join(w.pending)))
    elif w.state == "warning":
        parts = [related, RETIRE_DUE if w.retire_due else NEXT_RETIRES] if related else [RETIRE_DUE if w.retire_due else NEXT_RETIRES]
    elif w.state == "restored":
        parts = [RESTORED.format(k=w.restores)]
    elif w.state == "retired":
        parts = [related] if related else []
    else:
        parts = []
    if w.carried and w.state in ("new", "warning"):
        parts.append(CARRIED.format(old=w.carried))
    return f"{w.id} {w.state}" + (f" ({'; '.join(parts)})" if parts else "")


def in_its_watch(w: ItemWatch) -> bool:
    """Whether the item is in its watch now: ``new`` or ``warning`` (``kept`` has left it, ``restored`` and ``retired`` are facts of the file)."""
    return w.state in ("new", "warning")
