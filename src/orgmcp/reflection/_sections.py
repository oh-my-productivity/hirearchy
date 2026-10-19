"""The sections of an owner's run prompt that come from its services: the list, the playbooks, and what to reflect on first."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import RENDER_BODY_CHARS, Message
from ..mail import MailboxReader, TaskQuery
from ..services import Contract, ServiceCatalog, playbook_word_cap
from ._ports import ConfigSource, PlaybookSection, RejectedServices, ReflectSection, ServicePaths, ServicesListing
from .api import CaseHistory, ReflectionDigest, ServicePromptSections


def _quoted(text: str, where: str) -> str:
    """A playbook shown in the prompt: quoted, so its headings do not mix with the prompt's, cut like messages."""
    if len(text) > RENDER_BODY_CHARS:
        text = (
            text[:RENDER_BODY_CHARS].rstrip()
            + f"\n\n[... playbook cut: {len(text) - RENDER_BODY_CHARS} more characters. Read the rest with read(path=\"{where}\").]"
        )
    return "\n".join(f"> {line}".rstrip() for line in text.splitlines())


class MailRejectedServices(RejectedServices):
    """A rejection is a ``feedback: reject`` note in the batch, a reply to a request the owner received."""

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def among(self, addr: str, batch: Sequence[Message]) -> set[str]:
        notes = [m for m in batch if m.type == "note" and m.feedback == "reject" and m.to == addr and m.reply_to]
        if not notes:
            return set()
        service_of = {m.id: m.service for m in self._mail.received(addr) if m.type == "task" and m.service}
        return {svc for n in notes if (svc := service_of.get(n.reply_to or ""))}


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
                    f"{head}\nNo playbook yet: write v1 now from the evidence below (Reflect before you start), then "
                    "follow it."
                )
            return (
                f"{head}\nNo playbook yet: plan as usual; when you report this request, write v1 with revise_playbook "
                "from how it went."
            )
        return f"{head}\n{_quoted(pb.body, self._paths.rel(pb.path))}"


class EvidenceReflectSection(ReflectSection):
    """The steps the owner takes before the work: read the evidence, revise the playbook if it would prevent the problem (unless it is locked)."""

    def __init__(self, catalog: ServiceCatalog, config: ConfigSource, paths: ServicePaths) -> None:
        self._catalog = catalog
        self._config = config
        self._paths = paths

    def section(self, addr: str, contract: Contract, digest: str, *, rejected: bool = False, new_request: bool = True) -> str:
        c = contract
        pb = self._catalog.read_playbook(addr, c.name)
        cap = playbook_word_cap(self._config.config())
        since = f"Evidence since v{pb.version}:" if pb.version else "Evidence so far (there is no playbook yet):"
        first = (
            "Look for what repeats, and for anything the client rejected. A rejection or a failure is enough on its own; "
            "a single slow case is not."
        )
        client_wins = (
            "When a lesson of yours conflicts with the client's feedback, the client is right: fix the playbook to match "
            "the feedback (and say so in the reason)."
        )
        raise_bar = (
            "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel "
            "with every request. If the client's feedback is a lasting requirement, also tell your parent (`send`) so it "
            "can add it to the contract."
        )
        what = "rework" if rejected and not new_request else "request"
        if c.locked:
            intro = (
                "Your playbook is how your team delivers this service. The contract is locked by your parent, so you may "
                f"not revise the playbook. {since}"
            )
            steps = [
                first,
                "When a lesson of yours conflicts with the client's feedback, the client is right: follow the feedback.",
                f"You cannot change the playbook, but apply what the evidence shows when you plan this {what}. " + raise_bar,
                f"Then handle the {what} following the playbook.",
            ]
            lead = (
                "The client rejected a delivery. The contract is locked, so you cannot revise the playbook: apply what the "
                f"feedback shows, then handle the {what}."
                if rejected else "Before working on the new request:"
            )
        else:
            intro = f"Your playbook is how your team delivers this service; you own it and improve it. {since}"
            steps = [
                first,
                client_wins,
                "If a change to how the team works would prevent it, call `revise_playbook(service, content, reason)` with "
                f"the whole new playbook (at most {cap} words): concrete steps (who does what, in which order, which "
                f"check), not slogans. Name the cases in the reason. The new version applies to this {what}.",
                raise_bar,
            ]
            if pb.version >= 2:
                steps.append(
                    "If the current version did worse than an earlier one, restore that one "
                    f"(read {self._paths.service_dir(addr, c.name)}/history/PLAYBOOK.v<k>.md)."
                )
            steps.append(f"If nothing needs to change, do not revise. Then handle the {what} following the playbook.")
            lead = (
                "The client rejected a delivery: decide now whether the playbook must change so this does not happen "
                f"again (revise_playbook), then handle the {what}."
                if rejected else "Before working on the new request:"
            )
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
        playbooks: PlaybookSection, reflections: ReflectSection,
    ) -> None:
        self._catalog = catalog
        self._listing = listing
        self._digest = digest
        self._tasks = tasks
        self._rejections = rejections
        self._playbooks = playbooks
        self._reflections = reflections

    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        owned = self._catalog.owned_services(addr)
        if not owned:
            return ""
        sections = [self._listing.listing(addr, owned)]
        working = {t.service for t in self._tasks.open_tasks(addr) if t.service}
        new = {m.service for m in batch if m.type == "task" and m.service and not m.revises and m.to == addr}
        rejected = self._rejections.among(addr, batch)
        digests = {
            c.name: d for c in owned if c.name in new | rejected and (d := self._digest.reflection_digest(addr, c.name)) is not None
        }
        for c in owned:
            if c.name in working:
                sections.append(self._playbooks.section(addr, c, reflecting=c.name in digests))
        for c in owned:
            if c.name in digests:
                sections.append(self._reflections.section(
                    addr, c, digests[c.name], rejected=c.name in rejected, new_request=c.name in new,
                ))
        return "".join(f"\n{s}\n" for s in sections)
