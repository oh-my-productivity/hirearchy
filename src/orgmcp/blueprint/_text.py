"""Text the plan shows on one line (package-private). Not ``kernel.clip_line``: this one cuts at a sentence boundary."""
from __future__ import annotations
import re
from ._view import s
CLIP = 400
GOAL_CLIP = 800

def clip(text: object, limit: int=CLIP) -> str:
    """One line of ``text`` that never ends mid-sentence.

    Whole sentences are kept while they fit in ``limit`` characters; the first sentence is always kept whole, however
    long. When sentences were left out, the line says so (the full text is in the details).
    """
    raise NotImplementedError('red: C-blueprint-1')
