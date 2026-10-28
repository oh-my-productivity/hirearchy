"""The structural changes of the organization with who made them, and the unprompted charter edits (design 4.5, section 3; pure).

A change is an agent created or retired, a service defined or retired, a charter changed (a body edit, a frontmatter key, a line of the added section) or ORG.md's
``max_depth``. Each gets one label, read from what the files themselves record (``approved_in``, ``hired_by``, ``RETIRED.md``, the committed charters, the ``write``
events), never from a commit message: a commit can hold another process's edit, and root's tool calls do not commit.

An unprompted charter edit is a change between two committed versions of an agent's charter that no extension of the user's explains: the pairs labelled ``by {parent}``,
``outside the tools`` or ``by {parent}, or outside the tools``. A deletion, a re-created address and every path under ``.retired/`` are no edits."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..kernel import parent as parent_of
from ..services import line_key
from ._ports import CharterPair, CharterVersions, KeyChange
from ._views import AgentFact, EventFacts, RetiredFact, ServiceFact, ServiceRetired
from .api import BriefRecord

PLAN_LABEL = "from the plan you approved ({date})"
CHANGE_LABEL = "from your change {id}"
INSIDE_LABEL = "inside the plan, by {lead}"
PARENT_LABEL = "by {parent}"
HAND_LABEL = "outside the tools (a hand edit or the terminal)"
ROOT_LABEL = "by root, outside a plan (the terminal, or before this record was kept)"
BACK_LABEL = "taken back: the change {id} was not applied"
UNSURE_LABEL = "by {parent}, or outside the tools (the event log does not reach back)"
NO_HISTORY = "charter history unknown (no git history)"
TRUNCATED = "{n} or more (the history read stops at 40 commits)"
LIMITS = "Your hiring limits were set by the user's change:"  # the prefix of the limits line of an extension (blueprint/_added.py)
SAME_SECOND = timedelta(seconds=1)  # a commit time has whole seconds and an event time milliseconds
ROOT = "root"
PLAN_HEADING = "## Assignment (from the approved plan)"

_APPROVAL = re.compile(r"(plan|change) (\S+)(?: \((not applied)\))?")
_TAG = re.compile(r" \[change ([^\]]+)\]$")
_LIMITS_LINE = re.compile(r"up to (\d+) direct reports; may hire: (yes|no)")
_APPLIED = re.compile(r"root: applied extension (\S+)")
_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Change:
    """One structural change. ``kind`` is ``agent-created``, ``agent-retired``, ``service-defined``, ``service-retired``, ``charter`` or ``depth``; ``subject``
    the address, ``owner/name`` or ``ORG.md``; ``by`` who made it (``""`` when the files do not say); ``plan_id`` the id of the plan or change that approved it.
    ``text`` is the change as D8 words it, ``label`` who made it (``""`` when the files do not say), ``unprompted`` whether it counts as an unprompted charter
    edit; ``line`` is the D8 line, ``{text}: {label}``."""

    when: datetime | None
    kind: str
    subject: str
    text: str
    label: str
    by: str = ""
    plan_id: str = ""
    unprompted: bool = False

    @property
    def line(self) -> str:
        return f"{self.text}: {self.label}" if self.label else self.text


@dataclass(frozen=True)
class ChangeFacts:
    """Everything the changes are read from: the agents, the retired trees, the services and their retired copies, the committed charters (``versions``), the
    subjects of the commits that changed ORG.md, the ``write`` events, the briefs held (so that a change that is the effect of an item names it)."""

    agents: tuple[AgentFact, ...] = ()
    retired: tuple[RetiredFact, ...] = ()
    services: tuple[ServiceFact, ...] = ()
    retired_services: tuple[ServiceRetired, ...] = ()
    versions: CharterVersions = field(default_factory=CharterVersions)
    subjects: Mapping[str, str] = field(default_factory=dict)
    events: EventFacts = field(default_factory=EventFacts)
    briefs: tuple[BriefRecord, ...] = ()


@dataclass(frozen=True)
class Changes:
    """The changes since a time, oldest first, and the count of the unprompted charter edits among them. ``known`` is false without a git history (the count
    is then None); ``truncated``: the history read was cut, so the count is a floor."""

    changes: tuple[Change, ...]
    known: bool
    unprompted: int | None
    truncated: bool = False

    @property
    def unprompted_text(self) -> str:
        """The count as D8 words it: ``unknown`` without git, ``{n} or more (...)`` when the history read was cut."""
        if self.unprompted is None:
            return "unknown"
        return TRUNCATED.format(n=self.unprompted) if self.truncated else str(self.unprompted)

    @property
    def charter_line(self) -> str:
        """The line that stands for the charter and limit lines without a history; ``""`` with one."""
        return "" if self.known else NO_HISTORY


def _date(when: datetime | None) -> str:
    return "unknown date" if when is None else when.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _approval(text: str) -> tuple[str, str, bool]:
    """``approved_in`` as (``plan`` | ``change`` | ``""``, the id, whether the change was taken back)."""
    found = _APPROVAL.fullmatch(text.strip())
    return (found.group(1), found.group(2), found.group(3) is not None) if found else ("", "", False)


def _tag(line: str) -> str:
    found = _TAG.search(line.strip())
    return found.group(1) if found else ""


def _untagged(line: str) -> str:
    text = _TAG.sub("", line.strip())
    return text[2:] if text.startswith("- ") else text


def _item(briefs: tuple[BriefRecord, ...], when: datetime | None, kind: str, **effect: str) -> str:
    """``B<n>.<k>`` of the item of a held brief, made before ``when``, of this kind whose effect holds all of ``effect``; ``""`` when there is none."""
    if when is None:
        return ""
    for record in briefs:
        if record.at >= when:
            continue
        for item in record.items:
            if item.kind == kind and all(item.effect.get(k) == v for k, v in effect.items()):
                return f"{record.id}.{item.n}"
    return ""


def _approved(approval: tuple[str, str, bool], when: datetime | None, item: str) -> tuple[str, str]:
    """(label, plan id) of a creation or a retire that records its approval."""
    kind, plan_id, undone = approval
    if kind == "change" and undone:
        return BACK_LABEL.format(id=plan_id), plan_id
    if kind == "change":
        return CHANGE_LABEL.format(id=plan_id) + (f", item {item}" if item else ""), plan_id
    return PLAN_LABEL.format(date=_date(when)), plan_id


def _creation(approved_in: str, by: str, plan_heading: bool, when: datetime | None, item: str) -> tuple[str, str]:
    """(label, plan id) of an agent or a service made without the approval recorded: a lead's own, root's before Phase 2 (a plan heading), or root's outside a plan."""
    approval = _approval(approved_in)
    if approval[0]:
        return _approved(approval, when, item)
    if by != ROOT:
        return INSIDE_LABEL.format(lead=by), ""
    return (PLAN_LABEL.format(date=_date(when)), "") if plan_heading else (ROOT_LABEL, "")


