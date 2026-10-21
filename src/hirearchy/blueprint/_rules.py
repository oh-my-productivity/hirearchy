"""The text heuristics and small predicates the blueprint rules are made of (package-private, pure)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import cast

from ..kernel import inside
from ._view import WRITE_TOOLS, criteria_of, deliverable_of, needs_of, s, services_of, svc_criteria, svc_deliverable, task_of
from .api import Agent, Issue

WEB_STRONG = re.compile(r"https?://|\bweb\s*(?:search\w*|fetch\w*|access|sources?|sites?|pages?|research\w*|brows\w+)|\bwebsites?\b|\burls?\b|\binternet\b|\bonline\b|\bcit(?:e|es|ed|ation|ations)\b|\bbrowse\w*", re.I)
WEB_WEAK = re.compile(r"\b(?:current|latest|up-to-date|recent|as of|pricing|prices?|releases?|licen[sc]es?)\b", re.I)
NO_WEB = re.compile(r"\b(?:no|without|not)\s+(?:the\s+)?(?:web|internet|online)\b|\boffline\b", re.I)
_CODE = re.compile(
    r"\b(?:code|codebase|software|library|cli|script|implement\w*|program|repo|repository|pytest|refactor\w*|compile\w*|"
    r"command[- ]line|python package|unit tests?)\b", re.I)
_VAGUE = re.compile(
    r"\b(?:good|great|nice|high[- ]quality|comprehensive|thorough|appropriate|as needed|etc|well[- ]written|professional|"
    r"robust|solid|reasonable|clear|useful)\b", re.I)
TIERED = re.compile(r"cheap|strong|tier|haiku|draft", re.I)
_NEG_BEFORE = re.compile(r"(?:never|not|n't|no|nobody|cannot|without|nor)\W+(?:\w+\W+){0,3}$", re.I)
_EDITS_OTHERS = re.compile(
    r"\b(?:apply|make|write|put)\w*\s+(?:[\w']+\s+){0,3}(?:corrections?|fixes|changes|edits)\b[^.\n]{0,60}"
    r"|\b(?:edit|modif\w+|overwrit\w+|patch|rewrite|fix|correct)\w*\s+(?:[\w']+\s+){0,3}(?:directly|in place)\b"
    r"|\b(?:directly|in place)\b[^.\n]{0,30}\b(?:edit|modif\w+|correct\w*|fix\w*|updat\w+)"
    r"|\b(?:edit|modif\w+|overwrit\w+|patch|rewrite)\w*\s+(?:[\w']+\s+){0,3}(?:report|draft|file|code|document|deliverable)\b"
    r"|\bapply\w*\s+(?:them|it|these|those|the\s+\w+)\s+to\s+the\s+(?:report|draft|file|code|document|deliverable)\b"
    r"|\bcorrect(?:ed|ions?)?\b[^.\n]{0,25}\bdirectly\b",
    re.I)


def edits_others_files(text: str) -> str | None:
    """The first phrase in ``text`` that tells someone to change another agent's file, or None.

    The runtime lets an agent write only in its own directory, so "apply corrections directly to the report" can
    never be satisfied by a reviewer. Negated phrases ("never edit the report") are fine.
    """
    for m in _EDITS_OTHERS.finditer(text):
        if not _NEG_BEFORE.search(text[max(0, m.start() - 40):m.start()]):
            return m.group(0).strip()
    return None


def is_code(bp: Mapping[str, object]) -> bool:
    kind = s(needs_of(bp).get("kind")).lower()
    if kind:
        return kind == "code"
    d = deliverable_of(bp)
    parts = [bp.get("mission"), d.get("description"), d.get("format"), task_of(bp).get("goal")]
    for x in services_of(bp):
        parts += [x.get("description"), svc_deliverable(x).get("description"), svc_deliverable(x).get("format")]
    return bool(_CODE.search(" ".join(s(x) for x in parts)))


def blob(bp: Mapping[str, object]) -> str:
    n, d = needs_of(bp), deliverable_of(bp)
    t = task_of(bp)
    parts = [bp.get("mission"), n.get("scope"), n.get("sources"), n.get("quality_bar"), d.get("description"),
             d.get("format"), t.get("goal"), *criteria_of(bp)]
    for x in services_of(bp):  # what a service promises needs the same tools as what a task asks for
        sd = svc_deliverable(x)
        parts += [x.get("description"), sd.get("description"), sd.get("format"), *svc_criteria(x)]
        parts += [i.get("description") for i in cast("Iterable[object]", x.get("inputs") or []) if isinstance(i, dict)]
    return "\n".join(s(p) for p in parts if p)


def review_required(needs: Mapping[str, object]) -> bool | None:
    r = needs.get("review")
    if r is None or r == "":
        return None
    if isinstance(r, bool):
        return r
    return not re.match(r"\s*(?:no|none|false|not required|skip)\b", s(r), re.I)


def has_ws_tools(a: Agent) -> bool:
    return all(t in a.tools for t in WRITE_TOOLS)


def vague(crit: Sequence[str], where: str, issues: list[Issue]) -> None:
    """Warn about acceptance criteria that no one could check (too short, or vague words without a number or format)."""
    for i, c in enumerate(crit, 1):
        checkable = re.search(r"\d|[`\"'/]|\b(?:every|each|all|none|only|exactly)\b", c)
        if len(c.split()) < 4 or (_VAGUE.search(c) and not checkable):
            issues.append(Issue("warning", f"{where}[{i}]", f"'{c}' is not checkable; state the exact number, section, format or path that decides pass/fail", "vague-criterion"))


def delivers_directly(agents: Sequence[Agent], p: Path) -> bool:
    """Some author with write+shell can put files at ``p`` itself (otherwise the assistant copies the result there)."""
    return any(has_ws_tools(a) and a.workspace and inside(p, Path(a.workspace)) and a.kind == "author" for a in agents)
