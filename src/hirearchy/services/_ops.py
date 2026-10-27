"""``revise_playbook`` changes one item per call (design 5): the rules that judge a change, and the owner's reviser.

Pure rules first: the 30% rule (7), the two lists of the cap's refusal (10) and the weakening rule (9.1). Each refusal text is a constant beside its rule."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..kernel import OrgError
from .api import ItemWatch, PlaybookItem, text_tokens

# ----------------------------------------------------------------------------------------------------------------------- the 30% rule (7)

SPLIT_FLOOR = 50  # words: the limit of a small playbook (this design's labelled default, not configurable)
PB_SPLIT = (
    "refused: this change touches {changed} of the playbook's {base} words, more than about 30% ({limit}): make it as smaller changes (one item, or "
    "part of an item, per call), each with its own reason and evidence, so each one is judged and watched on its own. Nothing was written."
)


def item_tokens(item: PlaybookItem) -> list[str]:
    """The content words of one item as text tokens (pure): its ``text`` and, for a rule, its ``when`` (``always`` counts none)."""
    always = item.when.strip().lower() in ("", "always")
    return [*text_tokens(item.text), *([] if always else text_tokens(item.when))]


def content_tokens(items: Sequence[PlaybookItem], headings: Sequence[str] = ()) -> list[str]:
    """The content words of a playbook as text tokens (pure): those of every live item (:func:`item_tokens`) and of the section headings. Item
    markers, the WHEN/THEN/WHY keywords and the ids after WHY are no words, so a migration's markers never count."""
    return [*(tok for h in headings for tok in text_tokens(h)), *(tok for i in items for tok in item_tokens(i))]


def split_limit(base: int) -> int:
    """The most words one gated change may touch in a playbook of ``base`` content words: about 30% (rounded up), and at least 50."""
    return max(-(-3 * base // 10), SPLIT_FLOOR)


def split_check(current: Sequence[str], new: Sequence[str]) -> None:
    """Refuse (PB-SPLIT) a change that touches more than ``max(ceil(0.3 x base), 50)`` words (pure). ``current`` and ``new`` are the content words
    (:func:`content_tokens`) of the playbook before and after; ``changed`` is the size of the multiset difference both ways, ``base`` the size of
    ``current`` (0 for an empty playbook: the limit is then the floor)."""
    before, after = Counter(current), Counter(new)
    changed = sum((after - before).values()) + sum((before - after).values())
    limit = split_limit(len(current))
    if changed > limit:
        raise OrgError(PB_SPLIT.format(changed=changed, base=len(current), limit=limit))


# ----------------------------------------------------------------------------------------------------------------------- the cap (10)

CAP_LISTED = 5  # items each list of the cap's refusal names, at most
PB_CAP = (
    "refused: the playbook would have {n} words; the limit is {cap} (playbook_max_words). Retire an item first.{candidates}{uncovered}{rest} "
    "Nothing was written."
)
PB_CAP_CANDIDATES = " Candidates, oldest first (new items whose watch rests on no regression assertion): {items}."
PB_CAP_UNCOVERED = " Items that cover no criterion or assertion (no acknowledgement needed): {items}."
PB_CAP_EMPTY = " Every item covers a criterion or an assertion: retire one yourself (it needs {client}'s acknowledgement), or shorten one."
PB_CAP_SHORTEN = ' Or shorten an item (op="edit").'


@dataclass(frozen=True)
class CapCandidate:
    """A new item whose watch rests on no regression assertion (10): its id, the version that gave it its text, and what it covers."""

    id: str
    since: int
    covers: tuple[str, ...] = ()


def _number(item_id: str) -> int:
    return int(item_id[1:]) if item_id[1:].isdigit() else 0


def cap_lists(
    items: Sequence[PlaybookItem], watches: Mapping[str, ItemWatch], started: Mapping[str, Sequence[str]], current: int = 0,
) -> tuple[list[CapCandidate], list[tuple[str, int]]]:
    """The two lists of the cap's refusal (pure), each at most 5. First: the live items in ``new`` that continue no other watch and whose watch
    rests on no ``R<k>``, oldest first; ``started`` maps an item to the ``why`` ids of the gated change that started its watch (an item without
    an entry, such as one whose watch an exempt restore started, is none). Second: the oldest live items that cover no criterion or assertion
    (their retire needs no acknowledgement); an item the watch does not know counts as ``current`` (the version it is read in). ``watches`` maps
    an item to its ``ItemWatch``."""
    live = [i.id for i in items]

    def since(item_id: str) -> int:
        return watches[item_id].text_version if item_id in watches else current

    candidates = sorted(
        (
            i for i in live
            if i in watches and watches[i].state == "new" and not watches[i].carried and i in started
            and not any(x.startswith("R") for x in started[i])
        ),
        key=lambda i: (since(i), _number(i)),
    )
    uncovered = sorted((i for i in live if not (watches[i].coverage if i in watches else ())), key=lambda i: (since(i), _number(i)))
    return (
        [CapCandidate(i, since(i), watches[i].coverage) for i in candidates[:CAP_LISTED]],
        [(i, since(i)) for i in uncovered[:CAP_LISTED]],
    )


def cap_refusal(n: int, cap: int, candidates: Sequence[CapCandidate], uncovered: Sequence[tuple[str, int]], client: str) -> str:
    """PB-CAP (pure): the playbook would have ``n`` content words, over ``cap``; the two lists say what to retire. With both empty, the refusal says
    that every item covers something, so retiring one needs ``client``'s acknowledgement."""
    named = [
        f"{c.id} (since v{c.since}; cites {', '.join(c.covers)}: retiring it needs {client}'s acknowledgement)" if c.covers else f"{c.id} (since v{c.since})"
        for c in candidates
    ]
    old = [f"{item_id} (since v{since})" for item_id, since in uncovered]
    return PB_CAP.format(
        n=n, cap=cap,
        candidates=PB_CAP_CANDIDATES.format(items=", ".join(named)) if named else "",
        uncovered=PB_CAP_UNCOVERED.format(items=", ".join(old)) if old else "",
        rest=PB_CAP_SHORTEN if named or old else PB_CAP_EMPTY.format(client=client),
    )


# ----------------------------------------------------------------------------------------------------------------------- weakening (9.1)


def weakening(old: PlaybookItem | None, new: PlaybookItem, old_coverage: Sequence[str], new_coverage: Sequence[str]) -> bool:
    """Whether replacing the live text ``old`` with ``new`` lowers a bar (pure): (i) the new text's coverage lacks an id of the old text's, or (ii)
    the new text's content words are a strict sub-multiset of the old text's (it only deletes words). A formatting fix (equal tokens) is never
    weakening, and neither is a restore of a retired item (``old`` is None: it replaces no live text)."""
    if old is None:
        return False
    before, after = Counter(item_tokens(old)), Counter(item_tokens(new))
    if before == after:
        return False
    return any(i not in new_coverage for i in old_coverage) or not after - before
