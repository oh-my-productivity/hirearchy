"""The reflection digest: the cases with new evidence, as a compact block of lines."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from ..kernel import clip_line
from ..services import ServiceCatalog
from .api import Case, CaseHistory, ReflectionDigest, regressions, stats_by_version

DIGEST_CASES = 6  # cases with new evidence shown in the digest
DIGEST_CHARS = 3000  # soft limit of the whole digest
CLIP_LESSON = 220
CLIP_NOTE = 160
MAX_VERDICTS = 4  # verdicts of one case shown in a digest line


def verdict_chain(c: Case, assertions: Mapping[str, str] | None = None) -> str:
    """The client's verdicts in order, each with her words: ``reject "too long" -> accept "this one is right"``.

    ``assertions`` maps the id of a verdict note to its ``R<k>``: a rejection that has one reads ``reject R1 "too long"``. A relayed verdict reads
    ``reject (relayed) "..."`` or ``accept (relayed)``."""
    shown = c.verdicts[-MAX_VERDICTS:]
    clip = CLIP_NOTE if len(shown) <= 2 else CLIP_NOTE // 2
    ids = assertions or {}
    parts = [
        v.verdict
        + (" (relayed)" if v.tier == "relayed" else f" {ids[v.message.id]}" if v.message.id in ids else "")
        + (f' "{clip_line(v.note, clip)}"' if v.note else "")
        for v in shown
    ]
    if len(c.verdicts) > len(shown):
        parts.insert(0, "…")
    return " -> ".join(parts)


def case_line(c: Case, assertions: Mapping[str, str] | None = None) -> str:
    """One case in one line: state, playbook, runs, reworks, the client's verdicts, then the lessons (the latest first)."""
    bits = [f'case {c.id} "{clip_line(c.title, 40)}": {c.state}', f"playbook v{c.used}", f"{c.runs} of {c.budget} runs"]
    if c.reworks:
        bits.append(f"{c.reworks} rework(s)" + (f", {c.relayed_reworks} relayed" if c.relayed_reworks else ""))
    line = ", ".join(bits)
    if c.verdicts:  # the client's verdicts come before the lessons: her words outrank the owner's own conclusions
        who = "client feedback (an agent client: hypotheses)" if c.client_kind == "agent" else "client feedback"
        line += f"; {who}: {verdict_chain(c, assertions)}"
    if c.lessons:
        # The latest result is the team's final word on the case, earlier lessons only where room remains; a relayed rework's lessons are
        # marked: they are not the client's.
        sources = [*c.lesson_sources, *[""] * (len(c.lessons) - len(c.lesson_sources))]
        latest = c.lessons[-1]
        earlier = " / ".join(("(relayed) " if s == "relayed" else "") + x for x, s in zip(c.lessons[:-1], sources))
        first_reject = next((v.message.id for v in c.verdicts if v.verdict == "reject"), None)
        after = first_reject is not None and bool(c.lesson_ids) and c.lesson_ids[-1] > first_reject
        marks = [*(["from a relayed rework, not the client's"] if sources[-1] == "relayed" else []),
                 *(["written after the reject: check it against her words"] if after else [])]
        mark = f" ({'; '.join(marks)})" if marks else ""
        line += f'; lessons{mark}: "{clip_line(latest, CLIP_LESSON)}"'
        room = CLIP_LESSON - len(latest)
        if earlier and room > 40:
            line += f'; earlier: "{clip_line(earlier, room)}"'
    return "- " + line


class DigestBuilder(ReflectionDigest):
    """The most recent cases that have evidence newer than the playbook, and one line of statistics per version of it."""

    def __init__(self, catalog: ServiceCatalog, history: CaseHistory) -> None:
        self._catalog = catalog
        self._history = history

    def reflection_digest(self, owner: str, service: str) -> str | None:
        pb = self._catalog.read_playbook(owner, service)
        items = self._history.cases(owner, service)
        since = pb.revised if pb.version else None
        fresh = [c for c in items if c.evidence_at and (since is None or c.evidence_at > since)]
        if not fresh:
            return None
        fresh.sort(key=lambda c: cast(datetime, c.evidence_at))  # every case in ``fresh`` has evidence
        shown = fresh[-DIGEST_CASES:][::-1]
        ids = {a.verdict.message.id: a.id for a in regressions(items)}
        per_version = [f"- v{v}: {s.line()}" for v, s in stats_by_version(items).items()]
        while True:
            lines = [case_line(c, ids) for c in shown]
            text = "Cases with new evidence (most recent first):\n" + "\n".join(lines) + "\nBy playbook version:\n" + "\n".join(per_version)
            if len(text) <= DIGEST_CHARS or len(shown) == 1:
                return text if len(text) <= DIGEST_CHARS else text[: DIGEST_CHARS - 1].rstrip() + "…"
            shown = shown[:-1]
