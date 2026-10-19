"""The longest playbook an organization accepts (``playbook_max_words`` of ORG.md)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import SupportsInt, cast

DEFAULT_PLAYBOOK_WORDS = 1000


def playbook_word_cap(config: Mapping[str, object]) -> int:
    """``playbook_max_words`` of the settings; a malformed value, or one that is not positive, means 1000."""
    try:
        cap = int(cast("SupportsInt | str", config["playbook_max_words"]))
    except (TypeError, ValueError):
        return DEFAULT_PLAYBOOK_WORDS
    return cap if cap > 0 else DEFAULT_PLAYBOOK_WORDS
