"""The text of ORG.md with a new ``max_depth``: the one rewrite of a single setting, touching no other byte of the document."""

from __future__ import annotations

import re

from ..kernel import OrgError, split_frontmatter
from ._config import config_number, parse_config

_LINE = re.compile(r"^max_depth:[^\n]*$", re.MULTILINE)
_COMMENT = re.compile(r"[ \t]+#.*$")


def with_max_depth(text: str, value: int) -> tuple[str, int]:
    """``(new text, old value)``: ``text`` with ``max_depth`` set to ``value`` in its settings block and everything else as it was (the other keys
    with their comments, the body byte for byte). The old value is the one the settings read (the default when the key is missing). An ``OrgError``
    when ``value`` is not a whole number >= 1, or the settings block cannot be read as a mapping: nothing is to be written then."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise OrgError(f"max_depth is a whole number >= 1, not {value!r}. Nothing was written.")
    try:
        meta, _ = split_frontmatter(text)
        if text.startswith("---\n") and text.find("\n---\n", 4) == -1:
            raise ValueError("the settings block has no end")
        old = int(config_number(parse_config(text), "max_depth", int))
    except Exception as exc:  # noqa: BLE001 - YAML that does not parse: ORG.md is left as it is
        raise OrgError(f"ORG.md cannot be read ({exc}), so max_depth was not changed. Nothing was written.") from exc
    if not text.startswith("---\n"):
        new = f"---\nmax_depth: {value}\n---\n{text}"
    else:
        end = text.find("\n---\n", 4)
        block = text[: end + 1]
        found = _LINE.search(block)
        if found is None:
            new = block + f"max_depth: {value}\n" + text[end + 1 :]
        else:
            comment = _COMMENT.search(found.group(0))
            new = text[: found.start()] + f"max_depth: {value}" + (comment.group(0) if comment else "") + text[found.end() :]
    try:
        after, _ = split_frontmatter(new)
    except Exception as exc:  # noqa: BLE001 - the rewrite itself must parse
        raise OrgError(f"ORG.md would not be readable after the change ({exc}). Nothing was written.") from exc
    if after != {**meta, "max_depth": value}:
        raise OrgError("ORG.md's max_depth is written in a form this change cannot rewrite safely. Nothing was written.")
    return new, old
