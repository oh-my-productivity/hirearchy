"""The way to an organization: the example, the proposal and the application of a blueprint, over scripted ports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import testkit
import testkit.reach.yaml as yaml

from hirearchy.blueprint import BlueprintApplier, BlueprintError, BlueprintExamples, BlueprintLoader, ExtensionApplying, PlanIdentity, PlanRenderer, Summary
from hirearchy.blueprint.testing import applier_over_memory_directories, loader_over_memory, renderer_over_packaged_roles
from hirearchy.daemon import SchedulerState
from hirearchy.daemon.testing import FakeSchedulerStatus
from hirearchy.kernel import ROOT, OrgError, OrgPaths
from hirearchy.kernel.testing import DictEnvironment
from hirearchy.mcp_server._instructions import InstructionText
from hirearchy.mcp_server._tools_blueprint import (
    ApprovedPlanApplication,
    BindingPlanTarget,
    BlueprintTools,
    EnvironmentExampleLocation,
    RenderedPlanProposal,
    TemplateExampleText,
)
from hirearchy.mcp_server.testing import MemoryBinding, agents_in

from ._support import call, described, fails, names, serve

HERE = Path("/memory/org")


class TextLoader(BlueprintLoader):
    def load(self, source: object) -> dict[str, object]:
        return {"source": source}

    def load_text(self, text: str) -> dict[str, object]:
        if text == "bad":
            raise OrgError("blueprint is not valid YAML")
        return {"text": text}


class Examples(BlueprintExamples):
    def __init__(self) -> None:
        self.asked: list[tuple[str, Path | str, bool]] = []

    def example(self, kind: str = "research", base: Path | str = ".", service: bool = False) -> str:
        self.asked.append((kind, base, service))
        return f"EXAMPLE {kind} {base} {service}"


class Renderer(PlanRenderer):
    def __init__(self) -> None:
        self.asked: list[tuple[Mapping[str, object], str]] = []
        self.sources: list[bool] = []

    def render_plan(self, bp, issues=None, *, allowed_roots=None) -> str:  # type: ignore[no-untyped-def]
        return "plan"

    def plan_for_user(self, bp, issues=None, *, allowed_roots=None) -> str:  # type: ignore[no-untyped-def]
        return "for user"

    def propose_text(
        self, bp: Mapping[str, object], *, target: str = "", allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False,
    ) -> str:
        self.asked.append((bp, target))
        self.sources.append(require_sources)
        return f"PROPOSAL {bp['text']}\n{target}"

    def propose(self, source: object, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        return "proposal"


class Identity(PlanIdentity):
    def plan_id(self, bp: Mapping[str, object]) -> str:
        return "abc123"


class Applier(BlueprintApplier):
    def __init__(self, task_id: str = "t1") -> None:
        self.task_id = task_id
        self.applied: list[Mapping[str, object]] = []
        self.sources: list[bool] = []

    def apply(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False) -> Summary:
        self.applied.append(bp)
        self.sources.append(require_sources)
        return Summary(["ceo", "ceo/eng"], self.task_id, "ceo", 6)


def application(exists: bool = True, state: SchedulerState = SchedulerState("stopped"), applier: Applier | None = None) -> ApprovedPlanApplication:
    applier = applier or Applier()
    return ApprovedPlanApplication(InstructionText(MemoryBinding(HERE, exists=exists)), lambda: TextLoader(), lambda: Identity(), lambda: applier,
                                   lambda: FakeSchedulerStatus(state), lambda: OrgPaths(HERE))


def refusal(text: str) -> str:
    return text


def test_the_three_tools_and_their_order() -> None:
    group = BlueprintTools(TemplateExampleText(lambda: Examples(), EnvironmentExampleLocation(DictEnvironment(cwd=Path("/w")), MemoryBinding(HERE))),
                           RenderedPlanProposal(lambda: TextLoader(), lambda: Renderer(), BindingPlanTarget(MemoryBinding(HERE), lambda: agents_in())),
                           application())
    server = serve(group, ROOT)
    assert names(server) == ["blueprint_example", "propose_org", "apply_org"]
    assert described(server)["apply_org"].startswith("Create the agents of a blueprint and give its first task.")


# ------------------------------------------------------------------------------------------------------------- the example


def test_the_examples_go_to_the_current_directory() -> None:
    examples = Examples()
    text = TemplateExampleText(lambda: examples, EnvironmentExampleLocation(DictEnvironment(cwd=Path("/work/here"), home=Path("/home/u")), MemoryBinding(HERE)))
    assert text.example("code", True) == "EXAMPLE code /work/here True"
    assert examples.asked == [("code", Path("/work/here"), True)]


@pytest.mark.parametrize("cwd", ["/", "/memory/org", "/memory/org/ceo/work"])
def test_but_not_to_the_organization_itself_or_a_filesystem_root(cwd: str) -> None:
    location = EnvironmentExampleLocation(DictEnvironment(cwd=Path(cwd), home=Path("/home/u")), MemoryBinding(HERE, exists=True))
    assert location.base() == Path("/home/u")


def test_before_the_organization_exists_the_working_directory_is_never_inside_it() -> None:
    assert EnvironmentExampleLocation(DictEnvironment(cwd=Path("/memory/org"), home=Path("/home/u")), MemoryBinding(HERE)).base() == Path("/memory/org")


# ------------------------------------------------------------------------------------------------------------- the proposal


def test_a_proposal_names_the_target_that_exists() -> None:
    renderer = Renderer()
    agents = agents_in("ceo", "ceo/eng")
    proposal = RenderedPlanProposal(lambda: TextLoader(), lambda: renderer, BindingPlanTarget(MemoryBinding(HERE, exists=True), lambda: agents))
    assert proposal.propose("the blueprint") == (
        "PROPOSAL the blueprint\nTarget organization: /memory/org (exists, 2 agent(s) besides root; apply_org adds to it)")


def test_a_proposal_before_the_organization_exists_says_what_comes_first() -> None:
    target = BindingPlanTarget(MemoryBinding(HERE), lambda: agents_in())
    assert target.line() == "Target organization: /memory/org (none yet: create_org(mission=...) comes first, then apply_org)"
    assert BindingPlanTarget(MemoryBinding(None), lambda: agents_in()).line() == (
        "Target organization: (path given to create_org) (none yet: create_org(mission=...) comes first, then apply_org)")


def test_a_blueprint_that_cannot_be_read_is_the_refusal_of_the_tool() -> None:
    proposal = RenderedPlanProposal(lambda: TextLoader(), lambda: Renderer(), BindingPlanTarget(MemoryBinding(HERE), lambda: agents_in()))
    with pytest.raises(OrgError, match="not valid YAML"):
        proposal.propose("bad")


# ------------------------------------------------------------------------------------------------------------- the application


def test_nothing_is_applied_without_the_approval_of_the_user() -> None:
    with pytest.raises(OrgError) as info:
        application().apply("bp", False, "abc123")
    assert str(info.value) == ("not applied: the user must approve the plan first. Call propose_org(blueprint), show the PLAN FOR YOU block to the user, "
                               "and only after their explicit approval call apply_org(blueprint, approved=True, plan_id=<the plan_id propose_org returned>)")


@pytest.mark.parametrize("given, said", [(None, "plan_id is missing"), ("", "plan_id is missing"), ("zzz", "plan_id does not match this blueprint")])
def test_nothing_is_applied_for_another_plan_than_the_one_the_user_saw(given: str | None, said: str) -> None:
    with pytest.raises(OrgError) as info:
        application().apply("bp", True, given)
    assert str(info.value) == (f"not applied: {said}, so this is not the plan the user approved. Call propose_org(blueprint), show the PLAN FOR YOU "
                               "block to the user, get their explicit approval, then call apply_org(blueprint, approved=True, "
                               "plan_id=<the plan_id from that propose_org>) with the same blueprint")


def test_nothing_is_applied_before_the_organization_exists() -> None:
    with pytest.raises(OrgError) as info:
        application(exists=False).apply("bp", True, " abc123 ")
    assert str(info.value) == ("not applied: there is no organization yet, so call create_org(mission=...) first, then apply_org again with the same "
                               "blueprint and plan_id")


def test_an_approved_plan_is_applied_and_the_next_step_is_start() -> None:
    applier = Applier()
    out = application(applier=applier).apply("bp", True, "abc123")
    assert out == ("applied the blueprint to /memory/org\ncreated 2 agents: ceo, ceo/eng\ntask t1 -> ceo (budget 6)\n"
                   "Next step: call start() to run the scheduler, then answer status questions with progress().")
    assert applier.applied == [{"text": "bp"}]


def test_when_the_scheduler_runs_it_picks_the_work_up() -> None:
    out = application(state=SchedulerState("running", 3, "then")).apply("bp", True, "abc123")
    assert out.endswith("The scheduler is already running and will pick the work up; answer status questions with progress().")


def test_a_blueprint_with_services_only_gives_no_task() -> None:
    out = application(applier=Applier(task_id="")).apply("bp", True, "abc123")
    assert out.endswith("Nothing runs yet: the services are ready. When the user asks for one, call request(service, inputs) "
                        "(see services()), then start() if the scheduler is not running.")


def test_the_tools_hand_over_with_the_defaults_of_their_signature() -> None:
    applier = Applier()
    group = BlueprintTools(TemplateExampleText(lambda: Examples(), EnvironmentExampleLocation(DictEnvironment(cwd=Path("/w")), MemoryBinding(HERE))),
                           RenderedPlanProposal(lambda: TextLoader(), lambda: Renderer(), BindingPlanTarget(MemoryBinding(HERE), lambda: agents_in())),
                           application(applier=applier))
    server = serve(group, ROOT)
    assert call(server, "blueprint_example") == "EXAMPLE research /w False"
    assert call(server, "blueprint_example", kind="documents", service=True) == "EXAMPLE documents /w True"
    assert "PROPOSAL x" in call(server, "propose_org", blueprint="x")
    assert "not applied: the user must approve" in fails(server, "apply_org", blueprint="x")
    assert call(server, "apply_org", blueprint="x", approved=True, plan_id="abc123").startswith("applied the blueprint to /memory/org")


# ------------------------------------------------------------------------------------------------------------- provenance over MCP (Q9)
# Design 10.1 step 3: over MCP the proposal and the application ask for sources (`require_sources=True`), so a plan that records none of the user's
# words, or has a criterion with no source, is a draft without a plan_id and cannot be applied. These tests run the real renderer, loader and
# applier (over memory) behind the tools.

EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"
USER_WORDS = "Keep it under 1500 words. Every claim needs a source."


def research_text(tmp_path: Path, criteria: Sequence[object], elicitation: str | None = USER_WORDS) -> str:
    """The shipped research blueprint with the given task criteria and (when given) the user's words."""
    bp = yaml.safe_load(EXAMPLE.read_text())
    bp["task"]["acceptance"] = list(criteria)
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    bp["needs"].pop("elicitation")
    if elicitation is not None:
        bp["needs"]["elicitation"] = elicitation
    return str(yaml.safe_dump(bp, sort_keys=False))


