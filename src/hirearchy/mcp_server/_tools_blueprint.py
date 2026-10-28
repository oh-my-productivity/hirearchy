"""The assistant's way to an organization: ``blueprint_example``, ``propose_org`` and ``apply_org``.

The tools only hand over to three roles (the example, the proposal, the application), which hold the rules and the refusal texts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..agents import AgentDirectory
from ..blueprint import BlueprintApplier, BlueprintExamples, BlueprintLoader, ExtensionApplying, PlanIdentity, PlanRenderer, is_extension
from ..daemon import SchedulerStatus
from ..kernel import Environment, OrgError, OrgLayout, Provider
from ._ports import ExampleLocation, ExampleText, PlanApplication, PlanProposal, PlanTarget, SetupMode, ToolGroup
from .api import OrgBindingPort

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


EXTEND_CURRENT = "current"
EXTEND_MODE = 'refused: this blueprint changes an existing organization (it has extend:), so call propose_org(blueprint, extend="current").'
EXTEND_FULL = (
    'refused: extend="current" takes an extension blueprint (a top-level extend: with add_agents, add_services, add_charter_lines, remove_charter_lines, '
    "limits, budgets, schedules, retire_services or retire); a full blueprint builds a new team: call propose_org(blueprint) without extend."
)
EXTEND_TARGET = 'refused: extend names the organization this server is bound to: "current" or {path}. Nothing was read.'
EXTEND_NONE = "refused: there is no organization yet, so there is nothing to extend: create_org(mission=...) and a full blueprint come first."
MISSING_PLAN_ID = (
    "not applied: plan_id is missing, so this is not the plan the user approved. Call propose_org(blueprint, extend=\"current\"), show the PLAN FOR YOU "
    "block to the user, get their explicit approval, then call apply_org(blueprint, approved=True, plan_id=<the plan_id from that propose_org>) with the "
    "same blueprint"
)


class EnvironmentExampleLocation(ExampleLocation):
    def __init__(self, environment: Environment, binding: OrgBindingPort) -> None:
        self._environment = environment
        self._binding = binding

    def base(self) -> Path:
        cwd = self._environment.cwd().resolve()
        located = self._binding.location()
        if cwd == cwd.parent or (located is not None and (cwd == located or located in cwd.parents)):
            return self._environment.home()
        return cwd


class TemplateExampleText(ExampleText):
    def __init__(self, examples: Provider[BlueprintExamples], location: ExampleLocation) -> None:
        self._examples = examples
        self._location = location

    def example(self, kind: str, service: bool) -> str:
        return self._examples().example(kind, self._location.base(), service=service)


class BindingPlanTarget(PlanTarget):
    def __init__(self, binding: OrgBindingPort, directory: Provider[AgentDirectory]) -> None:
        self._binding = binding
        self._directory = directory

    def bound(self) -> Path | None:
        return self._binding.location()

    def line(self, extending: bool = False) -> str:
        located = self._binding.location()
        if located is not None:
            agents = len(self._directory().agents())
            return f"Target organization: {located} (exists, {agents} agent(s) besides root; " + ("this plan changes it)" if extending else "apply_org adds to it)")
        root = self._binding.root
        where = root if root is not None else "(path given to create_org)"
        return f"Target organization: {where} (none yet: create_org(mission=...) comes first, then apply_org)"


class RenderedPlanProposal(PlanProposal):
    def __init__(self, loader: Provider[BlueprintLoader], renderer: Provider[PlanRenderer], target: PlanTarget) -> None:
        self._loader = loader
        self._renderer = renderer
        self._target = target

    def propose(self, blueprint: str, extend: str | None = None) -> str:
        if extend is not None:
            bound = self._target.bound()
            if extend.strip() != EXTEND_CURRENT and (bound is None or extend.strip() != str(bound)):
                raise OrgError(EXTEND_TARGET.format(path=bound if bound is not None else "(none yet)"))
        bp = self._loader().load_text(blueprint)
        if extend is None:
            if is_extension(bp):
                raise OrgError(EXTEND_MODE)
            return self._renderer().propose_text(bp, target=self._target.line(), require_sources=True)
        if not is_extension(bp):
            raise OrgError(EXTEND_FULL)
        if self._target.bound() is None:
            raise OrgError(EXTEND_NONE)
        return self._renderer().propose_text(bp, target=self._target.line(extending=True), require_sources=True)


class ApprovedPlanApplication(PlanApplication):
    def __init__(
        self, setup: SetupMode, loader: Provider[BlueprintLoader], identity: Provider[PlanIdentity], applier: Provider[BlueprintApplier],
        scheduler: Provider[SchedulerStatus], layout: Provider[OrgLayout], extensions: Provider[ExtensionApplying] | None = None,
    ) -> None:
        self._setup = setup
        self._loader = loader
        self._identity = identity
        self._applier = applier
        self._scheduler = scheduler
        self._layout = layout
        self._extensions = extensions

    def apply(self, blueprint: str, approved: bool, plan_id: str | None) -> str:
        if not approved:
            raise OrgError("not applied: the user must approve the plan first. Call propose_org(blueprint), show the "
                           "PLAN FOR YOU block to the user, and only after their explicit approval call "
                           "apply_org(blueprint, approved=True, plan_id=<the plan_id propose_org returned>)")
        bp = self._loader().load_text(blueprint)
        if is_extension(bp) and self._extensions is not None:  # the extension applier makes the plan_id comparison against the organization as it is now
            if not plan_id:
                raise OrgError(MISSING_PLAN_ID)
            if self._setup.active():
                raise OrgError("not applied: there is no organization yet, so call create_org(mission=...) first, then "
                               "apply_org again with the same blueprint and plan_id")
            return self._extensions().apply(bp, plan_id=plan_id.strip(), require_sources=True)
        if not plan_id or plan_id.strip() != self._identity().plan_id(bp):
            raise OrgError(("not applied: plan_id is missing" if not plan_id else "not applied: plan_id does not match this blueprint")
                           + ", so this is not the plan the user approved. Call propose_org(blueprint), show the PLAN FOR YOU "
                           "block to the user, get their explicit approval, then call apply_org(blueprint, approved=True, "
                           "plan_id=<the plan_id from that propose_org>) with the same blueprint")
        if self._setup.active():
            raise OrgError("not applied: there is no organization yet, so call create_org(mission=...) first, then "
                           "apply_org again with the same blueprint and plan_id")
        summary = self._applier().apply(bp, require_sources=True)
        running = self._scheduler().describe().startswith("scheduler: running")
        if not summary.task_id:
            nxt = ("Nothing runs yet: the services are ready. When the user asks for one, call request(service, inputs) "
                   "(see services()), then start() if the scheduler is not running.")
        else:
            nxt = ("The scheduler is already running and will pick the work up; answer status questions with progress()."
                   if running else "Next step: call start() to run the scheduler, then answer status questions with progress().")
        return f"applied the blueprint to {self._layout().root}\n{summary.text()}\n{nxt}"


class BlueprintTools(ToolGroup):
    def __init__(self, examples: ExampleText, proposal: PlanProposal, application: PlanApplication) -> None:
        self._examples = examples
        self._proposal = proposal
        self._application = application

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def blueprint_example(kind: str = "research", service: bool = False) -> str:
            """A ready-to-edit blueprint (YAML with a comment on every field and a one-paragraph schema summary).

        kind: "research" (facts from the web with source URLs, fact-checked), "documents" (write from the user's local
        files, no web; uses `needs.inputs`, read-only folders), "code" (software in a repo workspace, with tests and
        local commits), "analysis" (the user's data files, read-only, analysed by a checked script) or "extension" (a change to the existing
        organization: new agents, services, lines in a charter, limits, budgets, retires; the template of the extension that propose_org(blueprint,
        extend="current") takes, with every field explained). Replace every
        <PLACEHOLDER> with what the user told you (ask for what is missing; do not invent lists), delete what does not apply, then call propose_org with the text. Read-only.

        service: true for work the user wants again and again ("every week", "whenever I..."): the template then offers it
        as a standing service (`services:` with inputs, acceptance, deliverable and budget per request, and an optional
        first request) instead of a one-off `task:`.
        """
            return self._examples.example(kind, service)

        @mcp.tool()
        def propose_org(blueprint: str, extend: str | None = None) -> str:
            """Validate a blueprint and return the plan the user must approve. Writes nothing; safe to call repeatedly.

        blueprint: YAML or JSON text (never a file path). Start from blueprint_example(kind) for a template with every
        field explained. Schema: `mission` (one paragraph); `needs` {scope, deliverable {description, format,
        max_words, path (absolute)}, quality_bar, sources, inputs (read-only folders), workspace (the one absolute
        folder agents may write in), budget_runs (the user's cap), models {cheap, strong} (optional: none = every agent on claude-sonnet-5.5), model_policy, review
        (true/false), approval, progress, kind (research|writing|code), code {tests, packaging, commits}}; `agents`:
        ONE top-level agent (template manager) with `children`; each agent has name and a template (manager,
        researcher, writer, reviewer, fact-checker, engineer, tester, code-reviewer, analyst, data-checker) or a charter, and optionally
        model, tools, workspace, scale; `task` {to, title, goal, acceptance: list of exact, checkable criteria}; optional
        `services` (recurring work the top agent offers on request): [{name, description, inputs: [{name, description,
        required}], acceptance, deliverable {description, format, max_words, path}, budget (runs per request), playbook,
        locked}], in which case `task` may be omitted or be a first request {service, inputs: {name: value}, title}.
        Criteria (the acceptance items of `task` and of each service): acceptance items: {text, from: <the user's exact words in
        needs.elicitation>, asked} or {text, default: true}; needs.elicitation: the user's answers, verbatim (required with criteria).
        extend: "current" to change the organization this server is bound to: blueprint is then an extension (extend: with add_agents,
        add_services, add_charter_lines, remove_charter_lines, limits, budgets, schedules, retire_services, retire; see
        blueprint_example("extension")). The plan shows what it adds, changes and removes; its plan_id holds only while nothing it touches changes.
        Works before the organization exists. Returns (1) a block headed "PLAN FOR YOU": show it to the user exactly
        as written and wait for their explicit approval; (2) Details, the full plan for you; (3) a plan_id that
        apply_org requires. If the plan has errors, fix the blueprint and propose again; never ask the user to approve
        a plan with errors.
        """
            return self._proposal.propose(blueprint, extend)

        @mcp.tool()
        def apply_org(blueprint: str, approved: bool = False, plan_id: str | None = None) -> str:
            """Create the agents of a blueprint and give its first task. Only after the user approved the plan.

        blueprint: the YAML/JSON text the user approved via propose_org (unchanged). approved: pass True only after
        the user explicitly approved that plan in this conversation; otherwise nothing happens. plan_id: the id that
        propose_org returned for exactly this blueprint; a missing or different id is refused (propose again, show the
        PLAN FOR YOU block, get approval). Needs an existing organization (create_org first if there is none).
        An extension (extend:) changes the existing organization: refused when anything it touches changed since propose_org.
        Refuses with the issues if the blueprint has errors or a name is taken, and undoes everything if it fails
        midway. Returns what was created (agents, services, the first task or request); then call start() (not when
        the blueprint gave no first task: the services wait for request(service, inputs)).
        """
            return self._application.apply(blueprint, approved, plan_id)
