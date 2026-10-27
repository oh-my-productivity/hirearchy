"""The sections of an owner's run prompt that come from its services: the list, the playbooks, and what to reflect on first."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from functools import partial

from ..kernel import RENDER_BODY_CHARS, ROOT, Message, OrgError, clip_line, latest_results, parent, verdict_tier
from ..mail import MailboxReader, still_open
from ..services import (
    Contract, ItemWatch, Playbook, ServiceCatalog, ServiceEvidence, confirmed_amendments, content_words, migrate_body, playbook_word_cap, render_items,
    watch_restores,
)
from ._ports import ConfigSource, PlaybookSection, RegressionSection, RejectedServices, ReflectSection, ServicePaths, ServicesListing
from ._reports import marked
from .api import Assertion, CaseHistory, ReflectionDigest, ServicePromptSections, confirmed_criteria, regressions

REGRESSION_LINES = 12  # the newest assertions shown in the owner's prompt
CLIP_REGRESSION = 300  # characters of the client's words shown for one of them


def _quoted(text: str, where: str) -> str:
    """A playbook shown in the prompt: quoted, so its headings do not mix with the prompt's, cut like messages."""
    if len(text) > RENDER_BODY_CHARS:
        text = (
            text[:RENDER_BODY_CHARS].rstrip()
            + f"\n\n[... playbook cut: {len(text) - RENDER_BODY_CHARS} more characters. Read the rest with read(path=\"{where}\").]"
        )
    return "\n".join(f"> {line}".rstrip() for line in text.splitlines())


class MailRejectedServices(RejectedServices):
    """A rejection is a ``feedback: reject`` note in the batch, a reply to a request the owner received; its tier is the note's (human > relayed > agent)."""

    STRENGTH = ("human", "relayed", "agent")

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def among(self, addr: str, batch: Sequence[Message]) -> dict[str, str]:
        notes = [m for m in batch if m.type == "note" and m.feedback == "reject" and m.to == addr and m.reply_to]
        if not notes:
            return {}
        service_of = {m.id: m.service for m in self._mail.received(addr) if m.type == "task" and m.service}
        tiers: dict[str, str] = {}
        for n in notes:
            svc, tier = service_of.get(n.reply_to or ""), verdict_tier(n)
            if svc and (svc not in tiers or self.STRENGTH.index(tier) < self.STRENGTH.index(tiers[svc])):
                tiers[svc] = tier
        return tiers


NO_PLAYBOOK_LOCKED = "No playbook yet, and the contract is locked: plan as usual."
NO_PLAYBOOK_REFLECTING = (  # the prompt carries a "Reflect before you start" section (14.1)
    'No playbook yet: write v1 now from how the team works with revise_playbook(op="first", text=...) (Reflect before you start shows the '
    "evidence; rules from lessons or relayed verdicts are not steps), then follow it. The first version needs no evidence and is allowed only until "
    "the client's first verdict or rework; after that, add items one at a time (op=\"add\") with the client's evidence."
)
NO_PLAYBOOK_PLAIN = (
    "No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook(op=\"first\", text=...): the steps your team "
    "followed, nothing more (no evidence needed, and only until the client's first verdict or rework; after that, op=\"add\" with the client's evidence)."
)
PLAYBOOK_HEAD = "# Playbook: {service} (v{n}, {who})"
PLAYBOOK_ITEMS = "yours to improve one item at a time; {words} of {cap} words"
LEGACY_IDS = "Items get these ids when you first change one."  # a free-text playbook, shown as it would migrate
STATES = "Item states: "
STATES_KEPT = "Item states: all items kept."
STATES_OTHERS = " All other items: kept."
NO_ITEMS = 'Playbook v{n} has no items: add one (op="add").'
NOT_ITEMS = "Playbook v{n} is not in item form ({reason}): your next change first turns its text into new items (no change of words)."
STATES_UNREAD = "Item states could not be read ({error}); follow the contract where an item differs from it."
STATE_NEW = "{id} {kind}, new since v{n} ({parts})"
STATE_NEW_WATCHED = "watched: a related client rejection warns it, a second retires it"
STATE_NEW_CARRIED = "carried from {old}"
STATE_NEW_WAITING = "waiting for the client's verdict on {n} {cases}"
STATE_NEW_PENDING = "waiting for the user's answer to {rejections}"
STATE_WARNING = "{id} {kind}, warning: rejection {rejection} (case {case}) is related; one more retires it{restores}"
STATE_WARNING_MANY = "{id} {kind}, warning: rejections {rejections} are related; one more retires it"
STATE_WARNING_CARRIED = "{id} {kind}, warning (carried from {old}): rejection{s} {rejections} {verb} related; one more retires it"
STATE_WARNING_RESTORES = " and restores the text of v{k}"
STATE_RESTORED = "{id} {kind}, restored (the watch put back the text of v{k})"
STATE_DUE = "{id}: retire due ({rejections} are related): the runtime retires it at {when}; follow the contract"
DUE_UNLOCKED = "the next change"
DUE_LOCKED = "the client's next answer"  # the owner's ops are refused first on a locked contract, so the settler runs at the client's answer (B6)
CASE_UNKNOWN = "unknown"


