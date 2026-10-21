"""``wire_services``: the runtime has the five services ports and the rework context of ``dispatch``, built from the agents, settings, mailboxes,
sender, delivery, clock, event sink, layout and atomic writer of the runtime - so a test that overrides them runs the rules over its own fakes."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents import AgentDirectory
from hirearchy.app import Org, wire_dispatch, wire_services, wiring
from hirearchy.delivery import MessageDelivery
from hirearchy.delivery.testing import RecordingDelivery
from hirearchy.dispatch import MessageSender, ReworkContext
from hirearchy.dispatch.testing import FixedReworkContext
from hirearchy.kernel import EventSink, Message, OrgError, OrgPaths
from hirearchy.kernel.testing import FakeClock, ListEventSink, SequenceIdGenerator
from hirearchy.mail import MailboxReader
from hirearchy.mail.testing import MemoryMailbox
from hirearchy.services import ContractNormalizer, ServiceCatalog, ServiceCommands, ServiceHints, ServiceStore
from hirearchy.services._catalog import ContractServiceCatalog
from hirearchy.services._commands import RuleServiceCommands
from hirearchy.services._hints import ServiceReportHints
from hirearchy.services._normalizer import TextContractNormalizer
from hirearchy.services._places import OrgServicePlaces
from hirearchy.services._rework import ServiceReworkContext
from hirearchy.services._store import FsServiceStore
from hirearchy.services.testing import MemoryServiceStore
from hirearchy.settings import OrgSettings
from hirearchy.settings.testing import MemoryOrgSettings

CHARTER = "---\nrole: R\ncan_hire: true\n---\nx\n"
BRIEF = dict(
    description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}], acceptance=["Short"],
    deliverable={"description": "one file"}, budget=4,
)


def test_the_runtime_has_the_services_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.service_store, FsServiceStore) and isinstance(runtime.service_store, ServiceStore)
    assert isinstance(runtime.service_catalog, ContractServiceCatalog) and isinstance(runtime.service_catalog, ServiceCatalog)
    assert isinstance(runtime.service_commands, RuleServiceCommands) and isinstance(runtime.service_commands, ServiceCommands)
    assert isinstance(runtime.service_hints, ServiceReportHints) and isinstance(runtime.service_hints, ServiceHints)
    assert isinstance(runtime.contract_normalizer, TextContractNormalizer) and isinstance(runtime.contract_normalizer, ContractNormalizer)


def test_the_port_of_dispatch_that_services_implements_is_provided_by_services(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.rework_context, ServiceReworkContext) and isinstance(runtime.rework_context, ReworkContext)
    assert not hasattr(wire_dispatch, "LegacyReworkContext") and not hasattr(wire_dispatch, "legacy_rework_context")
    assert hasattr(wire_services, "register")


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.service_store is not None and runtime.service_catalog is not None and runtime.service_commands is not None
    assert runtime.service_hints is not None and runtime.contract_normalizer is not None and runtime.rework_context is not None
    assert list(tmp_path.iterdir()) == []


def test_every_runtime_has_its_own_ports(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).service_commands is not wiring.open_runtime(tmp_path).service_commands
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.service_commands is runtime.service_commands


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    fake = memory_store(tmp_path)
    runtime = wiring.open_runtime(tmp_path, {ServiceStore: fake})
    assert runtime.service_store is fake
    assert wiring.open_runtime(tmp_path, {ReworkContext: FixedReworkContext({})}).rework_context is not None


def memory_store(root: Path) -> MemoryServiceStore:
    return MemoryServiceStore(OrgServicePlaces(OrgPaths(root)))


def test_the_catalog_reads_through_the_store_of_the_runtime(tmp_path: Path) -> None:
    store = memory_store(tmp_path)
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    runtime = wiring.open_runtime(tmp_path, {ServiceStore: store, AgentDirectory: box.agents, MailboxReader: box})
    store.write_contract("ceo", "brief", {"name": "brief", "description": "D", "budget": 3, "version": 1}, "", None)
    assert runtime.service_catalog.service_names("ceo") == ["brief"]
    contract = runtime.service_catalog.read_contract("ceo", "brief")
    assert contract is not None and contract.budget == 3
    assert [c.name for c in runtime.service_catalog.requestable_services("root")] == ["brief"]


def test_the_commands_use_the_sender_the_delivery_and_the_events_of_the_runtime(tmp_path: Path) -> None:
    clock = FakeClock()
    delivery = RecordingDelivery(clock, SequenceIdGenerator(clock))
    events = ListEventSink()
    sent: list[tuple[str, str, str]] = []

    class Sender(MessageSender):
        def send(self, actor: str, to: str, body: str, **kw: object) -> Message:
            sent.append((actor, to, str(kw["type"])))
            return Message(sender=actor, to=to, type="task", body=body, id="T1", title="T")

    store = memory_store(tmp_path)
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    runtime = wiring.open_runtime(
        tmp_path, {
            ServiceStore: store, AgentDirectory: box.agents, MailboxReader: box, MessageDelivery: delivery, EventSink: events, MessageSender: Sender(),
            OrgSettings: MemoryOrgSettings("---\nmission: m\n---\nrules\n"),
        },
    )
    runtime.service_commands.define_service("root", "ceo", "brief", **BRIEF)  # type: ignore[arg-type]
    runtime.service_commands.define_service("root", "ceo", "brief", budget=5)
    assert [e.kind for e in events.events] == ["service.define", "service.define"]  # the sink of the runtime
    assert [m.title for m in delivery.messages] == ["contract of service brief changed to v2"]  # the delivery of the runtime (a quiet note)
    runtime.service_commands.request("root", "brief", {"topic": "ai"})
    assert sent == [("root", "ceo", "task")]  # the sender of the runtime


def test_the_cap_of_the_playbook_is_that_of_the_settings_of_the_runtime(tmp_path: Path) -> None:
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    runtime = wiring.open_runtime(
        tmp_path, {AgentDirectory: box.agents, MailboxReader: box, OrgSettings: MemoryOrgSettings("---\nplaybook_max_words: 2\n---\nrules\n")},
    )
    with pytest.raises(OrgError, match="the limit is 2 \\(playbook_max_words\\)"):
        runtime.service_commands.define_service("root", "ceo", "brief", playbook="one two three", **BRIEF)  # type: ignore[arg-type]


def test_the_rework_context_of_the_runtime_asks_the_catalog_of_the_runtime(tmp_path: Path) -> None:
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", CHARTER)
    store = memory_store(tmp_path)
    store.write_playbook("ceo", "brief", 3, {"version": 3}, "Steps.")
    box.store(Message(sender="root", to="ceo", type="task", body="b", title="T", id="20260101T000000000001-root-aaaa", service="brief", contract=2))
    runtime = wiring.open_runtime(tmp_path, {ServiceStore: store, AgentDirectory: box.agents, MailboxReader: box})
    assert dict(runtime.rework_context.fields_for("root", "20260101T000000000001-root-aaaa")) == {"service": "brief", "contract": 2, "playbook": 3}


# ------------------------------------------------------------------------------------------------------------ the rework fields


def test_over_a_real_organization_a_service_request_gives_its_service_fields(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Chief", "Run it.", can_hire=True)
    org.define_service("root", "ceo", "weekly-brief", playbook="Steps.", **BRIEF)  # type: ignore[arg-type]
    request = org.request("root", "weekly-brief", {"topic": "ai"})
    plain = org.delegate("root", "ceo", "Other", "g", "a", budget=2)
    context = wiring.open_runtime(org.root).rework_context
    assert dict(context.fields_for("root", request.id)) == {"service": "weekly-brief", "contract": 1, "playbook": 1}
    assert dict(context.fields_for("root", plain.id)) == {} and dict(context.fields_for("root", "nope")) == {}


def test_a_rework_of_a_service_request_keeps_the_service_fields_through_the_assigner(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Chief", "Run it.", can_hire=True)
    org.define_service("root", "ceo", "weekly-brief", **BRIEF)  # type: ignore[arg-type]
    request = org.request("root", "weekly-brief", {"topic": "ai"})
    again = org.delegate("root", "ceo", "Again", "g", "a", budget=2, revises=request.id)
    assert (again.service, again.contract, again.playbook, again.revises) == ("weekly-brief", 1, 0, request.id)
