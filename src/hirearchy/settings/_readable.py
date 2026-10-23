"""``readable_config``: the settings of ORG.md, or an ``OrgError`` that names ORG.md when its settings block cannot be read."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..kernel import JsonObject, OrgError

if TYPE_CHECKING:
    from .api import OrgSettings

UNREADABLE = (
    "ORG.md cannot be read: the YAML of its settings block (between the --- lines) does not parse. "
    "Ask the user to repair it first (root can with write path=ORG.md)."
)


def readable_config(settings: OrgSettings) -> JsonObject:
    """``settings.config()``; when ORG.md cannot be read or parsed (a hand edit slipped) the ``OrgError`` ``UNREADABLE``, not the parser's own text."""
    try:
        return settings.config()
    except Exception as exc:  # noqa: BLE001 - any failure to read or parse the document: the caller needs it, so it is refused in plain words
        raise OrgError(UNREADABLE) from exc