def _agent(fact: AgentFact, briefs: tuple[BriefRecord, ...]) -> Change:
    item = _item(briefs, fact.created, "checker-add", owner=parent_of(fact.addr) or ROOT) if fact.verifier else ""
    label, plan_id = _creation(fact.approved_in, fact.hired_by, fact.plan_heading, fact.created, item)
    return Change(fact.created, "agent-created", fact.addr, f"agent {fact.addr} added ({_date(fact.created)})", label, fact.hired_by, plan_id)


def _retired(fact: RetiredFact, briefs: tuple[BriefRecord, ...]) -> Change:
    if not fact.recorded:
        return Change(fact.retired, "agent-retired", fact.addr, f"agent {fact.addr} retired {_date(fact.retired)}", "")
    label, plan_id = _creation(fact.approved_in, fact.by, False, fact.retired, _item(briefs, fact.retired, "retire", agent=fact.addr))
    return Change(fact.retired, "agent-retired", fact.addr, f"agent {fact.addr} retired ({_date(fact.retired)})", label, fact.by, plan_id)


def _service(fact: ServiceFact, briefs: tuple[BriefRecord, ...]) -> Change:
    name = f"{fact.owner}/{fact.name}"
    label, plan_id = _creation(fact.approved_in, fact.defined_by, False, fact.created, _item(briefs, fact.created, "service", service=name))
    return Change(fact.created, "service-defined", name, f"service {name} added ({_date(fact.created)})", label, fact.defined_by, plan_id)


def _service_retired(fact: ServiceRetired) -> Change:
    name = f"{fact.owner}/{fact.name}"
    label, plan_id = _creation(fact.approved_in, fact.by, False, fact.retired, "")
    return Change(fact.retired, "service-retired", name, f"service {name} retired ({_date(fact.retired)})", label, fact.by, plan_id)


def _limits_agree(pair: CharterPair, keys: list[KeyChange]) -> bool:
    """Whether the limit keys that changed hold the values the limits line of the added section names (design section 3, (b))."""
    line = next((_untagged(x) for x in reversed(pair.added_after) if _untagged(x).startswith(LIMITS)), "")
    found = _LIMITS_LINE.search(line)
    if not found:
        return False
    named = {"max_children": found.group(1), "can_hire": "true" if found.group(2) == "yes" else "false"}
    return all(k.new == named[k.key] for k in keys)


def _lower(change: KeyChange) -> bool:
    try:
        return change.key == "max_children" and int(change.new or "") < int(change.old or "")
    except ValueError:
        return False


def _covers(events: EventFacts, pair: CharterPair) -> bool:
    return events.covers_from is not None and events.covers_from <= (pair.older or pair.when)


