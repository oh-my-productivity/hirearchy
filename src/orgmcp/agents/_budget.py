"""The budget a message file carries."""

from __future__ import annotations

from ..kernel import split_frontmatter


def message_budget(text: str) -> int:
    """The runs of budget in the text of a message file; 0 for anything that is not a valid message.

    A valid message has a frontmatter with ``from``, ``to`` and ``type``, and a ``budget`` (if any) that ``int`` accepts.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        meta, _ = split_frontmatter(text)
    except Exception:  # noqa: BLE001 - yaml errors of any kind
        return 0
    if not meta or not all(meta.get(key) for key in ("from", "to", "type")):
        return 0
    try:
        budget: int = int(meta.get("budget") or 0)  # type: ignore[call-overload]
        return budget
    except (TypeError, ValueError):
        return 0
