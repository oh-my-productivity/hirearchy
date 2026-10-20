"""``wire_dispatch``: the runtime has the four dispatch ports, built from the agents, settings, mailboxes, delivery, allocation policy, templates and
access of the runtime; the rework fields come from ``services``, which implements the port (``wire_services``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory
from orgmcp.app import Org, wiring
from orgmcp.budget import AllocationPolicy
from orgmcp.delivery import MessageDelivery
from orgmcp.delivery.testing import RecordingDelivery
from orgmcp.dispatch import ArtifactNormalizer, HopCounter, MessageSender, ReworkContext, RoutePolicy, TaskAssigner, TaskReporter
from orgmcp.dispatch._artifacts import ArtifactAnnotator
from orgmcp.dispatch._hops import InflightHopCounter
from orgmcp.dispatch._routes import ParentSiblingRoutePolicy
from orgmcp.dispatch._assigner import RuleTaskAssigner
from orgmcp.dispatch._reporter import RuleTaskReporter
from orgmcp.dispatch._sender import RuleMessageSender
from orgmcp.dispatch.testing import FixedReworkContext
from orgmcp.kernel import Message, OrgError
from orgmcp.kernel.testing import FakeClock, SequenceIdGenerator
from orgmcp.mail import MailboxReader, TaskQuery
from orgmcp.mail._tasks import DerivedTaskQuery
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.settings import OrgSettings
from orgmcp.services._rework import ServiceReworkContext
from orgmcp.settings.testing import MemoryOrgSettings

CHARTER = "---\nrole: R\ncan_hire: true\n---\nx\n"


def test_the_runtime_has_the_four_dispatch_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.message_sender, RuleMessageSender) and isinstance(runtime.message_sender, MessageSender)
    assert isinstance(runtime.task_assigner, RuleTaskAssigner) and isinstance(runtime.task_assigner, TaskAssigner)
    assert isinstance(runtime.task_reporter, RuleTaskReporter) and isinstance(runtime.task_reporter, TaskReporter)
    assert isinstance(runtime.rework_context, ServiceReworkContext) and isinstance(runtime.rework_context, ReworkContext)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.message_sender is not None and runtime.task_assigner is not None and runtime.task_reporter is not None
    assert runtime.rework_context is not None
    assert list(tmp_path.iterdir()) == []


def test_every_collaborator_comes_from_the_runtime(tmp_path: Path) -> None:
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    box.agents.put("ceo/eng/AGENT.md", "---\nrole: R\n---\nx\n")
    clock = FakeClock()
    delivery = RecordingDelivery(clock, SequenceIdGenerator(clock))
    settings = MemoryOrgSettings("---\nmax_message_chars: 20\n---\nrules\n")

    class Policy(AllocationPolicy):
        def check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
            if amount > 2:
                raise OrgError("the fake policy allows 2")

        def default_budget(self, actor: str) -> int:
            return 2

        def budget_to_return(self, actor: str, task: Message, status: str) -> int:
            return 1

    overrides: dict[type, object] = {
        MailboxReader: box, TaskQuery: DerivedTaskQuery(box), AgentDirectory: box.agents, OrgSettings: settings, MessageDelivery: delivery,
        AllocationPolicy: Policy(),
    }
    runtime = wiring.open_runtime(tmp_path, overrides)
    task = runtime.task_assigner.delegate("root", "ceo", "Work", "Do it.", "Done when it is.")
    assert task.budget == 2 and delivery.messages == [task]  # the default of the fake policy, delivered by the fake delivery
    with pytest.raises(OrgError, match="the limit is 20"):  # the cap of the fake settings
        runtime.message_sender.send("ceo", "ceo/eng", "x" * 21)
    with pytest.raises(OrgError, match="the fake policy allows 2"):
        runtime.message_sender.send("ceo", "ceo/eng", "runs", budget=3)
    box.store(task)
    result = runtime.task_reporter.report("ceo", task.id, "done", "Done.")
    assert (result.budget, result.to, result.supersedes) == (1, "root", None) and delivery.messages[-1] is result


def test_the_sender_is_the_one_the_assigner_and_the_reporter_use(tmp_path: Path) -> None:
    class Spy(MessageSender):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def send(self, actor: str, to: str, body: str, **kw: object) -> Message:
            self.calls.append(str(kw["type"]))
            return Message(sender=actor, to=to, type="task", body=body, id="T1", created="2026-01-01T00:00:00+00:00", title="T")

    spy = Spy()
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    runtime = wiring.open_runtime(tmp_path, {MessageSender: spy, MailboxReader: box, TaskQuery: DerivedTaskQuery(box), AgentDirectory: box.agents})
    runtime.task_assigner.delegate("root", "ceo", "T", "g", "a", budget=1)
    box.store(Message(sender="root", to="ceo", type="task", body="b", title="T", id="20260101T000000000001-root-aaaa"))
    runtime.task_reporter.report("ceo", "20260101T000000000001-root-aaaa", "done", "ok")
    assert spy.calls == ["task", "result"]


def test_an_override_replaces_the_rework_context(tmp_path: Path) -> None:
    fake = FixedReworkContext({})
    assert wiring.open_runtime(tmp_path, {ReworkContext: fake}).rework_context is fake


def test_every_runtime_has_its_own_ports(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).message_sender is not wiring.open_runtime(tmp_path).message_sender


# ------------------------------------------------------------------------------------------------------------ the rework fields


def test_over_a_real_organization_a_service_request_gives_its_service_fields(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Chief", "Run it.", can_hire=True)
    org.define_service(
        "root", "ceo", "weekly-brief", description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}],
        acceptance=["Short"], deliverable={"description": "one file"}, budget=4, playbook="Steps.",
    )
    request = org.request("root", "weekly-brief", {"topic": "ai"})
    plain = org.delegate("root", "ceo", "Other", "g", "a", budget=2)
    context = wiring.open_runtime(org.root).rework_context
    assert dict(context.fields_for("root", request.id)) == {"service": "weekly-brief", "contract": 1, "playbook": 1}
    assert dict(context.fields_for("root", plain.id)) == {} and dict(context.fields_for("root", "nope")) == {}


def test_the_runtime_hands_out_the_rules_the_commands_are_made_of(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.route_policy, ParentSiblingRoutePolicy) and isinstance(runtime.route_policy, RoutePolicy)
    assert isinstance(runtime.hop_counter, InflightHopCounter) and isinstance(runtime.hop_counter, HopCounter)
    assert isinstance(runtime.artifact_normalizer, ArtifactAnnotator) and isinstance(runtime.artifact_normalizer, ArtifactNormalizer)


def test_the_sender_uses_the_route_policy_and_the_hop_counter_of_the_runtime(tmp_path: Path) -> None:
    class Never(RoutePolicy):
        def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
            return False

    class Hops(HopCounter):
        def next_hops(self, actor: str) -> int:
            return 99

    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    box.agents.put("ceo/eng/AGENT.md", "---\nrole: R\n---\nx\n")
    clock = FakeClock()
    common: dict[type, object] = {
        MailboxReader: box, AgentDirectory: box.agents, OrgSettings: MemoryOrgSettings("---\nmax_hops: 5\n---\nrules\n"),
        MessageDelivery: RecordingDelivery(clock, SequenceIdGenerator(clock)),
    }
    runtime = wiring.open_runtime(tmp_path, {**common, RoutePolicy: Never()})
    with pytest.raises(OrgError, match="ceo cannot message ceo/eng"):
        runtime.message_sender.send("ceo", "ceo/eng", "hello")
    runtime = wiring.open_runtime(tmp_path, {**common, HopCounter: Hops()})
    with pytest.raises(OrgError, match="hop"):
        runtime.message_sender.send("ceo", "ceo/eng", "hello")
