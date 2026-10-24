"""Standing services, by role, so a plain worker sees none of them: root and every agent that has direct reports or may hire get ``services``,
``define_service``, ``request`` and ``feedback``; an agent that offers a service gets ``services`` and ``revise_playbook``."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..kernel import ROOT, Message, OrgError, Provider, parent
from ..reflection import ServiceReports, ServiceSteps
from ..services import BASE_HEADING, ServiceCatalog, ServiceCommands
from ._ports import ServiceRoles, SetupMode, ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class DirectoryServiceRoles(ServiceRoles):
    """Who needs the service tools, from the directory, the charters and the catalog of services (decided when the server starts)."""

    def __init__(
        self, setup: SetupMode, directory: Provider[AgentDirectory], charters: Provider[CharterReader], catalog: Provider[ServiceCatalog],
    ) -> None:
        self._setup = setup
        self._directory = directory
        self._charters = charters
        self._catalog = catalog

    def manager(self, me: str) -> bool:
        if me == ROOT:
            return True
        if self._setup.active():
            return False
        return bool(self._directory().children(me) or self._charters().charter(me)[0].get("can_hire"))

    def owner(self, me: str) -> bool:
        return not self._setup.active() and me != ROOT and bool(self._catalog().service_names(me))


def _step(make: Callable[[], str]) -> str:
    """The next step root is told after a write ("" when there is none). It is advice about something already recorded, so a record that cannot
    be read (``OrgError``, ``OSError``) gives no step and never fails the call; any other error is a bug in the step and propagates."""
    try:
        text = make()
    except (OrgError, OSError):
        return ""
    return f"\n{text}" if text else ""


class ServiceTools(ToolGroup):
    def __init__(
        self, roles: ServiceRoles, reports: Provider[ServiceReports], commands: Provider[ServiceCommands], budgets: Provider[BudgetQuery],
        steps: Provider[ServiceSteps],
    ) -> None:
        self._roles = roles
        self._reports = reports
        self._commands = commands
        self._budgets = budgets
        self._steps = steps

    def register(self, mcp: FastMCP, me: str) -> None:
        manager, owner = self._roles.manager(me), self._roles.owner(me)
        if not (manager or owner):
            return

        @mcp.tool()
        def services() -> str:
            """The standing services you can request from your direct reports and the ones you offer, with contract and
        playbook versions, inputs, budget per request and the record so far (requests, outcomes, runs, feedback)."""
            return self._reports().services_text(me)

        if manager:
            self._register_client_tools(mcp, me)
        if owner:
            self._register_owner_tools(mcp, me)

    def _register_client_tools(self, mcp: FastMCP, me: str) -> None:
        if me == ROOT:  # only root records the user's answer: the agents' tool has no `answers`, `about` or `words`
            self._register_root_define(mcp, me)
        else:
            self._register_agent_define(mcp, me)

        if me == ROOT:  # only root records where a rework comes from: the agents' tool has no `source`
            self._register_root_request(mcp, me)
        else:
            self._register_agent_request(mcp, me)

        if me == ROOT:  # only root records where a verdict comes from and what it is about: the agents' tool has neither
            self._register_root_feedback(mcp, me)
        else:
            self._register_agent_feedback(mcp, me)

    def _register_root_define(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def define_service(
            owner: str,
            name: str,
            description: str | None = None,
            acceptance: list[str] | None = None,
            deliverable: dict | None = None,  # type: ignore[type-arg]
            budget: int | None = None,
            inputs: list[dict] | None = None,  # type: ignore[type-arg]
            playbook: str | None = None,
            locked: bool | None = None,
            notes: str | None = None,
            add_acceptance: list[str] | None = None,
            remove_acceptance: list[str] | None = None,
            answers: str | None = None,
            about: str | None = None,
            words: str | None = None,
        ) -> str:
            """Define a standing service of one of your direct reports (root: a top-level agent), or amend its contract.

        You are the client: the contract is yours; the owner cannot change it. owner: the report. name: lowercase-dashed,
        unique among your reports' services. FIRST definition needs description (one line), acceptance (concrete,
        checkable criteria that travel with every request), deliverable ({description, format?, max_words?, path?
        (absolute)}) and budget (runs handed down with each request); optional: inputs ([{name, description, required
        (default true)}] the requester fills in), playbook (markdown workflow, first definition only), locked (true = the
        owner may not revise the playbook), notes (free text for the owner).
        AMENDMENT (the service exists): pass only what changes, the rest stays. To add a lasting requirement:
        `add_acceptance=[<criterion>]`; to drop one: `remove_acceptance=[<its exact text>]`; `acceptance` replaces
        all (not together with add/remove). The old contract is archived and the owner quietly told what changed; the
        reply lists the criteria now in force. An amendment that changes nothing is refused.
        CHANGING THE CRITERIA (you, root): only as the user's answer after a rejection: answers=<the rejection's
        message id>, about=<the C or R id your one question named>, words=<their answer, verbatim> (it records their yes
        as the link itself); or, for a change the user asks for on their own outside any rejection, words=<their
        request, verbatim> alone (never admits a playbook revision). Every delivered request of the service needs its
        verdict first.
        """
            return self._commands().define_service(
                me, owner, name, description=description, inputs=inputs, acceptance=acceptance,
                deliverable=deliverable, budget=budget, playbook=playbook, locked=locked, notes=notes,
                add_acceptance=add_acceptance, remove_acceptance=remove_acceptance, answers=answers, about=about, words=words,
            )

    def _register_agent_define(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def define_service(
            owner: str,
            name: str,
            description: str | None = None,
            acceptance: list[str] | None = None,
            deliverable: dict | None = None,  # type: ignore[type-arg]
            budget: int | None = None,
            inputs: list[dict] | None = None,  # type: ignore[type-arg]
            playbook: str | None = None,
            locked: bool | None = None,
            notes: str | None = None,
            add_acceptance: list[str] | None = None,
            remove_acceptance: list[str] | None = None,
        ) -> str:
            """Define a standing service of one of your direct reports (root: a top-level agent), or amend its contract.

        You are the client: the contract is yours; the owner cannot change it. owner: the report. name: lowercase-dashed,
        unique among your reports' services. FIRST definition needs description (one line), acceptance (concrete,
        checkable criteria that travel with every request), deliverable ({description, format?, max_words?, path?
        (absolute)}) and budget (runs handed down with each request); optional: inputs ([{name, description, required
        (default true)}] the requester fills in), playbook (markdown workflow, first definition only), locked (true = the
        owner may not revise the playbook), notes (free text for the owner).
        AMENDMENT (the service exists): pass only what changes, the rest stays. To add a lasting requirement:
        `add_acceptance=[<criterion>]`; to drop one: `remove_acceptance=[<its exact text>]`; `acceptance` replaces
        all (not together with add/remove). The old contract is archived and the owner quietly told what changed; the
        reply lists the criteria now in force. An amendment that changes nothing is refused.
        """
            return self._commands().define_service(
                me, owner, name, description=description, inputs=inputs, acceptance=acceptance,
                deliverable=deliverable, budget=budget, playbook=playbook, locked=locked, notes=notes,
                add_acceptance=add_acceptance, remove_acceptance=remove_acceptance,
            )

    def _register_root_feedback(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def feedback(
            task_id: str,
            verdict: str,
            note: str = "",
            source: str = "relayed",
            criterion: list[str] | None = None,
            confirms: str | None = None,
        ) -> str:
            """Tell the owner of a service whether a delivered request was good: verdict "accept" or "reject".

        task_id: a service request (or rework) you sent that has a result. note: required for reject (what was wrong),
        optional for accept: the user's own words, verbatim. It costs no run and does not wake the owner; it shows up in
        the evidence the owner reviews before its next request (and the moment a rejection arrives). Give it on the user's
        own judgement of each delivery, also on a rework: every verdict stays in the case's history, the latest one is the
        final verdict, and an earlier reject is still shown to the owner with your words. source: "human" only when the
        verdict is the user's own judgement and note holds their words; "relayed" (the default) for anything you concluded
        yourself: it is shown to the owner but weighs nothing when it revises its playbook. criterion (reject only): what
        the rejection is about, as ids: "C<k>" (a contract criterion, see `services`), "R<k>" (an earlier rejection it
        repeats) or "none" (no lasting rule); on the rejection itself it is shown as not confirmed, whatever the source.
        Pass your reading there (one id: what you read the rejection as), and the reply gives the exact question naming it.
        confirms: the user's answer that changes no criterion ("no", "a one-off", "about C<k> as it is"): call again with
        the same task_id, verdict "reject", confirms=<the rejection's message id>, criterion ("none", "R<j>" or "C<k>"),
        source "human" and their answer verbatim as note; it records the link, not a new verdict. A yes that changes the
        contract is define_service(..., answers=<the rejection's message id>, about=<the id>, words=<their answer>), which
        records the link itself; after it, that rejection takes no confirms. Feedback is for reflection only: it never
        waives an acceptance criterion or changes the outcome of the request.
        """
            msg = self._commands().feedback(me, task_id, verdict, note, source=source, criterion=criterion, confirms=confirms)
            if confirms is not None:
                return (f"recorded: rejection {confirms} is about {msg.criterion} (source {msg.source}; message {msg.id}); "
                        f"it does not wake {msg.to}")
            about = f", about {msg.criterion} (not confirmed)" if msg.criterion else ""
            return (f"feedback {verdict} recorded on {task_id} for {msg.to} (message {msg.id}, source {msg.source}{about}); "
                    f"it does not wake {msg.to}" + _step(lambda: self._steps().feedback_step(msg)))

    def _register_agent_feedback(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def feedback(task_id: str, verdict: str, note: str = "") -> str:
            """Tell the owner of a service whether a delivered request was good: verdict "accept" or "reject".

        task_id: a service request (or rework) you sent that has a result. note: required for reject (what was wrong),
        optional for accept. It costs no run and does not wake the owner; it shows up in the evidence the owner reviews
        before its next request (and the moment a rejection arrives). Give it on your own judgement of each delivery,
        also on a rework: every verdict stays in the case's history, the latest one is the final verdict, and an
        earlier reject is still shown to the owner with your words. Feedback is for reflection only: it never waives an
        acceptance criterion or changes the outcome of the request.
        """
            msg = self._commands().feedback(me, task_id, verdict, note)
            return f"feedback {verdict} recorded on {task_id} for {msg.to} (message {msg.id}); it does not wake {msg.to}"

    def _requested(self, me: str, msg: Message, service: str, revises: str | None, base: str | None = None) -> str:
        tail = "Call start() if the scheduler is not running." if me == ROOT else f"Your budget is now {self._budgets().budget(me)}."
        total = self._reports().case_total(msg) if revises else ""
        asked = _step(lambda: self._steps().rework_step(msg)) if revises and me == ROOT else ""  # a relayed rework repeats the client questions
        return (f"requested service `{service}` from {msg.to}: task {msg.id}, budget {msg.budget} "
                f"(contract v{msg.contract}, playbook v{msg.playbook}). {tail}" + (f"\n{total}" if total else "") + asked + self._based(msg, base))

    @staticmethod
    def _based(msg: Message, base: str | None) -> str:
        """What the base the caller named did (the task body has the base section only when a relayed rework changed what the user judged)."""
        if base is None:
            return ""
        if BASE_HEADING not in msg.body:
            return "\nbase: not needed (no relayed rework changed the delivery the user judged)."
        if base == "delivered":
            return "\nbase delivered: the lead starts from the version the user judged."
        return "\nbase latest: the changes of your own relayed rework stay in it: tell the user so."

    def _register_root_request(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def request(
            service: str,
            inputs: dict | None = None,  # type: ignore[type-arg]
            title: str = "",
            note: str = "",
            extra_acceptance: list[str] | None = None,
            budget: int | None = None,
            revises: str | None = None,
            source: str | None = None,
            base: str | None = None,
        ) -> str:
            """Ask a direct report for one of its services (see `services`): a task built from the contract.

        inputs: {input name: value}; required ones must be present. note: free text for the owner. extra_acceptance:
        criteria added after the contract's (the contract's always apply). budget: runs handed down (default: the
        contract's; for a rework the user asked for, source="human", what is left of the runs the user approved for the
        case, at most the contract's, and 1 when nothing is left; the usual reserve rule applies). revises: id of an
        earlier request of this service to send back for rework; the reply then states the case total (runs used by the
        whole chain, the user's and your relayed reworks' apart, runs handed down, the contract's budget per request)
        and tells you to inform the user when the user's requests cost more than they approved, and names the top-up to
        ask for when a rework the user asked for gets less than a round of the team needs.
        source (with revises): "human" when the user asked for this rework
        (a rework after their own rejection, carrying their corrections, is one), "relayed" (the default) when it is your
        own reading; the owner sees which.
        base (with revises and source="human"): "delivered" or "latest". When your own relayed rework changed a file after the
        delivery the user judged, this is refused until you say which version the user's corrections apply to:
        "delivered" (the lead restores the version they judged, then applies their corrections) or "latest" (your
        relayed changes stay; tell the user).
        Returns the task id; the result comes back like any result, then rate it with `feedback`.
        """
            msg = self._commands().request(me, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance,
                                           budget=budget, revises=revises, source=source, base=base)
            return self._requested(me, msg, service, revises, base)

    def _register_agent_request(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def request(
            service: str,
            inputs: dict | None = None,  # type: ignore[type-arg]
            title: str = "",
            note: str = "",
            extra_acceptance: list[str] | None = None,
            budget: int | None = None,
            revises: str | None = None,
        ) -> str:
            """Ask a direct report for one of its services (see `services`): a task built from the contract.

        inputs: {input name: value}; required ones must be present. note: free text for the owner. extra_acceptance:
        criteria added after the contract's (the contract's always apply). budget: runs handed down (default: the
        contract's; the usual reserve rule applies). revises: id of an earlier request of this service to send back for
        rework; the reply then states the case total (runs used by the whole chain, runs handed down, the contract's
        budget per request) and tells you to inform the user when the case exceeds that budget. Returns the task id;
        the result comes back like any result, then rate it with `feedback`.
        """
            msg = self._commands().request(me, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance,
                                           budget=budget, revises=revises)
            return self._requested(me, msg, service, revises)

    def _register_owner_tools(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def revise_playbook(service: str, content: str, reason: str, evidence: list[str]) -> str:
            """Write the next version of the playbook of a service you offer: how your team delivers it.

        Only the owner can; refused when the contract is locked. content: the WHOLE new playbook in markdown (steps: who
        does what, in which order, which check; budget plan; pitfalls), at most playbook_max_words (default 1000) words,
        and different from the current one. reason: 1-400 characters naming the cases it rests on. evidence (required):
        the ids it rests on, from the regression list and the digest in your prompt: "R<k>" (a rejection by the client),
        "C<k>" (a contract criterion), verdict ids, case ids. It is admitted only when the same criterion or regression
        assertion failed in 2 different cases the client rejected, or when it cites a criterion your parent added to the
        contract by an amendment the client confirmed (your Reflect section and the amendment note name them); line by
        line: under the first rule every line you add or change carries the id it rests on ("[C6]"), under the second it
        is only that criterion's words ("- C<k>: <its text>"); a link note id counts as its criterion; your lessons,
        relayed verdicts and an agent client's verdicts are not evidence. Pass evidence=[] only for the first playbook
        (the steps your team followed, nothing more), or to restore unchanged a version your parent wrote. A refusal
        writes nothing and gives you a question to send your parent once; do not wait for the answer (it reaches you as
        a contract change or a criterion link). The old version is archived; your parent is told quietly. The playbook
        may raise the bar, never lower it: the acceptance criteria come from the contract. Returns the new version,
        which applies from now on.
        """
            version = self._commands().revise_playbook(me, service, content, reason, evidence)
            client = parent(me)
            return f"playbook of `{service}` is now v{version}; {client} was told without being woken"
