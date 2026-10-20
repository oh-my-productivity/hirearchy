"""Whether the message in a file wakes its recipient (moved from ``FsMailbox._wakes``, which the static ``Org._wakes`` of the facade also serves)."""

from __future__ import annotations

from pathlib import Path

from .api import MessageParser


def wakes(parser: MessageParser, path: Path) -> bool:
    """``wake`` of the message in ``path``; a file that cannot be read still counts as mail: a run should look at it."""
    try:
        return parser.parse(path).wake
    except Exception:  # noqa: BLE001 - an unreadable file still counts as mail: a run should look at it
        return True