SOURCED = [{"text": "At most 1500 words as counted by read.", "from": "under 1500 words"}, {"text": "Cite 2 sources per claim.", "default": True}]


def real_proposal(tmp_path: Path) -> RenderedPlanProposal:
    return RenderedPlanProposal(lambda: loader_over_memory(tmp_path).loader, lambda: renderer_over_packaged_roles(tmp_path).renderer,
                                BindingPlanTarget(MemoryBinding(HERE, exists=True), lambda: agents_in()))


def test_over_mcp_a_string_criterion_is_criterion_source_and_the_plan_a_draft_without_plan_id(tmp_path: Path) -> None:
    out = real_proposal(tmp_path).propose(research_text(tmp_path, ["At most 1500 words as counted by read.", SOURCED[1]]))
    assert "DRAFT - NOT READY" in out and "plan_id: none" in out and "Show the block below" not in out
    assert "Errors (1):\n- task.acceptance[1]: criterion 1 does not say where it comes from" in out


def test_over_mcp_a_plan_without_elicitation_is_a_draft_without_plan_id(tmp_path: Path) -> None:
    out = real_proposal(tmp_path).propose(research_text(tmp_path, SOURCED, elicitation=None))
    assert "DRAFT - NOT READY" in out and "plan_id: none" in out
    assert "this plan records none of the user's words" in out
    sourced = real_proposal(tmp_path).propose(research_text(tmp_path, SOURCED))
    assert "DRAFT" not in sourced and "plan_id: none" not in sourced and "\nplan_id: " in sourced  # (control: the same plan with its words)


