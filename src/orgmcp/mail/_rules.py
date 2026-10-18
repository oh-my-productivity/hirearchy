"""Rules every implementation of the mailboxes shares: what a message id may look like, which names are messages."""

from __future__ import annotations

import re

RECEIVED_BOXES = ("inbox", "inflight", "read")  # the boxes a message is in once it has been delivered to its recipient
PLAIN_ID = re.compile(r"[\w.\-]+")  # an id that is a file name and nothing else: no separator, no blank


def is_plain_id(msg_id: object) -> bool:
    """``msg_id`` is a non-empty id made of word characters, dots and dashes (so ``<box>/<id>.md`` stays inside the box)."""
    return bool(msg_id) and PLAIN_ID.fullmatch(str(msg_id)) is not None


def is_message_name(name: str) -> bool:
    """A file name that is a message: ``*.md`` and not hidden (temporary files of an atomic write start with a dot)."""
    return name.endswith(".md") and not name.startswith(".")