class QuotedPlaybookSection(PlaybookSection):
    """The playbook of a service with an open request, quoted, with the states of its watched items; or what to do while there is none."""

    def __init__(self, catalog: ServiceCatalog, config: ConfigSource, paths: ServicePaths, evidence: ServiceEvidence) -> None:
        self._catalog = catalog
        self._config = config
        self._paths = paths
        self._evidence = evidence

    def section(self, addr: str, contract: Contract, *, reflecting: bool = False) -> str:
        c = contract
        pb = self._catalog.read_playbook(addr, c.name)
        who = "locked by your parent" if c.locked else "yours to improve"
        if not pb.version:
            head = PLAYBOOK_HEAD.format(service=c.name, n=0, who=who)
            if c.locked:
                return f"{head}\n{NO_PLAYBOOK_LOCKED}"
            return f"{head}\n{NO_PLAYBOOK_REFLECTING if reflecting else NO_PLAYBOOK_PLAIN}"
        legacy = pb.items is None and not pb.parse_error
        migrated = migrate_body(pb.body) if legacy else None
        body = render_items(migrated.items, migrated.sections) if migrated is not None else pb.body
        if not c.locked:
            words = len(pb.body.split()) if pb.items is None else content_words(pb.items, [s.heading for s in pb.sections if s.heading])
            who = PLAYBOOK_ITEMS.format(words=words, cap=playbook_word_cap(self._config.config()))
        lines = [PLAYBOOK_HEAD.format(service=c.name, n=pb.version, who=who)]
        if body.strip():
            lines.append(_quoted(body, self._paths.rel(pb.path)))
        if legacy:
            lines += [LEGACY_IDS, STATES_KEPT]
        elif pb.parse_error:
            lines.append(NOT_ITEMS.format(n=pb.version, reason=pb.parse_error))
        elif not pb.items:
            lines.append(NO_ITEMS.format(n=pb.version))
        else:
            lines.append(self._states(addr, c, pb))
        return "\n".join(lines)

    def _states(self, addr: str, contract: Contract, pb: Playbook) -> str:
        """The states line (14.1): ids, states, versions and rejection ids only, never a count of clean cases. One ``evidence.watch`` read."""
        try:
            watch = {w.id: w for w in self._evidence.watch(addr, contract.name)}
            live = [i.id for i in pb.items or ()]
            listed = [watch[i] for i in live if i in watch and (watch[i].state in ("new", "warning", "restored") or watch[i].retire_due)]
            warned = [w for w in listed if w.state == "warning" and not w.retire_due and not w.carried and len(w.related) == 1]
            cases = self._cases(addr, contract.name) if warned else {}
            versions = self._catalog.playbook_versions(addr, contract.name) if warned else []
            entries = [self._entry(w, contract.locked, cases, versions) for w in listed]
        except (OrgError, OSError) as error:
            return STATES_UNREAD.format(error=error)
        if not entries:
            return STATES_KEPT
        return STATES + "; ".join(entries) + "." + (STATES_OTHERS if len(listed) < len(live) else "")

    def _cases(self, addr: str, name: str) -> dict[str, str]:
        """The case of every human rejection of the service, by its ``R<k>``."""
        return {r.assertion: r.case or r.task or CASE_UNKNOWN for r in self._evidence.amendment_basis(addr, name).rejections}

    @staticmethod
    def _entry(w: ItemWatch, locked: bool, cases: Mapping[str, str], versions: Sequence[Playbook]) -> str:
        if w.retire_due:
            return STATE_DUE.format(id=w.id, rejections=", ".join(w.related), when=DUE_LOCKED if locked else DUE_UNLOCKED)
        if w.state == "restored":
            return STATE_RESTORED.format(id=w.id, kind=w.kind, k=w.restores)
        if w.state == "new":
            parts = [STATE_NEW_CARRIED.format(old=w.carried)] if w.carried else []
            held = [
                *([STATE_NEW_WAITING.format(n=w.waiting, cases="case" if w.waiting == 1 else "cases")] if w.waiting else []),
                *([STATE_NEW_PENDING.format(rejections=", ".join(w.pending))] if w.pending else []),
            ]
            parts += held or [STATE_NEW_WATCHED]
            return STATE_NEW.format(id=w.id, kind=w.kind, n=w.text_version, parts="; ".join(parts))
        if w.carried:
            many = len(w.related) != 1
            return STATE_WARNING_CARRIED.format(
                id=w.id, kind=w.kind, old=w.carried, s="s" if many else "", rejections=", ".join(w.related), verb="are" if many else "is",
            )
        if len(w.related) != 1:
            return STATE_WARNING_MANY.format(id=w.id, kind=w.kind, rejections=", ".join(w.related))
        k = watch_restores(versions, w)
        return STATE_WARNING.format(
            id=w.id, kind=w.kind, rejection=w.related[0], case=cases.get(w.related[0], CASE_UNKNOWN),
            restores=STATE_WARNING_RESTORES.format(k=k) if k else "",
        )