def test_apply_org_refuses_a_sourceless_plan_with_blueprint_has_errors(tmp_path: Path) -> None:
    applier = applier_over_memory_directories(tmp_path)
    group = ApprovedPlanApplication(InstructionText(MemoryBinding(HERE, exists=True)), lambda: loader_over_memory(tmp_path).loader, lambda: Identity(),
                                    lambda: applier.applier, lambda: FakeSchedulerStatus(SchedulerState("stopped")), lambda: OrgPaths(HERE))
    with pytest.raises(OrgError, match="blueprint has errors, nothing was created:") as refused:
        group.apply(research_text(tmp_path, ["At most 1500 words as counted by read."]), True, "abc123")
    assert "criterion 1 does not say where it comes from" in str(refused.value) and applier.log.of("hire") == []
    group.apply(research_text(tmp_path, SOURCED), True, "abc123")  # the same plan with its sources applies
    assert applier.log.of("hire") != []


def test_propose_org_docstring_gives_the_criteria_schema_and_requires_elicitation() -> None:
    group = BlueprintTools(TemplateExampleText(lambda: Examples(), EnvironmentExampleLocation(DictEnvironment(cwd=Path("/w")), MemoryBinding(HERE))),
                           RenderedPlanProposal(lambda: TextLoader(), lambda: Renderer(), BindingPlanTarget(MemoryBinding(HERE), lambda: agents_in())),
                           application())
    text = " ".join(described(serve(group, ROOT))["propose_org"].split())
    assert "acceptance items: {text, from: <the user's exact words in needs.elicitation>, asked} or {text, default: true}" in text
    assert "needs.elicitation: the user's answers, verbatim (required with criteria)" in text