def _wrote(events: EventFacts, pair: CharterPair, parent: str) -> bool:
    start = pair.older or _EPOCH
    return any(w.actor == parent and w.path == pair.path and start <= w.when <= pair.when + SAME_SECOND for w in events.writes)


def _what(pair: CharterPair) -> str:
    parts = (["body"] if pair.body_differs else []) + [k.key for k in pair.keys] + (["added section"] if pair.added_before != pair.added_after else [])
    return ", ".join(parts)


def _charter(pair: CharterPair, facts: ChangeFacts) -> Change | None:
    """The change one edit pair is, or None when nothing differs. The label tries the extension's own marks first, then who could have written."""
    before, after = {line_key(x): x for x in pair.added_before}, {line_key(x): x for x in pair.added_after}
    touched = [x for key, x in after.items() if key not in before] + [x for key, x in before.items() if key not in after]
    foreign = [x for x in touched if not _tag(x)]
    limit_keys = [k for k in pair.keys if k.key in ("can_hire", "max_children")]
    limits_agree = bool(limit_keys) and _limits_agree(pair, limit_keys)
    rest = [k for k in pair.keys if not (limits_agree and k in limit_keys)]
    differs = pair.body_differs or bool(rest) or bool(foreign)
    plan_id = next((_tag(x) for x in touched if _tag(x)), "")
    when, addr = pair.when, pair.addr
    if not (touched or rest or pair.body_differs or limits_agree):
        return None
    text = f"charter of {addr} changed: {_what(pair)} ({_date(when)})"
    if not differs:
        if not plan_id:  # the limits line was not among the lines that changed: take its tag
            plan_id = next((_tag(x) for x in pair.added_after if _tag(x) and _untagged(x).startswith(LIMITS)), "")
        item = next((n for x in touched if (n := _fix_item(facts.briefs, when, addr, line_key(_untagged(x))))), "")
        label = CHANGE_LABEL.format(id=plan_id) + (f", item {item}" if item else "")
        return Change(when, "charter", addr, text, label, "", plan_id)
    agent_only = not foreign and all(k.key == "role" or _lower(k) for k in rest)
    parent = parent_of(addr) if "/" in addr else ""  # root's MCP write of a charter is refused: a top-level charter has no writer among the tools
    if not parent or not agent_only:
        label, by = HAND_LABEL, ""
    elif not _covers(facts.events, pair):
        label, by = UNSURE_LABEL.format(parent=parent), parent
    elif _wrote(facts.events, pair, parent):
        label, by = PARENT_LABEL.format(parent=parent), parent
    else:
        label, by = HAND_LABEL, ""
    return Change(when, "charter", addr, text, label, by, "", True)


def _fix_item(briefs: tuple[BriefRecord, ...], when: datetime, agent: str, wanted: str) -> str:
    """``B<n>.<k>`` of the ``checker-fix`` item of a held brief, made before ``when``, that is for ``agent`` and whose line has the key ``wanted``."""
    for record in briefs:
        if record.at >= when:
            continue
        for item in record.items:
            if item.kind == "checker-fix" and item.effect.get("agent") == agent and line_key(item.effect.get("line", "")) == wanted:
                return f"{record.id}.{item.n}"
    return ""


def _depth(pair: CharterPair, facts: ChangeFacts) -> Change:
    old, new = pair.depth or ("", "")
    text = f"ORG.md max_depth {old} -> {new} ({_date(pair.when)})"
    found = _APPLIED.match(facts.subjects.get(pair.commit, ""))
    label = CHANGE_LABEL.format(id=found.group(1)) if found else HAND_LABEL
    return Change(pair.when, "depth", "ORG.md", text, label, "", found.group(1) if found else "")


def changes_of(facts: ChangeFacts, since: datetime | None) -> Changes:
    """The structural changes after ``since`` (all of them when None), oldest first, with the count of the unprompted charter edits among them. A change with
    no date is left out when ``since`` is given."""
    found = [
        *(_agent(a, facts.briefs) for a in facts.agents), *(_retired(r, facts.briefs) for r in facts.retired),
        *(_service(s, facts.briefs) for s in facts.services), *(_service_retired(s) for s in facts.retired_services),
    ]
    for pair in facts.versions.pairs:
        if pair.kind != "edit" or pair.path.startswith(".retired/"):
            continue  # a deletion, a re-created address and a retired tree are no edit
        change = _depth(pair, facts) if pair.depth is not None else _charter(pair, facts)
        if change is not None:
            found.append(change)
    kept = sorted((c for c in found if since is None or (c.when is not None and c.when > since)), key=lambda c: (c.when or _EPOCH, c.subject, c.kind))
    known = facts.versions.known
    return Changes(tuple(kept), known, sum(c.unprompted for c in kept) if known else None, facts.versions.truncated and known)