class RegressionListSection(RegressionSection):
    """The client's rejections of a service, verbatim: the lines a delivery is checked against (the newest ones; ``services`` lists them all)."""

    def __init__(self, catalog: ServiceCatalog, history: CaseHistory) -> None:
        self._catalog = catalog
        self._history = history

    @staticmethod
    def _line(a: Assertion, current: set[str]) -> str:
        if a.link == "confirmed":
            about = f", about {marked(a.about, current)}"
        elif a.link == "none":
            about = ", no lasting rule (the client said so): do not check it"
        elif a.link == "unconfirmed":
            about = (
                ", possibly a one-off (not confirmed by the client)" if a.verdict.links == ("none",)
                else f", about {marked(a.verdict.links, current)} (not confirmed by the client)"
            )
        else:
            about = ""
        return f'- {a.id}, case {a.case}, verdict {a.verdict.message.id}{about}: "{clip_line(a.verdict.note, CLIP_REGRESSION)}"'

    def section(self, addr: str, contract: Contract) -> str:
        found = regressions(self._history.cases(addr, contract.name))
        if not found:
            return ""
        current = {x.id for x in self._catalog.criteria(addr, contract.name) if x.current}
        shown = found[-REGRESSION_LINES:]
        older = [f"- {len(found) - len(shown)} older line(s) not shown: `services` lists them all."] if len(found) > len(shown) else []
        return "\n".join([
            f"# Regression list: {contract.name} (the client's rejections, verbatim)",
            "Each line is something the client rejected. Check every delivery of this service against each line, except the lines marked "
            '"no lasting rule" (the client said it was a one-off: do not check them), and copy this list verbatim into every review or check '
            "task you delegate for it. A line is not a criterion: it becomes one when your parent adds it to the contract, or ends as "
            '"no lasting rule".',
            *older,
            *(self._line(a, current) for a in shown),
        ])