def test_the_tools_ask_the_renderer_and_the_applier_for_sources() -> None:
    renderer, applier = Renderer(), Applier()
    RenderedPlanProposal(lambda: TextLoader(), lambda: renderer, BindingPlanTarget(MemoryBinding(HERE, exists=True), lambda: agents_in())).propose("bp")
    application(applier=applier).apply("bp", True, "abc123")
    assert renderer.sources == [True] and applier.sources == [True]


# ------------------------------------------------------------------------------------------------------------- propose_org(extend="current") and its apply (design 5, G1)

EXTEND_STALE = (
    "not applied: plan_id does not match this change against the organization as it is now (the blueprint, or something it names: an agent, a service, "
    "a limit or a schedule, changed since propose_org), so this is not the plan the user approved. Call propose_org(blueprint, extend=\"current\") again, "
    "show the new PLAN FOR YOU block, and apply only after their approval."
)


class HashPlanIdentity(PlanIdentity):
    """The id of a blueprint as the real identity makes it, in the one property these tests need: any change of the text changes it."""

    def plan_id(self, bp: Mapping[str, object]) -> str:
        return hashlib.sha256(json.dumps(bp, sort_keys=True, default=str).encode()).hexdigest()[:12]


EXTENSION = "reason: B1.1\nextend:\n  limits:\n    - {agent: lead, max_children: 3}\n"
FULL = "mission: m\nagents: []\n"


class ExtensionRenderer(Renderer):
    def propose_text(
        self, bp: Mapping[str, object], *, target: str = "", allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False,
    ) -> str:
        self.asked.append((bp, target))
        self.sources.append(require_sources)
        return f"EXTENSION PROPOSAL\n{target}\nplan_id: {HashPlanIdentity().plan_id(bp)}"


class ExtensionApplier(ExtensionApplying):
    """Applies an extension whose plan id is the hash of the blueprint, as the real applier does (it compares against the organization as it is now)."""

    def __init__(self) -> None:
        self.asked: list[tuple[Mapping[str, object], str | None, bool]] = []

    def apply(
        self, bp: Mapping[str, object], *, plan_id: str | None, require_sources: bool = False, allowed_roots: Sequence[str | Path] | None = None,
    ) -> str:
        self.asked.append((bp, plan_id, require_sources))
        if plan_id is not None and plan_id != HashPlanIdentity().plan_id(bp):
            raise BlueprintError(EXTEND_STALE)
        return f"applied the change {plan_id} to /memory/org\nNothing runs because of it."


