"""An extension that fails midway is taken back write by write (design 5.5, the undo table), or is partly applied when a retire fails."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from testkit.reach.hirearchy.app import wiring
from testkit.reach.hirearchy.core import ROOT, OrgError

from hirearchy.agents import AgentRegistry
from hirearchy.blueprint import BlueprintError
from hirearchy.blueprint.testing import FlakyHiring, FlakyServiceCommands
from hirearchy.hierarchy import Retired, Retirement
from hirearchy.kernel.testing import ListEventSink
from hirearchy.kernel import EventSink
from hirearchy.services import ServiceCommands
from hirearchy.settings import OrgLimits

from ._extension_world import World, extension, world

CRITERIA = ["Every row has a date.", "At most 3 pages."]


class FlakyRegistry(AgentRegistry):
    """The agent registry whose ``fail_on``-th charter rewrite fails (1-based); everything else is the real one."""

    def __init__(self, inner: AgentRegistry, fail_on: int) -> None:
        self._inner = inner
        self._left = fail_on

    def create(self, addr: str, meta: object, charter_text: str) -> None:
        self._inner.create(addr, meta, charter_text)  # type: ignore[arg-type]

    def rewrite_charter(self, addr: str, text: str) -> None:
        self._left -= 1
        if self._left == 0:
            raise OrgError("disk full")
        self._inner.rewrite_charter(addr, text)

    def archive(self, addr: str, stamp: str, record: object = None) -> str:
        return self._inner.archive(addr, stamp, record)  # type: ignore[arg-type]


class FlakyLimits(OrgLimits):
    def set_max_depth(self, value: int) -> int:
        raise OrgError("disk full")


class FlakyRetirement(Retirement):
    """A retirement that refuses the agent ``name`` and does the others through ``inner``."""

    def __init__(self, inner: Retirement, name: str) -> None:
        self._inner = inner
        self._name = name

    def retire(self, actor: str, name: str, reason: str) -> str:
        return self._inner.retire(actor, name, reason)

    def retire_team(self, actor: str, name: str, reason: str, approved_in: str = "") -> Retired:
        if name == self._name:
            raise OrgError("disk full")
        return self._inner.retire_team(actor, name, reason, approved_in)


@pytest.fixture
def w(tmp_path: Path) -> World:
    made = world(tmp_path)
    made.org.hire("lead", "second", "Second", "x", tools=["read"])
    for name in ("weekly", "daily"):
        made.org.define_service(ROOT, "lead", name, description=f"A {name} note", inputs=[], acceptance=CRITERIA, deliverable={"description": "a note"}, budget=9, playbook="steps")
    made.org.hire(ROOT, "old", "Old", "x", tools=["read"])
    return made


def everything() -> dict[str, object]:
    """Every kind of write of steps 3 to 5, in the order the applier makes them."""
    return extension(
        limits=[{"agent": "lead", "max_children": 3}, {"org": "max_depth", "value": 5}],
        add_agents=[{"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"], "charter_extra": "Check every date."}],
        add_services=[{"owner": "solo", "name": "monthly", "description": "A monthly note", "acceptance": [{"text": "Every row has a date.", "default": True}],
                       "deliverable": {"description": "a note", "format": "markdown"}}],
        add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}],
        budgets=[{"owner": "lead", "service": "weekly", "budget": 20}, {"owner": "lead", "service": "daily", "budget": 20}],
        retire=[{"agent": "old", "reason": "no longer needed"}],
    ) | {"needs": {"elicitation": "Monthly notes, please."}}


def state(w: World) -> tuple[Any, ...]:
    """What the writes of an extension change, as the files show it (the retired trees are what stays visible: see ``taken_back``)."""
    org = w.org
    contracts = {(o, n): org.runtime.service_catalog.read_contract(o, n) for o in ("lead", "solo") for n in org.service_names(o)}
    return (
        sorted(org.agents()), {a: org.charter(a) for a in org.agents()}, org.runtime.settings.read_raw(),
        {k: (c.version, c.budget) for k, c in contracts.items() if c is not None},
    )


def run(w: World, bp: dict[str, object], ports: dict[type, object]) -> tuple[BlueprintError, ListEventSink]:
    events = ListEventSink()
    runtime = wiring.open_runtime(w.org.root, {EventSink: events, **ports})
    with pytest.raises(BlueprintError) as raised:
        runtime.extension_applier.apply(bp, plan_id=None, allowed_roots=[w.tmp])
    return raised.value, events


def injections(w: World) -> list[tuple[str, dict[type, object]]]:
    rt = w.org.runtime
    return [
        ("a limits rewrite", {AgentRegistry: FlakyRegistry(rt.agent_registry, 1)}),
        ("max_depth", {OrgLimits: FlakyLimits()}),
        ("a new agent", {_hiring(): FlakyHiring(rt.hiring, fail_on=1)}),
        ("a new service", {ServiceCommands: FlakyServiceCommands(rt.service_commands, fail_define_on=1)}),
        ("an added line", {AgentRegistry: FlakyRegistry(rt.agent_registry, 3)}),
        ("a budget amendment", {ServiceCommands: FlakyServiceCommands(rt.service_commands, fail_define_on=3)}),
    ]


def _hiring() -> type:
    from hirearchy.hierarchy import Hiring

    return Hiring


@pytest.mark.parametrize("index", range(6))
def test_a_failure_at_each_write_takes_back_everything_before_it(w: World, index: int) -> None:
    label, ports = injections(w)[index]
    before = state(w)
    error, events = run(w, everything(), ports)
    assert str(error).startswith("not applied: disk full. Everything this change wrote was taken back."), label
    assert state(w) == before if index != 5 else state(w)[:3] == before[:3]  # a budget amendment leaves its two versions: the budget is back (below)
    assert {k: v[1] for k, v in state(w)[3].items()} == {k: v[1] for k, v in before[3].items()}
    assert [e.kind for e in events.events if e.kind.startswith("extension.")] == ["extension.rolled_back"]
    assert not any(e.kind == "team_note.failed" for e in events.events) and "old" in w.org.agents()  # the retires come after: none ran


def test_a_taken_back_agent_and_service_carry_approved_in_not_applied(w: World) -> None:
    bp = everything()
    pid = str(w.org.runtime.plan_identity.plan_id(bp))
    run(w, bp, {ServiceCommands: FlakyServiceCommands(w.org.runtime.service_commands, fail_define_on=3)})
    (tree,) = w.org.runtime.retired_archive.trees()
    record = w.org.runtime.retired_archive.record(tree)
    assert tree.addr == "lead/checker" and record["approved_in"] == f"change {pid} (not applied)" and record["by"] == ROOT
    assert record["reason"] == f"the change {pid} was not applied"
    copies = list((w.org.root / "solo" / "services" / ".retired").glob("monthly-*/RETIRED.md"))
    assert len(copies) == 1 and f"approved_in: change {pid} (not applied)" in copies[0].read_text(encoding="utf-8")


def test_a_taken_back_budget_names_versions_n1_and_n2(w: World) -> None:
    error, _ = run(w, everything(), {ServiceCommands: FlakyServiceCommands(w.org.runtime.service_commands, fail_define_on=3)})
    assert str(error) == (
        "not applied: disk full. Everything this change wrote was taken back.; weekly has versions v2 and v3 (the budget went back to 9)"
    )
    contract = w.org.runtime.service_catalog.read_contract("lead", "weekly")
    assert contract is not None and (contract.version, contract.budget) == (3, 9)
    assert sorted(p.name for p in (w.org.root / "lead" / "services" / "weekly" / "history").glob("SERVICE.v*.md")) == ["SERVICE.v1.md", "SERVICE.v2.md"]


def test_a_failure_in_the_retires_is_partly_applied_with_its_text(w: World) -> None:
    bp = extension(
        add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}],
        retire_services=[{"owner": "lead", "service": "daily", "reason": "unused"}], retire=[{"agent": "old", "reason": "no longer needed"}],
    )
    error, events = run(w, bp, {Retirement: FlakyRetirement(w.org.runtime.retirement, "old")})
    assert str(error) == (
        "partly applied: service daily of lead retired; old failed (disk full); everything before the retires was applied. Tell the user."
    )
    assert "Cite the source." in w.org.charter("lead/writer")[1] and w.org.runtime.service_catalog.read_contract("lead", "daily") is None and "old" in w.org.agents()
    assert [(e.kind, e.fields["failed"], e.fields["done"]) for e in events.events if e.kind == "extension.partial"] == [("extension.partial", "old", ["service daily of lead"])]


def test_a_retire_that_fails_before_any_retire_took_place_takes_everything_back(w: World) -> None:
    bp = extension(add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}], retire=[{"agent": "old", "reason": "no longer needed"}])
    before = state(w)
    error, events = run(w, bp, {Retirement: FlakyRetirement(w.org.runtime.retirement, "old")})
    assert str(error).startswith("not applied: disk full. Everything this change wrote was taken back.") and state(w) == before
    assert [e.kind for e in events.events if e.kind.startswith("extension.")] == ["extension.rolled_back"]


def test_extension_rolled_back_and_extension_partial_are_emitted(w: World) -> None:
    bp = everything()
    pid = str(w.org.runtime.plan_identity.plan_id(bp))
    _, events = run(w, bp, {OrgLimits: FlakyLimits()})
    (rolled,) = [e for e in events.events if e.kind == "extension.rolled_back"]
    assert (rolled.actor, rolled.fields["plan_id"], rolled.fields["step"], rolled.fields["error"]) == (ROOT, pid, "max_depth", "disk full")