REFLECT_WORDS = 600  # the Reflect section in all, counted with ``str.split`` (design 12)
REFLECT_FIXED_WORDS = 400  # its fixed text (everything but the digest), in every variant
DIGEST_MIN_WORDS = 200  # what the digest may always have
SHOWN_IDS = 5  # ids one list of the fixed text names, then "+{n} more"
REFLECT_HEAD = "# Reflect before you start: {service}"
REFLECT_INTRO = "Your playbook is how your team delivers this service; you own it and change it one item at a time. {since}"
REFLECT_INTRO_LOCKED = (
    "Your playbook is how your team delivers this service. The contract is locked by your parent, so you may not change the playbook. {since}"
)
SINCE = "Evidence since v{n}:"
SINCE_NONE = "Evidence so far (there is no playbook yet):"
REFLECT_WARNING = "Warning: {items} {verb} one related rejection; a second retires it."
REFLECT_STEP_1 = (
    "Look for what repeats, and for anything the client rejected{regression}. A rejection or a failure is enough to look into on its own; a single "
    "slow case is not."
)
REGRESSION_LIST = " (the regression list)"
REFLECT_STEP_2 = "When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: apply the feedback in this {what}."
REFLECT_STEP_2_LOCKED = "When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: follow the feedback."
REFLECT_STEP_3 = (  # Q4 (B10): the last-but-two sentence is root's acknowledgement path, built on the recommended answer
    "If a change to how the team works would prevent it, change one item with `revise_playbook` (its description gives the ops). A rule, or a step "
    "that changes a check, an output or how a criterion is handled, needs evidence in `evidence`: the same criterion or assertion failed in 2 "
    "different cases the client rejected, or the item is the own words of a criterion the client confirmed ({eligible}). Lessons and relayed "
    "verdicts are not evidence. An admitted item is watched: a related client rejection warns it, a second retires it. Retiring or weakening an "
    "item that covers a criterion needs your parent's acknowledgement. If a change is refused, nothing is written: send your parent its question "
    "once and go on."
)
REFLECT_STEP_3_AGENT = (
    "Your client is an agent, so nothing can admit a change (only the first version): apply the evidence when you plan this {what}, and if you "
    "think the playbook must change, send your parent (`send`) what you would change and why."
)
REFLECT_STEP_3_LOCKED = "You cannot change the playbook, but apply what the evidence shows when you plan this {what}. {bar}"
BAR = "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. "
BAR_AGENT = "If the client's feedback is a lasting requirement, also tell your parent (`send`) so it can add it to the contract."
BAR_LOCKED = "Your parent asks the client whether a rejection is a lasting requirement; do not send it yourself."
BAR_HUMAN = (
    "Your parent asks the client whether a rejection is a lasting requirement: send nothing about it yourself beyond a refused change's question "
    "(step 3)."
)
REFLECT_STEP_5 = "If nothing needs to change, change nothing. Then handle the {what} following the playbook."
REFLECT_STEP_5_LOCKED = "Then handle the {what} following the playbook."
LEAD_NEW = "Before working on the new request:"
LEAD_HUMAN = (
    "The client rejected a delivery: check it against their words, the regression list and the contract before you plan the {what}. Without the "
    "client's evidence (step 3) a rejection is a reason to look, not to change an item: your parent asks the client whether it is a lasting "
    "requirement, and the answer reaches you as a contract change or a criterion link."
)
LEAD_RELAYED = (
    "A relayed rejection arrived (the assistant's own reading, not the client's words): apply what it asks in this {what} where the contract allows "
    "it; it is not the client's evidence, so it cannot change the playbook (step 3). Then handle the {what}."
)
LEAD_AGENT = (
    "Your client, an agent, rejected a delivery (its verdict is a hypothesis): apply what it asks in this {what} where the contract allows it; it is "
    "not the client's evidence, so it cannot change the playbook (step 3). Then handle the {what}."
)
LEAD_LOCKED = "{rejecter}. The contract is locked, so you cannot change the playbook: apply what the feedback shows, then handle the {what}."
REJECTER = {
    "human": "The client rejected a delivery",
    "relayed": "A relayed rejection arrived (the assistant's own reading, not the client's words)",
    "agent": "Your client, an agent, rejected a delivery (its verdict is a hypothesis)",
}
ELIGIBLE_NONE = "none yet"
ELIGIBLE_NOW = "now {ids} (an item may be the own words of {one})"
ELIGIBLE_WAITING = "{ids} not confirmed yet"
ELIGIBLE_OWN = "{ids} user-initiated (never rule (c))"
MORE_IDS = "+{n} more"


