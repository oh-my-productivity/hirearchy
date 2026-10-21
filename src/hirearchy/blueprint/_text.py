"""Text the plan shows on one line (package-private). Not ``kernel.clip_line``: this one cuts at a sentence boundary."""

from __future__ import annotations

import re

from ._view import s

CLIP = 400  # characters a one-line field of the plan block may take before it is cut at a sentence boundary
GOAL_CLIP = 800  # the Goal line: the whole mission, unless it is really long


def clip(text: object, limit: int = CLIP) -> str:
    """One line of ``text`` that never ends mid-sentence.

    Whole sentences are kept while they fit in ``limit`` characters; the first sentence is always kept whole, however
    long. When sentences were left out, the line says so (the full text is in the details).
    """
    line = " ".join(s(text).split())
    if len(line) <= limit:
        return line
    sentences = re.split(r"(?<=[.!?])\s+", line)
    out = sentences[0]
    for sentence in sentences[1:]:
        if len(out) + 1 + len(sentence) > limit:
            break
        out += " " + sentence
    return out if out == line else out + " (the rest is in the details)"
