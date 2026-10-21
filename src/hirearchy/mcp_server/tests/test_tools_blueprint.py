"""The way to an organization: the example, the proposal and the application of a blueprint, over scripted ports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from hirearchy.blueprint import BlueprintApplier, BlueprintExamples, BlueprintLoader, PlanIdentity, PlanRenderer, Summary
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

    def render_plan(self, bp, issues=None, *, allowed_roots=None) -> str:  # type: ignore[no-untyped-def]
        return "plan"

    def plan_for_user(self, bp, issues=None, *, allowed_roots=None) -> str:  # type: ignore[no-untyped-def]
        return "for user"

    def propose_text(self, bp: Mapping[str, object], *, target: str = "", allowed_roots: Sequence[str | Path] | None = None) -> str:
        self.asked.append((bp, target))
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

    def apply(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None) -> Summary:
        self.applied.append(bp)
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