def _ids(ids: Sequence[str]) -> str:
    """At most ``SHOWN_IDS`` ids, then ``+{n} more``."""
    shown = list(ids[:SHOWN_IDS])
    return ", ".join([*shown, *([MORE_IDS.format(n=len(ids) - SHOWN_IDS)] if len(ids) > SHOWN_IDS else [])])


def eligible_clause(admitted: Sequence[str], waiting: Sequence[str], own: Sequence[str]) -> str:
    """What rule (c) admits now, for step 3 (pure): the confirmed amendments, the unconfirmed ones and the user's own, each list at most 5 ids long;
    ``none yet`` when there is no one."""
    parts = []
    if admitted:
        parts.append(ELIGIBLE_NOW.format(ids=_ids(admitted), one="it" if len(admitted) == 1 else "one"))
    if waiting:
        parts.append(ELIGIBLE_WAITING.format(ids=_ids(waiting)))
    if own:
        parts.append(ELIGIBLE_OWN.format(ids=_ids(own)))
    if not parts:
        return ELIGIBLE_NONE
    return "; ".join(parts) if admitted else "; ".join([ELIGIBLE_NONE, *parts])


def warning_line(warned: Sequence[ItemWatch]) -> str:
    """The warning line of the Reflect section (pure): the items in warning with their one related rejection, at most 5, then ``+{n} more``; ``""``
    when none is."""
    if not warned:
        return ""
    shown = [f"{w.id} ({w.related[0]})" for w in warned[:SHOWN_IDS]]
    if len(warned) > SHOWN_IDS:
        shown.append(MORE_IDS.format(n=len(warned) - SHOWN_IDS))
    return REFLECT_WARNING.format(items=", ".join(shown), verb="has" if len(warned) == 1 else "each have")


class EvidenceReflectSection(ReflectSection):
    """The steps the owner takes before the work: read the evidence, change one playbook item if it would prevent the problem (unless it is locked), in
    at most ``REFLECT_WORDS`` words."""

    def __init__(self, catalog: ServiceCatalog, config: ConfigSource, paths: ServicePaths, history: CaseHistory, evidence: ServiceEvidence) -> None:
        self._catalog = catalog
        self._config = config
        self._paths = paths
        self._history = history
        self._evidence = evidence

    def _eligible(self, addr: str, name: str) -> str:
        """What rule (c) admits now, for step 3."""
        criteria = self._catalog.criteria(addr, name)
        current = [c for c in criteria if c.current]
        confirmed = confirmed_criteria(self._history.cases(addr, name), criteria)
        admitted = [c.id for c in confirmed_amendments(current, confirmed)]
        waiting = [c.id for c in current if c.amended and not c.user and c.id not in confirmed]
        own = [c.id for c in current if c.amended and c.user]
        return eligible_clause(admitted, waiting, own)

    def _warned(self, addr: str, name: str) -> list[ItemWatch]:
        """The live items with exactly one related rejection (``[]`` when the watch cannot be read: the playbook section says so)."""
        try:
            watch = self._evidence.watch(addr, name)
        except (OrgError, OSError):
            return []
        return [w for w in watch if w.state == "warning" and not w.retire_due and len(w.related) == 1]

    def section(self, addr: str, contract: Contract, digest: Callable[[int], str], *, rejected: str = "", new_request: bool = True) -> str:
        c = contract
        pb = self._catalog.read_playbook(addr, c.name)
        human_client = parent(addr) == ROOT
        since = SINCE.format(n=pb.version) if pb.version else SINCE_NONE
        what = "rework" if rejected and not new_request else "request"
        first = REFLECT_STEP_1.format(regression=REGRESSION_LIST if human_client else "")
        if not human_client:
            raise_bar = BAR + BAR_AGENT
        elif c.locked:
            raise_bar = BAR + BAR_LOCKED
        else:
            raise_bar = BAR + BAR_HUMAN
        if c.locked:
            intro = REFLECT_INTRO_LOCKED.format(since=since)
            steps = [
                first, REFLECT_STEP_2_LOCKED, REFLECT_STEP_3_LOCKED.format(what=what, bar=raise_bar), REFLECT_STEP_5_LOCKED.format(what=what),
            ]
            lead = LEAD_LOCKED.format(rejecter=REJECTER[rejected], what=what) if rejected else LEAD_NEW
        else:
            intro = REFLECT_INTRO.format(since=since)
            step_3 = REFLECT_STEP_3.format(eligible=self._eligible(addr, c.name)) if human_client else REFLECT_STEP_3_AGENT.format(what=what)
            steps = [first, REFLECT_STEP_2.format(what=what), step_3, raise_bar, REFLECT_STEP_5.format(what=what)]
            lead = {"human": LEAD_HUMAN, "relayed": LEAD_RELAYED, "agent": LEAD_AGENT}.get(rejected, LEAD_NEW).format(what=what)
        numbered = "\n".join(f"{i}. {x}" for i, x in enumerate(steps, 1))
        warning = warning_line(self._warned(addr, c.name))
        fixed = "\n".join([REFLECT_HEAD.format(service=c.name), intro, *([warning] if warning else []), lead, numbered])
        words = max(REFLECT_WORDS - len(fixed.split()), DIGEST_MIN_WORDS)
        return "\n".join([REFLECT_HEAD.format(service=c.name), intro, digest(words), *([warning] if warning else []), lead, numbered])