def extension_proposal(exists: bool = True, renderer: Renderer | None = None) -> RenderedPlanProposal:
    return RenderedPlanProposal(lambda: loader_over_memory(HERE).loader, lambda: renderer or ExtensionRenderer(),
                                BindingPlanTarget(MemoryBinding(HERE, exists=exists), lambda: agents_in("lead", "lead/writer")))


def extension_application(exists: bool = True, applier: ExtensionApplier | None = None) -> ApprovedPlanApplication:
    applier = applier or ExtensionApplier()
    return ApprovedPlanApplication(
        InstructionText(MemoryBinding(HERE, exists=exists)), lambda: loader_over_memory(HERE).loader, lambda: HashPlanIdentity(), lambda: Applier(),
        lambda: FakeSchedulerStatus(SchedulerState("stopped")), lambda: OrgPaths(HERE), lambda: applier,
    )


def test_extend_current_proposes_the_change_plan_with_its_plan_id() -> None:
    renderer = ExtensionRenderer()
    out = extension_proposal(renderer=renderer).propose(EXTENSION, "current")
    assert out == f"EXTENSION PROPOSAL\nTarget organization: /memory/org (exists, 2 agent(s) besides root; this plan changes it)\nplan_id: {HashPlanIdentity().plan_id(renderer.asked[0][0])}"
    assert renderer.sources == [True]  # over MCP the criteria must declare their sources
    assert extension_proposal().propose(EXTENSION, str(HERE)).startswith("EXTENSION PROPOSAL")  # the bound path is the same as "current"


def test_an_extension_without_extend_is_extend_mode() -> None:
    with pytest.raises(OrgError) as info:
        extension_proposal().propose(EXTENSION)
    assert str(info.value) == 'refused: this blueprint changes an existing organization (it has extend:), so call propose_org(blueprint, extend="current").'


def test_extend_with_a_full_blueprint_is_extend_full() -> None:
    with pytest.raises(OrgError) as info:
        extension_proposal().propose(FULL, "current")
    assert str(info.value) == (
        'refused: extend="current" takes an extension blueprint (a top-level extend: with add_agents, add_services, add_charter_lines, remove_charter_lines, '
        "limits, budgets, schedules, retire_services or retire); a full blueprint builds a new team: call propose_org(blueprint) without extend."
    )


@pytest.mark.parametrize("target", ["somewhere", "/other/org", "", "Current"])
def test_extend_naming_another_path_is_extend_target(target: str) -> None:
    with pytest.raises(OrgError) as info:
        extension_proposal().propose("not even read: [", target)  # (the target is judged before the text is read)
    assert str(info.value) == 'refused: extend names the organization this server is bound to: "current" or /memory/org. Nothing was read.'


def test_extend_without_an_organization_is_extend_none() -> None:
    with pytest.raises(OrgError) as info:
        extension_proposal(exists=False).propose(EXTENSION, "current")
    assert str(info.value) == "refused: there is no organization yet, so there is nothing to extend: create_org(mission=...) and a full blueprint come first."


def test_an_extension_applies_only_with_approved_and_a_fresh_plan_id() -> None:
    applier = ExtensionApplier()
    bp = loader_over_memory(HERE).loader.load_text(EXTENSION)
    fresh = HashPlanIdentity().plan_id(bp)
    with pytest.raises(OrgError, match="^not applied: the user must approve the plan first"):
        extension_application(applier=applier).apply(EXTENSION, False, fresh)
    for missing in (None, ""):
        with pytest.raises(OrgError, match="^not applied: plan_id is missing, so this is not the plan the user approved"):
            extension_application(applier=applier).apply(EXTENSION, True, missing)
    with pytest.raises(OrgError, match="^not applied: there is no organization yet"):
        extension_application(exists=False, applier=applier).apply(EXTENSION, True, fresh)
    assert applier.asked == []  # none of the three got as far as the applier
    assert extension_application(applier=applier).apply(EXTENSION, True, f" {fresh} ") == f"applied the change {fresh} to /memory/org\nNothing runs because of it."
    assert [(plan_id, sources) for _, plan_id, sources in applier.asked] == [(fresh, True)]


