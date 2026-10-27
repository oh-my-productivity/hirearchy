"""The reflection digest: the cases with new evidence, as a compact block of lines."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from ..kernel import clip_line
from ..services import ServiceCatalog
from .api import Case, CaseHistory, ReflectionDigest, regressions, stats_by_version

DIGEST_CASES = 6  # cases with new evidence shown in the digest
DIGEST_CHARS = 3000  # soft limit of the whole digest
CLIP_LESSON = 220
CLIP_NOTE = 160
CLIP_PART = 60  # characters of one part of an after-action review in the digest
MAX_VERDICTS = 4  # verdicts of one case shown in a digest line
MORE = "… (more: services)"  # what a clipped digest ends with: `services` lists the rest


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


@dataclass(frozen=True)
class AarParts:
    """The parts of an after-action review a team wrote in its ``lessons`` (design 11); a part the text does not have is ``""``."""

    expected: str = ""
    happened: str = ""
    caught_at: str = ""
    cause: str = ""
    prevent: str = ""
    near_miss: str = ""


_FIELDS = {"expected": "expected", "happened": "happened", "caught at": "caught_at", "cause": "cause", "prevent": "prevent", "near miss": "near_miss"}
_SHOWN = (("Expected", "expected"), ("Happened", "happened"), ("Caught at", "caught_at"), ("Cause", "cause"), ("Prevent", "prevent"), ("Near miss", "near_miss"))
_LABEL = re.compile(r"(?:^|(?<=[.;\n]))[ \t]*(expected|happened|caught\s+at|cause|prevent|near\s+miss)[ \t]*:[ \t]*", re.IGNORECASE)
NO_NEAR_MISS = "none recorded"


def aar_parts(text: str) -> AarParts | None:
    """The labelled parts of ``text``, or None when it has no label (pure). A label (``Expected:``, ``Happened:``, ``Caught at:``, ``Cause:``,
    ``Prevent:``, ``Near miss:``) counts at the start of the text or after a sentence end (``.``, ``;``, a newline), in any case; a part runs to the next
    label. The first part with a label wins when a label repeats."""
    found = list(_LABEL.finditer(text))
    if not found:
        return None
    values: dict[str, str] = {}
    for m, following in zip(found, [*found[1:], None]):
        part = " ".join(text[m.end() : following.start() if following else len(text)].split()).rstrip(" .;")
        values.setdefault(_FIELDS[" ".join(m.group(1).lower().split())], part)
    return AarParts(**values)


def _owners_view(lesson: str, accepted: bool) -> str:
    """A case's latest lesson as the owner's view (design 11): the labelled parts, each clipped to ``CLIP_PART`` and the whole to ``CLIP_LESSON``;
    for an accepted case its near miss; the lesson quoted when it has no label."""
    parts = aar_parts(lesson)
    if accepted:
        return f"near miss: {clip_line(parts.near_miss, CLIP_PART) if parts and parts.near_miss else NO_NEAR_MISS}"
    shown = [f"{label} {clip_line(getattr(parts, name), CLIP_PART)}" for label, name in _SHOWN if parts and getattr(parts, name)]
    return clip_line(" | ".join(shown), CLIP_LESSON) if shown else f'"{clip_line(lesson, CLIP_LESSON)}"'


def case_line(c: Case, assertions: Mapping[str, str] | None = None) -> str:
    """One case in one line: state, playbook, runs, reworks, the client's verdicts, then the owner's view of the lessons (the latest first)."""
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
        view = _owners_view(latest, bool(c.verdicts) and c.verdicts[-1].verdict == "accept")
        line += f"; owner's view{mark}: {view}"
        room = CLIP_LESSON - (len(view) - 2 if view.startswith('"') else len(view))  # the quotes of a quoted lesson are not its words
        if earlier and room > 40:
            line += f'; earlier: "{clip_line(earlier, room)}"'
    return "- " + line


class DigestBuilder(ReflectionDigest):
    """The most recent cases that have evidence newer than the playbook, and one line of statistics per version of it."""

    def __init__(self, catalog: ServiceCatalog, history: CaseHistory) -> None:
        self._catalog = catalog
        self._history = history

    def reflection_digest(self, owner: str, service: str, words: int | None = None) -> str | None:
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
            text = self._text(lines, per_version)
            if (len(text) <= DIGEST_CHARS and (words is None or len(text.split()) <= words)) or len(shown) == 1:
                break
            shown = shown[:-1]  # the oldest of the shown cases goes first
        if len(text) > DIGEST_CHARS:
            text = text[: DIGEST_CHARS - 1].rstrip() + "…"
        if words is not None and len(text.split()) > words:
            text = self._text([self._clipped(lines[0], words - len(self._text([""], per_version).split()))], per_version)
            if len(text.split()) > words:  # the other lines alone are too long for the room: cut the whole block
                text = _cut(text, words)
        return text

    @staticmethod
    def _text(lines: list[str], per_version: list[str]) -> str:
        return "Cases with new evidence (most recent first):\n" + "\n".join(lines) + "\nBy playbook version:\n" + "\n".join(per_version)

    @staticmethod
    def _clipped(line: str, room: int) -> str:
        """``line`` cut to ``room`` words, ending with ``MORE`` (at least the first word stays)."""
        keep = max(room - len(MORE.split()), 1)
        found = line.split()
        return line if len(found) <= room else " ".join(found[:keep]) + " " + MORE


def _cut(text: str, words: int) -> str:
    """``text`` cut after the words that fit, ending with ``MORE`` (the last resort when even one case line and the statistics are too long)."""
    marks = list(re.finditer(r"\S+", text))
    keep = max(words - len(MORE.split()), 1)
    return text[: marks[keep - 1].end()] + " " + MORE
