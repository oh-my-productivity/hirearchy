"""The reflection digest: the cases with new evidence, as a compact block of lines."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from ..kernel import clip_line
from ..services import ServiceCatalog
from .api import Case, CaseHistory, ReflectionDigest, stats_by_version

DIGEST_CASES = 6  # cases with new evidence shown in the digest
DIGEST_CHARS = 3000  # soft limit of the whole digest
CLIP_LESSON = 220
CLIP_NOTE = 160
MAX_VERDICTS = 4  # verdicts of one case shown in a digest line


def verdict_chain(c: Case) -> str:
    """The client's verdicts in order, each with her words: ``reject "too long" -> accept "this one is right"``."""
    raise NotImplementedError  # red: C-reflection


def case_line(c: Case) -> str:
    """One case in one line: state, playbook, runs, reworks, the client's verdicts, then the lessons (the latest first)."""
    raise NotImplementedError  # red: C-reflection


class DigestBuilder(ReflectionDigest):
    """The most recent cases that have evidence newer than the playbook, and one line of statistics per version of it."""

    def __init__(self, catalog: ServiceCatalog, history: CaseHistory) -> None:
        self._catalog = catalog
        self._history = history

    def reflection_digest(self, owner: str, service: str) -> str | None:
        raise NotImplementedError  # red: C-reflection