def test_a_stale_extension_is_refused_with_extend_stale_not_todays_text() -> None:
    with pytest.raises(OrgError) as info:
        extension_application().apply(EXTENSION, True, "000000000000")
    assert str(info.value) == EXTEND_STALE and "plan_id does not match this blueprint" not in str(info.value)
    assert "before/now" not in str(info.value) and "->" not in str(info.value)  # the id is a hash: it cannot say what changed


def test_an_edited_extension_blueprint_is_extend_stale_too() -> None:
    bp = loader_over_memory(HERE).loader.load_text(EXTENSION)
    fresh = HashPlanIdentity().plan_id(bp)
    with pytest.raises(OrgError) as info:
        extension_application().apply(EXTENSION.replace("max_children: 3", "max_children: 4"), True, fresh)
    assert str(info.value) == EXTEND_STALE


def test_the_target_line_of_an_extension_says_this_plan_changes_it() -> None:
    target = BindingPlanTarget(MemoryBinding(HERE, exists=True), lambda: agents_in("lead"))
    assert target.line(extending=True) == "Target organization: /memory/org (exists, 1 agent(s) besides root; this plan changes it)"
    assert target.line() == "Target organization: /memory/org (exists, 1 agent(s) besides root; apply_org adds to it)"
    assert target.bound() == HERE and BindingPlanTarget(MemoryBinding(HERE), lambda: agents_in()).bound() is None


def test_the_docstrings_name_extend_and_the_stale_rule() -> None:
    group = BlueprintTools(TemplateExampleText(lambda: Examples(), EnvironmentExampleLocation(DictEnvironment(cwd=Path("/w")), MemoryBinding(HERE))),
                           extension_proposal(), extension_application())
    docs = described(serve(group, ROOT))
    assert 'extend: "current" to change the organization this server is bound to: blueprint is then an extension' in docs["propose_org"]
    assert "its plan_id holds only while nothing it touches changes" in " ".join(docs["propose_org"].split())
    assert "An extension (extend:) changes the existing organization: refused when anything it touches changed since propose_org." in " ".join(docs["apply_org"].split())


def test_the_tools_pass_extend_and_the_plan_id_through() -> None:
    applier = ExtensionApplier()
    group = BlueprintTools(TemplateExampleText(lambda: Examples(), EnvironmentExampleLocation(DictEnvironment(cwd=Path("/w")), MemoryBinding(HERE))),
                           extension_proposal(), extension_application(applier=applier))
    server = serve(group, ROOT)
    assert call(server, "propose_org", blueprint=EXTENSION, extend="current").startswith("EXTENSION PROPOSAL")
    assert "this blueprint changes an existing organization" in fails(server, "propose_org", blueprint=EXTENSION)
    fresh = HashPlanIdentity().plan_id(loader_over_memory(HERE).loader.load_text(EXTENSION))
    assert call(server, "apply_org", blueprint=EXTENSION, approved=True, plan_id=fresh).startswith(f"applied the change {fresh}")


def test_a_full_blueprint_keeps_todays_plan_id_refusal() -> None:
    with pytest.raises(OrgError) as info:
        extension_application().apply(FULL, True, "zzz")
    assert str(info.value) == ("not applied: plan_id does not match this blueprint, so this is not the plan the user approved. Call propose_org(blueprint), "
                               "show the PLAN FOR YOU block to the user, get their explicit approval, then call apply_org(blueprint, approved=True, "
                               "plan_id=<the plan_id from that propose_org>) with the same blueprint")


def test_blueprint_example_offers_kind_extension() -> None:
    group = BlueprintTools(TemplateExampleText(lambda: Examples(), EnvironmentExampleLocation(DictEnvironment(cwd=Path("/w")), MemoryBinding(HERE))),
                           extension_proposal(), extension_application())
    server = serve(group, ROOT)
    text = " ".join(described(server)["blueprint_example"].split())
    assert '"extension" (a change to the existing organization: new agents, services, lines in a charter, limits, budgets, retires;' in text
    assert 'the template of the extension that propose_org(blueprint, extend="current") takes, with every field explained)' in text
    assert call(server, "blueprint_example", kind="extension") == "EXAMPLE extension /w False"
