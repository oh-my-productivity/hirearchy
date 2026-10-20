"""The client defines a service for a direct report, or amends its contract."""

from __future__ import annotations

from collections.abc import Mapping

from ..agents import AgentDirectory
from ..delivery import MessageDelivery
from ..kernel import NAME_RE, ROOT, Clock, EventSink, JsonObject, OrgError, parent
from ._lines import criteria_lines
from ._protocols import ContractAmendment, ContractDefinitions, OwnerAddresses, PlaybookTexts, PlaybookWriter, ServicePlaces
from .api import DESCRIPTION_MAX, Contract, ContractNormalizer, ServiceCatalog, ServiceStore


class RuleContractDefiner(ContractDefinitions):
    """Only the parent of the owner defines or amends; a first definition is complete, an amendment keeps what it does not name."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, store: ServiceStore, places: ServicePlaces, normalizer: ContractNormalizer,
        amendment: ContractAmendment, texts: PlaybookTexts, owners: OwnerAddresses, playbooks: PlaybookWriter, delivery: MessageDelivery,
        clock: Clock, events: EventSink,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._store = store
        self._places = places
        self._normalizer = normalizer
        self._amendment = amendment
        self._texts = texts
        self._owners = owners
        self._playbooks = playbooks
        self._delivery = delivery
        self._clock = clock
        self._events = events

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None, inputs: object, acceptance: object,
        deliverable: Mapping[str, object] | None, budget: int | None, playbook: str | None, locked: bool | None, notes: str | None,
        add_acceptance: object, remove_acceptance: object,
    ) -> str:
        actor = self._agents.require(actor)
        owner = self._owners.resolve(actor, owner)
        if owner == ROOT or not self._agents.exists(owner):
            raise OrgError(f"no such agent: {owner}. A service is offered by one of your direct reports (root: a top-level agent).")
        client = parent(owner) or ROOT
        if actor != client:
            raise OrgError(
                f"only {client}, the parent of {owner}, can define its services (you are {actor}): the contract belongs "
                f"to the client. Ask {client}, or define services for your own direct reports."
            )
        if not NAME_RE.fullmatch(name or ""):
            raise OrgError("a service name is lowercase letters, digits and dashes, starting with a letter (max 32), e.g. weekly-brief")
        for sibling in self._agents.children(client):
            if sibling != owner and name in self._catalog.service_names(sibling):
                raise OrgError(
                    f"a service called `{name}` already exists at {sibling}. Requests name the service only, so names "
                    f"must be unique among the agents that report to {client}: pick another name."
                )
        old = self._catalog.read_contract(owner, name)
        if old is not None and playbook is not None:
            raise OrgError(
                f"the playbook belongs to {owner}, which revises it with revise_playbook: do not pass `playbook` when "
                "you redefine the contract. Leave it out; the existing playbook stays."
            )
        if acceptance is not None and (add_acceptance is not None or remove_acceptance is not None):
            raise OrgError(
                "`acceptance` replaces all criteria; do not combine it with add_acceptance / remove_acceptance. Use "
                "add_acceptance / remove_acceptance alone to change single criteria."
            )
        if old is None:
            if add_acceptance is not None or remove_acceptance is not None:
                raise OrgError(
                    f"service `{name}` does not exist yet: add_acceptance / remove_acceptance amend an existing contract. "
                    "Give the full `acceptance` list for a first definition."
                )
            missing = [k for k, v in (("description", description), ("acceptance", acceptance), ("deliverable", deliverable),
                                      ("budget", budget)) if v is None]
            if missing:
                raise OrgError(f"a first definition of `{name}` needs {', '.join(missing)} (it does not exist yet, so there is nothing to keep)")

        if description is not None:
            description = description.strip() if isinstance(description, str) else ""
            if not description or len(description) > DESCRIPTION_MAX or "\n" in description:
                raise OrgError(f"description is one line of at most {DESCRIPTION_MAX} characters saying what the service delivers")
        if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int) or budget < 1):
            raise OrgError("budget is the number of runs handed down with each request: a whole number, at least 1")
        if locked is not None and not isinstance(locked, bool):
            raise OrgError("locked must be true or false")
        inputs_n = self._normalizer.inputs(inputs) if inputs is not None or old is None else old.inputs
        deliverable_n = self._normalizer.deliverable(deliverable) if deliverable is not None else (old.deliverable if old else {})
        if acceptance is not None:
            accept_n = criteria_lines(acceptance, "acceptance", required=True)
        elif old is None:
            accept_n = []
        else:
            accept_n = self._amendment.amended_criteria(name, old.acceptance, add_acceptance, remove_acceptance)
        playbook_body = self._texts.body(playbook) if playbook is not None else None

        now = self._clock.now().isoformat(timespec="microseconds")
        notes_n = (notes if notes is not None else (old.notes if old else "") or "").strip()
        new = Contract(
            name=name, owner=owner, description=description if description is not None else (old.description if old else ""),
            inputs=inputs_n, acceptance=accept_n, deliverable=deliverable_n,
            budget=budget if budget is not None else (old.budget if old else 1),
            locked=locked if locked is not None else (old.locked if old else False),
            version=1 if old is None else old.version + 1, notes=notes_n,
        )
        meta: JsonObject = {
            "name": name, "description": new.description, "inputs": new.inputs, "acceptance": new.acceptance,
            "deliverable": new.deliverable, "budget": new.budget, "locked": new.locked, "version": new.version, "defined_by": actor,
            "defined": now, "created": now if old is None or old.created is None else old.created.isoformat(timespec="microseconds"),
        }
        changes: list[str] = []
        if old is not None:
            changes = self._amendment.changes(old, new)
            if not changes:
                raise OrgError(
                    f"no change: the amendment leaves the contract of `{name}` exactly as it is (v{old.version}). "
                    f"Current criteria:\n{self._amendment.numbered(old.acceptance)}"
                )
        where = self._store.write_contract(owner, name, meta, notes_n, old.version if old is not None else None)
        self._events.emit("service.define", actor=actor, owner=owner, service=name, version=new.version, by=actor, amendment=old is not None)
        if old is None:
            text = f"defined service `{name}` (contract v1) for {owner}: {where}"
            if playbook_body is not None:
                text += f"; playbook v1: {self._playbooks.write(owner, name, 1, playbook_body, actor, 'initial playbook')}"
            else:
                text += f". It has no playbook yet: {owner} writes v1 with revise_playbook after its first request."
            return text
        self._delivery.notify(
            owner, f"contract of service {name} changed to v{new.version}", self._amendment.diff(old, new, changes, where), wake=False,
        )
        kept = self._places.rel(self._places.history_file(owner, name, "SERVICE", old.version))
        return (
            f"redefined service `{name}` of {owner}: contract v{old.version} -> v{new.version} ({where}); the old one "
            f"is kept at {kept}. {owner} was told (without waking it).\n"
            "Changed:\n" + "\n".join(changes) + f"\nAcceptance criteria now ({len(accept_n)}):\n{self._amendment.numbered(accept_n)}"
        )
