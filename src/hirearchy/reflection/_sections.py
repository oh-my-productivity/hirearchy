"""The sections of an owner's run prompt that come from its services: the list, the playbooks, and what to reflect on first."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import RENDER_BODY_CHARS, ROOT, Message, clip_line, parent, verdict_tier
from ..mail import MailboxReader, TaskQuery
from ..services import Contract, ServiceCatalog, confirmed_amendments, playbook_word_cap
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


class QuotedPlaybookSection(PlaybookSection):
    """The playbook of a service with an open request, quoted; or what to do while there is none."""

    def __init__(self, catalog: ServiceCatalog, paths: ServicePaths) -> None:
        self._catalog = catalog
        self._paths = paths

    def section(self, addr: str, contract: Contract, *, reflecting: bool = False) -> str:
        c = contract
        pb = self._catalog.read_playbook(addr, c.name)
        who = "locked by your parent" if c.locked else "yours to improve"
        head = f"# Playbook: {c.name} (v{pb.version}, {who})"
        if not pb.version:
            if c.locked:
                return f"{head}\nNo playbook yet, and the contract is locked: plan as usual."
            if reflecting:
                return (
                    f"{head}\nNo playbook yet: write v1 now from how the team works (Reflect before you start shows the evidence; rules from "
                    "lessons or relayed verdicts are not steps), then follow it (the first version needs no evidence: evidence=[])."
                )
            return (
                f"{head}\nNo playbook yet: plan as usual; when you report this request, write v1 with revise_playbook: the steps your team "
                "followed, nothing more (the first version needs no evidence: evidence=[])."
            )
        return f"{head}\n{_quoted(pb.body, self._paths.rel(pb.path))}"


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


class EvidenceReflectSection(ReflectSection):
    """The steps the owner takes before the work: read the evidence, revise the playbook if it would prevent the problem (unless it is locked)."""

    def __init__(self, catalog: ServiceCatalog, config: ConfigSource, paths: ServicePaths, history: CaseHistory) -> None:
        self._catalog = catalog
        self._config = config
        self._paths = paths
        self._history = history

    def _eligible(self, addr: str, name: str) -> str:
        """What rule (c) admits now, for step 3: the current amendments the client confirmed, and those it has not (``none yet`` when no one is)."""
        criteria = self._catalog.criteria(addr, name)
        current = [c for c in criteria if c.current]
        confirmed = confirmed_criteria(self._history.cases(addr, name), criteria)
        admitted = [c.id for c in confirmed_amendments(current, confirmed)]
        waiting = [c.id for c in current if c.amended and not c.user and c.id not in confirmed]
        own = [c.id for c in current if c.amended and c.user]
        text = "none yet"
        if admitted:
            text = f"now {', '.join(admitted)}: a revision citing {'it' if len(admitted) == 1 else 'one of them'} may add its words"
        if waiting:
            text += f"; {', '.join(waiting)} {'is' if len(waiting) == 1 else 'are'} not confirmed yet"
        if own:
            text += f"; {', '.join(own)} {'is' if len(own) == 1 else 'are'} user-initiated (rule (c) never admits {'it' if len(own) == 1 else 'them'})"
        return text

    def section(self, addr: str, contract: Contract, digest: str, *, rejected: str = "", new_request: bool = True) -> str:
        c = contract
        pb = self._catalog.read_playbook(addr, c.name)
        human_client = parent(addr) == ROOT
        since = f"Evidence since v{pb.version}:" if pb.version else "Evidence so far (there is no playbook yet):"
        what = "rework" if rejected and not new_request else "request"
        first = (
            f"Look for what repeats, and for anything the client rejected{' (the regression list)' if human_client else ''}. "
            "A rejection or a failure is enough to look into on its own; a single slow case is not."
        )
        bar = "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. "
        if not human_client:
            raise_bar = bar + "If the client's feedback is a lasting requirement, also tell your parent (`send`) so it can add it to the contract."
        elif c.locked:
            raise_bar = bar + "Your parent asks the client whether a rejection is a lasting requirement; do not send it yourself."
        else:
            raise_bar = (
                bar + "Your parent asks the client whether a rejection is a lasting requirement: send nothing about it yourself beyond a "
                "refused revision's question (step 3)."
            )
        rejecter = {
            "human": "The client rejected a delivery",
            "relayed": "A relayed rejection arrived (the assistant's own reading, not the client's words)",
            "agent": "Your client, an agent, rejected a delivery (its verdict is a hypothesis)",
        }.get(rejected, "")
        if c.locked:
            intro = (
                "Your playbook is how your team delivers this service. The contract is locked by your parent, so you may "
                f"not revise the playbook. {since}"
            )
            steps = [
                first,
                "When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: follow the feedback.",
                f"You cannot change the playbook, but apply what the evidence shows when you plan this {what}. " + raise_bar,
                f"Then handle the {what} following the playbook.",
            ]
            lead = (
                f"{rejecter}. The contract is locked, so you cannot revise the playbook: apply what the feedback shows, then handle the {what}."
                if rejected else "Before working on the new request:"
            )
        else:
            intro = f"Your playbook is how your team delivers this service; you own it and improve it. {since}"
            if human_client:
                revise = (
                    "If a change to how the team works would prevent it, call `revise_playbook(service, content, reason, evidence)` with "
                    f"the whole new playbook (at most {playbook_word_cap(self._config.config())} words): concrete steps (who does what, in "
                    "which order, which check), not slogans. Name the cases in the reason, and list in `evidence` what it rests on: "
                    "regression assertions (R<k>), criteria (C<k>), verdict or case ids. It is admitted only when the same criterion or "
                    "assertion failed in 2 different cases the client rejected (then every line it adds or changes carries that id, "
                    'e.g. "[C6]"), or when it cites a criterion your parent added to the contract by an amendment the client confirmed '
                    f"({self._eligible(addr, c.name)}): then it may add only that criterion's own words, one line each, "
                    '"- C<k>: <its text>". A link note id counts as its criterion. Your lessons and relayed verdicts (the '
                    "assistant's own reading) are not evidence. If it is refused, nothing is written: send your parent the refusal's question "
                    "once and go on with the playbook as it is. "
                    f"The new version applies to this {what}."
                )
            else:
                revise = (
                    "Your client is an agent, so nothing in this service's history can admit a playbook revision (only the first version, "
                    f"or restoring a version your parent wrote): apply the evidence when you plan this {what}, and if you think the "
                    "playbook must change, send your parent (`send`) what you would change and why."
                )
            steps = [
                first,
                "When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: apply the "
                f"feedback in this {what}, and change the playbook only as step 3 says (say so in the reason).",
                revise,
                raise_bar,
            ]
            if pb.version >= 2:
                steps.append(
                    "If the current version did worse than an earlier one, restore that one "
                    f"(read {self._paths.service_dir(addr, c.name)}/history/PLAYBOOK.v<k>.md): revise_playbook with its text unchanged; "
                    "a version your parent wrote needs evidence=[], any other needs evidence like a revision."
                )
            steps.append(f"If nothing needs to change, do not revise. Then handle the {what} following the playbook.")
            if rejected == "human":
                lead = (
                    f"{rejecter}: check the delivery against its words, the regression list and the contract before you plan the {what}. "
                    "A rule without the client's evidence (step 3) is a reason to look, not to change how the team works: your parent asks the "
                    "client whether it is a lasting requirement, and the answer reaches you as a contract change or a criterion link. Revise "
                    f"the playbook when step 3 admits it, then handle the {what}."
                )
            elif rejected:
                lead = (
                    f"{rejecter}: apply what it asks in this {what} where the contract allows it; it is not the client's evidence, so it "
                    f"cannot change the playbook (step 3). Then handle the {what}."
                )
            else:
                lead = "Before working on the new request:"
        numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        return f"# Reflect before you start: {c.name}\n{intro}\n{digest}\n{lead}\n{numbered}"


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
    """The services an agent owns, the playbook of each it is working on, and the reflection a new request or a rejection calls for."""

    def __init__(
        self, catalog: ServiceCatalog, listing: ServicesListing, digest: ReflectionDigest, tasks: TaskQuery, rejections: RejectedServices,
        playbooks: PlaybookSection, reflections: ReflectSection, regressions: RegressionSection,
    ) -> None:
        self._catalog = catalog
        self._listing = listing
        self._digest = digest
        self._tasks = tasks
        self._rejections = rejections
        self._playbooks = playbooks
        self._reflections = reflections
        self._regressions = regressions

    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        owned = self._catalog.owned_services(addr)
        if not owned:
            return ""
        sections = [self._listing.listing(addr, owned)]
        working = {t.service for t in self._tasks.open_tasks(addr) if t.service}
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
                    addr, c, digests[c.name], rejected=rejected.get(c.name, ""), new_request=c.name in new,
                ))
        return "".join(f"\n{s}\n" for s in sections if s)
