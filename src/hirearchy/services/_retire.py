"""The client takes a service of a direct report out of use."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import ROOT, Clock, EventSink, OrgError, parent
from ._criteria import unanswered
from ._protocols import OwnerAddresses, ServiceRetirement
from .api import Rejection, ServiceCatalog, ServiceEvidence, ServiceStore

ROOT_ONLY_APPROVED = "refused: approved_in records the user's approval of a change; only root passes it. Nothing was retired."
RETIRE_UNRATED = (
    "refused: {n} delivered request(s) of `{name}` have no verdict yet: {tasks}. Record the user's verdict on each with feedback first "
    "(CLI: hirearchy feedback <task id> accept|reject --note ...); a service is retired only after its verdicts, so that its record stays "
    "complete. Nothing was retired."
)
RETIRE_OPEN = (
    "refused: rejection {assertion} (message {note}) on task {task} of `{name}` has no answer yet. Ask the user the one question first "
    "({question}) and record the answer: define_service(..., answers=\"{note}\", about=<the id you asked about>, words=<their answer, verbatim>) "
    "on yes (CLI: --answers, --about, --words), "
    'feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", '
    "note=<their answer, verbatim>) otherwise (CLI: --confirms, --criterion, --source human, --note). A service is retired only after its "
    "rejections are answered. Nothing was retired."
)
RETIRE_UNREADABLE = (
    "refused: the record of `{name}` cannot be read ({error}), so the service was not retired. Try again; if it persists, tell the user."
)


class RuleServiceRetirement(ServiceRetirement):
    """Same authority as a definition: the parent of the owner. The files are kept, under ``services/.retired``. Root retires a service only after
    its verdicts and answers (the basis of the gate of the criteria): the copy that is kept then holds a complete record."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, store: ServiceStore, owners: OwnerAddresses, delivery: MessageDelivery,
        clock: Clock, events: EventSink, evidence: ServiceEvidence,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._store = store
        self._owners = owners
        self._delivery = delivery
        self._clock = clock
        self._events = events
        self._evidence = evidence

    def retire_service(self, actor: str, owner: str, name: str, reason: str, approved_in: str = "") -> str:
        actor = self._agents.require(actor)
        approval = approved_in.strip()
        if actor != ROOT and approval:
            raise OrgError(ROOT_ONLY_APPROVED)
        owner = self._owners.resolve(actor, owner)
        if owner == ROOT or not self._agents.exists(owner) or parent(owner) != actor:
            raise OrgError(f"you can only retire services of your direct reports (root: top-level agents); {owner!r} is not one")
        if self._catalog.read_contract(owner, name) is None:
            known = ", ".join(self._catalog.service_names(owner)) or "none"
            raise OrgError(f"{owner} offers no service called `{name}`. Its services: {known}")
        if not (reason or "").strip():
            raise OrgError("say why the service is retired (reason)")
        if actor == ROOT:  # an agent client retires its report's service as before
            self._check_record(owner, name)
        now = self._clock.now()
        record = {"retired": now.isoformat(timespec="seconds"), "by": actor, "reason": reason.strip(), **({"approved_in": approval} if approval else {})}
        dest = self._store.retire(owner, name, f"{now:%Y%m%dT%H%M%S%f}", record)
        self._events.emit("service.retire", actor=actor, owner=owner, service=name, by=actor)
        self._delivery.notify(
            owner, f"service {name} retired",
            f"{actor} retired the service `{name}`: {reason.strip()}. It cannot be requested any more; its files are kept at "
            f"{dest}.", wake=False,
        )
        return f"retired service `{name}` of {owner}; files kept at {dest}"

    def _check_record(self, owner: str, name: str) -> None:
        """Every delivery has its verdict and every rejection its answer (a link, or a contract version that answers it), or the retirement is refused
        and nothing is moved. A record that cannot be read refuses too: a skipped check would keep an incomplete record."""
        try:
            basis = self._evidence.amendment_basis(owner, name)
            waiting = unanswered(basis, self._store, owner, name)
        except (OrgError, OSError) as error:
            raise OrgError(RETIRE_UNREADABLE.format(name=name, error=error)) from error
        if basis.unrated:
            raise OrgError(RETIRE_UNRATED.format(n=len(basis.unrated), name=name, tasks=", ".join(basis.unrated)))
        if waiting:
            oldest: Rejection = waiting[0]
            raise OrgError(RETIRE_OPEN.format(
                assertion=oldest.assertion, note=oldest.note, task=oldest.task, name=name, question=oldest.question,
            ))
