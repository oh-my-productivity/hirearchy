"""The text heuristics and small predicates the blueprint rules are made of (package-private, pure)."""
from __future__ import annotations
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import cast
from ..kernel import inside
from ._view import WRITE_TOOLS, criteria_of, deliverable_of, needs_of, s, services_of, svc_criteria, svc_deliverable, task_of
from .api import Agent, Issue
WEB_STRONG = re.compile('https?://|\\bweb\\s*(?:search\\w*|fetch\\w*|access|sources?|sites?|pages?|research\\w*|brows\\w+)|\\bwebsites?\\b|\\burls?\\b|\\binternet\\b|\\bonline\\b|\\bcit(?:e|es|ed|ation|ations)\\b|\\bbrowse\\w*', re.I)
WEB_WEAK = re.compile('\\b(?:current|latest|up-to-date|recent|as of|pricing|prices?|releases?|licen[sc]es?)\\b', re.I)
NO_WEB = re.compile('\\b(?:no|without|not)\\s+(?:the\\s+)?(?:web|internet|online)\\b|\\boffline\\b', re.I)
_CODE = re.compile('\\b(?:code|codebase|software|library|cli|script|implement\\w*|program|repo|repository|pytest|refactor\\w*|compile\\w*|command[- ]line|python package|unit tests?)\\b', re.I)
_VAGUE = re.compile('\\b(?:good|great|nice|high[- ]quality|comprehensive|thorough|appropriate|as needed|etc|well[- ]written|professional|robust|solid|reasonable|clear|useful)\\b', re.I)
TIERED = re.compile('cheap|strong|tier|haiku|draft', re.I)
_NEG_BEFORE = re.compile("(?:never|not|n't|no|nobody|cannot|without|nor)\\W+(?:\\w+\\W+){0,3}$", re.I)
_EDITS_OTHERS = re.compile("\\b(?:apply|make|write|put)\\w*\\s+(?:[\\w']+\\s+){0,3}(?:corrections?|fixes|changes|edits)\\b[^.\\n]{0,60}|\\b(?:edit|modif\\w+|overwrit\\w+|patch|rewrite|fix|correct)\\w*\\s+(?:[\\w']+\\s+){0,3}(?:directly|in place)\\b|\\b(?:directly|in place)\\b[^.\\n]{0,30}\\b(?:edit|modif\\w+|correct\\w*|fix\\w*|updat\\w+)|\\b(?:edit|modif\\w+|overwrit\\w+|patch|rewrite)\\w*\\s+(?:[\\w']+\\s+){0,3}(?:report|draft|file|code|document|deliverable)\\b|\\bapply\\w*\\s+(?:them|it|these|those|the\\s+\\w+)\\s+to\\s+the\\s+(?:report|draft|file|code|document|deliverable)\\b|\\bcorrect(?:ed|ions?)?\\b[^.\\n]{0,25}\\bdirectly\\b", re.I)

def edits_others_files(text: str) -> str | None:
    """The first phrase in ``text`` that tells someone to change another agent's file, or None.

    The runtime lets an agent write only in its own directory, so "apply corrections directly to the report" can
    never be satisfied by a reviewer. Negated phrases ("never edit the report") are fine.
    """
    raise NotImplementedError('red: C-blueprint-1')

def is_code(bp: Mapping[str, object]) -> bool:
    raise NotImplementedError('red: C-blueprint-1')

def blob(bp: Mapping[str, object]) -> str:
    raise NotImplementedError('red: C-blueprint-1')

def review_required(needs: Mapping[str, object]) -> bool | None:
    raise NotImplementedError('red: C-blueprint-1')

def has_ws_tools(a: Agent) -> bool:
    raise NotImplementedError('red: C-blueprint-1')

def vague(crit: Sequence[str], where: str, issues: list[Issue]) -> None:
    """Warn about acceptance criteria that no one could check (too short, or vague words without a number or format)."""
    raise NotImplementedError('red: C-blueprint-1')

def delivers_directly(agents: Sequence[Agent], p: Path) -> bool:
    """Some author with write+shell can put files at ``p`` itself (otherwise the assistant copies the result there)."""
    raise NotImplementedError('red: C-blueprint-1')
