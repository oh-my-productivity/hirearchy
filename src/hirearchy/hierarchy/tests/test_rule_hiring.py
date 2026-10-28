"""``RuleHiring`` against spies: which collaborator is asked what, in which order, and what the registry is given.

The contract suite (``test_contract_hiring.py``) pins what a caller sees; this file pins the order of the rules and the injection of every
collaborator (the clock, the model resolver, the authority policy, the templates)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.access import AccessScopes, AuthorityPolicy, ModelResolver
from hirearchy.agents import AgentRegistry
from hirearchy.agents.testing import MemoryAgents
from hirearchy.hierarchy import Hiring
from hirearchy.hierarchy._hiring import RuleHiring
from hirearchy.hierarchy.testing import MemoryAgentSlots
from hirearchy.kernel import OrgError, join_frontmatter
from hirearchy.kernel.testing import FakeClock, ListEventSink
from hirearchy.settings.testing import MemoryOrgSettings
from hirearchy.templates import DocumentTemplates

CHIEF = {"role": "Chief", "tools": ["read"], "can_hire": True, "max_children": 2, "inputs": ["/data"]}


class Calls:
    """The order in which the spies were asked."""

    def __init__(self) -> None:
        self.log: list[str] = []


class SpyRegistry(AgentRegistry):
    def __init__(self, calls: Calls, files: MemoryAgents) -> None:
        self.calls = calls
        self.files = files
        self.created: list[tuple[str, dict[str, object], str]] = []

    def create(self, addr: str, meta: Mapping[str, object], charter_text: str) -> None:
        self.calls.log.append("create")
        self.created.append((addr, dict(meta), charter_text))
        self.files.create(addr, meta, charter_text)

    def rewrite_charter(self, addr: str, text: str) -> None:
        raise AssertionError("hiring never rewrites a charter")

    def archive(self, addr: str, stamp: str) -> str:
        raise AssertionError("hiring never archives")


class SpyAuthority(AuthorityPolicy):
    def __init__(self, calls: Calls) -> None:
        self.calls = calls
        self.checked: list[tuple[str, tuple[str, ...], str | None, list[str] | None]] = []
        self.grants: list[tuple[str, bool, int | None]] = []

    def check_authority(self, actor: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str] | None = None) -> None:
        self.calls.log.append("authority")
        self.checked.append((actor, tuple(tools), workspace, None if inputs is None else list(inputs)))

    def check_inputs(self, inputs: object) -> list[str]:
        self.calls.log.append("inputs")
        return ["/checked"] if inputs else []

    def check_grant(self, actor: str, *, grants_hire: bool, max_children: int | None) -> None:
        self.calls.log.append("grant")
        self.grants.append((actor, grants_hire, max_children))


class FixedScopes(AccessScopes):
    def __init__(self, unconfined: bool) -> None:
        self.unconfined = unconfined

    def workspace_of(self, addr: str) -> None:
        raise AssertionError("not asked")

    def inputs_of(self, addr: str) -> list[Path]:
        raise AssertionError("not asked")

    def readable_roots(self, addr: str) -> list[Path]:
        raise AssertionError("not asked")

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        return self.unconfined


class FixedModel(ModelResolver):
    def __init__(self, calls: Calls, files: MemoryAgents) -> None:
        self.calls = calls
        self.files = files
        self.seen_agent_exists: list[bool] = []

    def default_model(self) -> str:
        raise AssertionError("not asked")

    def model_for(self, addr: str) -> str:
        self.calls.log.append("model")
        self.seen_agent_exists.append(self.files.exists(addr))
        return f"model-of-{addr}"

    def effort(self) -> str:
        raise AssertionError("not asked")


class ShoutingTemplates(DocumentTemplates):
    def org_rules(self, mission: str | None) -> str:
        raise AssertionError("not asked")

    def charter_body(self, role: str, charter: str) -> str:
        return f"BODY[{role}|{charter}]"

    def task_body(self, goal: str, acceptance: str, inputs: Sequence[str]) -> str:
        raise AssertionError("not asked")

    def result_body(self, summary: str, artifacts: Sequence[str], lessons: str = "") -> str:
        raise AssertionError("not asked")


class Rig:
    def __init__(self, *, unconfined: bool = False, org_md: str = "---\nmax_depth: 3\n---\nr\n") -> None:
        self.calls = Calls()
        self.files = MemoryAgents()
        self.files.put("ceo/AGENT.md", join_frontmatter(dict(CHIEF), "# Role\n"))
        self.registry = SpyRegistry(self.calls, self.files)
        self.authority = SpyAuthority(self.calls)
        self.model = FixedModel(self.calls, self.files)
        self.events = ListEventSink()
        self.clock = FakeClock(datetime(2030, 5, 6, 7, 8, 9, tzinfo=timezone.utc))
        self.hiring: Hiring = RuleHiring(
            self.files, self.files, self.registry, MemoryAgentSlots(self.files), MemoryOrgSettings(org_md), ShoutingTemplates(),
            FixedScopes(unconfined), self.authority, self.model, self.clock, self.events,
        )


def test_the_registry_is_given_the_address_the_meta_in_its_order_and_the_body_of_the_templates() -> None:
    rig = Rig()
    rig.hiring.hire("ceo", "eng", " Engineer ", "Build.", model="claude-opus-5.5", tools=["b", "a", "b"], can_hire=True, max_children=3, workspace="/ws", inputs=["/in"])
    ((addr, meta, text),) = rig.registry.created
    assert addr == "ceo/eng" and text == "BODY[ Engineer |Build.]"
    assert list(meta) == ["role", "model", "tools", "can_hire", "max_children", "workspace", "inputs", "hired_by", "created"]
    assert meta == {
        "role": "Engineer", "model": "claude-opus-5.5", "tools": ["a", "b"], "can_hire": True, "max_children": 3, "workspace": "/ws",
        "inputs": ["/checked"], "hired_by": "ceo", "created": "2030-05-06T07:08:09+00:00",
    }


def test_what_is_not_given_is_left_out_of_the_meta() -> None:
    rig = Rig()
    rig.hiring.hire("root", "eng", "E", "c")
    ((_, meta, _),) = rig.registry.created
    assert list(meta) == ["role", "tools", "can_hire", "max_children", "hired_by", "created"]


def test_kind_and_approved_in_are_written_when_given() -> None:
    rig = Rig()
    rig.hiring.hire("root", "eng", "E", "c", kind="verifier", approved_in="plan 0123456789ab")
    ((_, meta, _),) = rig.registry.created
    assert list(meta) == ["role", "tools", "can_hire", "max_children", "hired_by", "created", "kind", "approved_in"]
    assert (meta["kind"], meta["approved_in"]) == ("verifier", "plan 0123456789ab")


def test_without_them_no_key_is_written() -> None:
    rig = Rig()
    rig.hiring.hire("root", "eng", "E", "c")
    ((_, meta, _),) = rig.registry.created
    assert "kind" not in meta and "approved_in" not in meta


def test_the_created_time_is_the_injected_clock_s() -> None:
    rig = Rig()
    rig.clock.advance(86400)
    rig.hiring.hire("root", "eng", "E", "c")
    assert rig.registry.created[0][1]["created"] == "2030-05-07T07:08:09+00:00"


def test_the_inputs_are_checked_first_then_the_rights_then_the_authority_then_the_grant_then_the_agent_is_made_then_the_model_is_asked() -> None:
    rig = Rig()
    rig.hiring.hire("ceo", "eng", "E", "c", inputs=["/in"])
    assert rig.calls.log == ["inputs", "authority", "grant", "create", "model"]
    assert rig.authority.grants == [("ceo", False, 0)]  # no can_hire, so max_children 0


def test_an_approved_hire_skips_the_grant_check_and_nothing_else() -> None:
    rig = Rig()
    rig.hiring.hire("ceo", "eng", "E", "c", can_hire=True, max_children=4, inputs=["/in"], approved=True)
    assert rig.calls.log == ["inputs", "authority", "create", "model"] and rig.authority.grants == []
    assert rig.registry.created[0][1]["max_children"] == 4


def test_the_grant_asks_whether_the_report_gets_the_right_and_which_limit() -> None:
    rig = Rig()
    rig.hiring.hire("ceo", "eng", "E", "c", can_hire=True, max_children=3)
    assert rig.authority.grants == [("ceo", True, 3)]


def test_the_authority_is_asked_what_the_hirer_would_hand_down() -> None:
    rig = Rig()
    rig.hiring.hire("ceo", "eng", "E", "c", tools=["read", "read"], workspace="/ws", inputs=["/in"])
    assert rig.authority.checked == [("ceo", ("read",), "/ws", ["/checked"])]


def test_root_is_not_asked_for_authority() -> None:
    rig = Rig()
    rig.hiring.hire("root", "eng", "E", "c", tools=["anything"])
    assert rig.calls.log == ["create", "model"]


def test_a_confined_hirer_hands_down_no_inputs_when_it_hands_down_a_read_without_a_workspace() -> None:
    rig = Rig(unconfined=False)
    rig.hiring.hire("ceo", "eng", "E", "c", tools=["read"])
    assert rig.registry.created[0][1]["inputs"] == [] and rig.authority.checked == [("ceo", ("read",), None, [])]


def test_an_unconfined_hirer_leaves_the_inputs_out() -> None:
    rig = Rig(unconfined=True)
    rig.hiring.hire("ceo", "eng", "E", "c", tools=["read"])
    assert "inputs" not in rig.registry.created[0][1] and rig.authority.checked == [("ceo", ("read",), None, None)]


def test_the_model_is_asked_after_the_agent_exists_and_its_answer_is_in_the_event() -> None:
    rig = Rig()
    rig.hiring.hire("ceo", "eng", "E", "c")
    assert rig.model.seen_agent_exists == [True]
    (event,) = rig.events.events
    assert event.fields["model"] == "model-of-ceo/eng"


def test_the_depth_is_judged_after_the_authority_and_the_grant_and_before_the_place_is_looked_at() -> None:
    rig = Rig(org_md="---\nmax_depth: 1\n---\nr\n")
    rig.files.put_dir("ceo/eng")  # the place is taken, too: the depth is what is said
    with pytest.raises(OrgError, match="limited to depth 1"):
        rig.hiring.hire("ceo", "eng", "E", "c")
    assert rig.calls.log == ["authority", "grant"]


def test_nothing_is_made_nor_said_when_a_rule_refuses() -> None:
    rig = Rig()
    rig.files.put_dir("ceo/eng")
    with pytest.raises(OrgError, match="ceo/eng already exists"):
        rig.hiring.hire("ceo", "eng", "E", "c")
    assert rig.registry.created == [] and rig.events.events == [] and "model" not in rig.calls.log


def test_the_event_is_the_last_thing_that_happens() -> None:
    rig = Rig()
    rig.hiring.hire("ceo", "eng", "E", "c")
    assert rig.calls.log[-1] == "model" and len(rig.events.events) == 1
