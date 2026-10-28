"""The shape of a one-off case (design section 3): two of root's one-off tasks are of one shape when they went to the same assignee and (i) their title
skeletons are equal, (ii) their criteria keys are equal, or (iii) the Jaccard index of their criteria token sets is at least ``shape_overlap``. A shape
group is a connected set of such tasks (union-find). Pure."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from ..kernel import strip_markers
from ..services import line_key, text_tokens
from ._views import OneOffCase

RELATIONS = ("title", "criteria", "overlap")  # the order in which a pair is tried and a group lists what joined it
MIN_TOKENS = 3  # a token set of fewer words never matches by overlap


def _digitless(tokens: Sequence[str]) -> list[str]:
    return [t for t in tokens if not any(ch.isdigit() for ch in t)]


def title_skeleton(title: str) -> tuple[str, ...]:
    """The :func:`text_tokens` of ``title`` without the tokens that contain a digit."""
    return tuple(_digitless(text_tokens(title)))


def criteria_key(lines: Sequence[str]) -> tuple[str, ...]:
    """The sorted tuple of the :func:`line_key` of every line, each with its digit runs replaced by ``#``; a line with no letter or digit has no key and
    is left out, so ``()`` is the key of a section with no line."""
    return tuple(sorted(key for line in lines if (key := re.sub(r"\d+", "#", line_key(line)))))


def criteria_tokens(lines: Sequence[str]) -> frozenset[str]:
    """The union of the :func:`text_tokens` of the lines without the tokens that contain a digit."""
    return frozenset(t for line in lines for t in _digitless(text_tokens(strip_markers(line))))


def related(a: OneOffCase, b: OneOffCase, overlap: Fraction) -> str:
    """The relation that makes ``a`` and ``b`` one shape (``title``, ``criteria`` or ``overlap``, tried in that order), ``""`` when they are not.
    An empty title skeleton, an empty criteria key and a token set of fewer than ``MIN_TOKENS`` words never match."""
    if a.assignee != b.assignee:
        return ""
    skeleton = title_skeleton(a.title)
    if skeleton and skeleton == title_skeleton(b.title):
        return "title"
    key = criteria_key(a.criteria)
    if key and key == criteria_key(b.criteria):
        return "criteria"
    left, right = criteria_tokens(a.criteria), criteria_tokens(b.criteria)
    if len(left) >= MIN_TOKENS and len(right) >= MIN_TOKENS and Fraction(len(left & right), len(left | right)) >= overlap:
        return "overlap"
    return ""


@dataclass(frozen=True)
class ShapeGroup:
    """A connected set of two or more one-off cases of one shape: ``cases`` by id, ``relations`` the relations that joined pairs of them."""

    cases: tuple[OneOffCase, ...]
    relations: tuple[str, ...]

    @property
    def head(self) -> str:
        """The smallest case id of the group."""
        return self.cases[0].id

    @property
    def assignee(self) -> str:
        return self.cases[0].assignee


def groups(cases: Sequence[OneOffCase], overlap: Fraction) -> tuple[ShapeGroup, ...]:
    """The shape groups of ``cases`` with two or more members, ordered by their smallest id; the order of ``cases`` does not matter."""
    ordered = sorted(cases, key=lambda c: c.id)
    parent = list(range(len(ordered)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    pairs: list[tuple[int, int, str]] = []
    for i, a in enumerate(ordered):
        for j in range(i + 1, len(ordered)):
            if relation := related(a, ordered[j], overlap):
                pairs.append((i, j, relation))
                parent[find(j)] = find(i)
    members: dict[int, list[OneOffCase]] = {}
    for i, case in enumerate(ordered):
        members.setdefault(find(i), []).append(case)
    joined: dict[int, set[str]] = {}
    for i, _, relation in pairs:
        joined.setdefault(find(i), set()).add(relation)
    found = [ShapeGroup(tuple(group), tuple(r for r in RELATIONS if r in joined.get(root, set()))) for root, group in members.items() if len(group) > 1]
    return tuple(sorted(found, key=lambda g: g.head))