class OwnedServicesListing(ServicesListing):
    """The services an agent owns, one line each, under the reminder of who owns the contract and who the playbook."""

    def __init__(self, catalog: ServiceCatalog, history: CaseHistory, paths: ServicePaths) -> None:
        self._catalog = catalog
        self._history = history
        self._paths = paths

    def listing(self, addr: str, owned: Sequence[Contract]) -> str:
        lines = []
        for c in owned:
            pb = self._catalog.read_playbook(addr, c.name)
            lines.append(
                f"- {c.name}: contract v{c.version}{' (locked)' if c.locked else ''}, "
                f"{'playbook v' + str(pb.version) if pb.version else 'no playbook yet'}, {len(self._history.cases(addr, c.name))} request(s) so far; "
                f"contract: {self._paths.rel(c.path)}; playbook: {self._paths.playbook_file(addr, c.name)}"
            )
        return "# Your services\nThe contract (SERVICE.md) is your parent's; the playbook (PLAYBOOK.md) is yours.\n" + "\n".join(lines)


class OwnerPromptSections(ServicePromptSections):
    """The services an agent owns, the playbook of each it still owes a report on (``mail.still_open``), and the reflection a new request or a rejection
    calls for."""

    def __init__(
        self, catalog: ServiceCatalog, listing: ServicesListing, digest: ReflectionDigest, mail: MailboxReader, rejections: RejectedServices,
        playbooks: PlaybookSection, reflections: ReflectSection, regressions: RegressionSection,
    ) -> None:
        self._catalog = catalog
        self._listing = listing
        self._digest = digest
        self._mail = mail
        self._rejections = rejections
        self._playbooks = playbooks
        self._reflections = reflections
        self._regressions = regressions

    def _capped(self, addr: str, name: str, words: int) -> str:
        """The digest of a service within ``words`` words (the section that asks has a digest: it was found to have evidence)."""
        return self._digest.reflection_digest(addr, name, words=words) or ""

    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        owned = self._catalog.owned_services(addr)
        if not owned:
            return ""
        sections = [self._listing.listing(addr, owned)]
        received = self._mail.received(addr)
        latest = latest_results(self._mail.sent(addr))
        working = {t.service for t in received if t.type == "task" and t.service and still_open(t, latest.get(t.id), received)}  # D-E7-2 F-E7-8
        new = {m.service for m in batch if m.type == "task" and m.service and not m.revises and m.to == addr}
        rejected = self._rejections.among(addr, batch)
        digests = {
            c.name: d for c in owned if c.name in new | rejected.keys() and (d := self._digest.reflection_digest(addr, c.name)) is not None
        }
        for c in owned:
            if c.name in working:
                sections += [self._playbooks.section(addr, c, reflecting=c.name in digests), self._regressions.section(addr, c)]
        for c in owned:
            if c.name in digests:
                if c.name not in working:
                    sections.append(self._regressions.section(addr, c))
                sections.append(self._reflections.section(
                    addr, c, partial(self._capped, addr, c.name), rejected=rejected.get(c.name, ""), new_request=c.name in new,
                ))
        return "".join(f"\n{s}\n" for s in sections if s)
