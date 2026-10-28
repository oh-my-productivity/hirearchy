"""Contract of ``Hiring``: the rules of creating a direct report, over the real classes on disk and over the in-memory fakes.

What the callers rely on (the MCP tool, the CLI, the blueprint): the charter that is written, the skeleton that comes with it, the refusals in the
words agents are shown, and the one event."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.hierarchy import Hiring
from hirearchy.hierarchy.testing import IMPLEMENTATIONS, HierarchyWorld
from hirearchy.kernel import RESERVED, OrgError

from ._support import make, outside


@pytest.fixture(params=IMPLEMENTATIONS[Hiring], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> HierarchyWorld:
    made = make(request, tmp_path)
    assert isinstance(made.hiring, Hiring)
    return made


def refusal(w: HierarchyWorld, *args: str, **kw: object) -> str:
    with pytest.raises(OrgError) as e:
        w.hiring.hire(*args, **kw)  # type: ignore[arg-type]
    return str(e.value)


def meta_of(w: HierarchyWorld, addr: str) -> dict[str, object]:
    return dict(w.charters.charter(addr)[0])


# ------------------------------------------------------------------------------ what is created


def test_the_address_of_the_report_is_returned(w: HierarchyWorld) -> None:
    assert w.hiring.hire("root", "ops", "Ops", "Run things.") == "ops"
    assert w.hiring.hire("ceo", "qa", "QA", "Test things.") == "ceo/qa"


def test_the_actor_is_normalized(w: HierarchyWorld) -> None:
    assert w.hiring.hire("ceo/", "qa", "QA", "Test things.") == "ceo/qa"
    assert w.hiring.hire(" root ", "ops", "Ops", "Run things.") == "ops"


def test_the_new_agent_exists_and_is_a_direct_report(w: HierarchyWorld) -> None:
    w.hiring.hire("ceo", "qa", "QA", "Test things.")
    assert w.agents.exists("ceo/qa") and w.agents.children("ceo") == ["ceo/eng", "ceo/qa"]


def test_the_charter_is_written_byte_for_byte(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "chief", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    assert w.read("chief/AGENT.md") == (
        "---\nrole: Chief executive\ntools: []\ncan_hire: true\nmax_children: 2\nhired_by: root\ncreated: '2026-10-18T10:00:00+00:00'\n---\n"
        "# Role: Chief executive\n\nRun the company.\n"
    )


def test_every_key_is_written_in_its_order_when_everything_is_given(w: HierarchyWorld) -> None:
    ws, data = outside(w, "ws"), outside(w, "data")
    w.hiring.hire("root", "dev", " Developer ", "Write code.", model="claude-opus-5.5", tools=["shell", "read"], can_hire=True, max_children=3,
                  workspace=ws, inputs=[data])
    assert w.read("dev/AGENT.md") == (
        f"---\nrole: Developer\nmodel: claude-opus-5.5\ntools:\n- read\n- shell\ncan_hire: true\nmax_children: 3\nworkspace: {ws}\ninputs:\n- {data}\n"
        "hired_by: root\ncreated: '2026-10-18T10:00:00+00:00'\n---\n# Role:  Developer \n\nWrite code.\n"  # the heading has the role as given
    )


def test_hire_accepts_kind_and_approved_in(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "chk", "Independent Reviewer", "Check.", kind="verifier", approved_in="plan 0123456789ab")
    w.hiring.hire("root", "plain", "Ops", "Run things.")
    assert (meta_of(w, "chk")["kind"], meta_of(w, "chk")["approved_in"]) == ("verifier", "plan 0123456789ab")
    assert "kind" not in meta_of(w, "plain") and "approved_in" not in meta_of(w, "plain")


def test_a_charter_with_its_own_heading_keeps_it(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "  # Operator\n\nOwn heading wins.  ")
    assert w.read("ops/AGENT.md") is not None and w.read("ops/AGENT.md").endswith("---\n# Operator\n\nOwn heading wins.\n")  # type: ignore[union-attr]


def test_created_is_the_time_of_the_clock_to_the_second(w: HierarchyWorld) -> None:
    w.clock.advance(3725)
    w.hiring.hire("root", "ops", "Ops", "Run things.")
    assert meta_of(w, "ops")["created"] == "2026-10-18T11:02:05+00:00"


def test_the_skeleton_of_an_agent_comes_with_it(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.")
    assert w.listing("ops") == ["AGENT.md", "MEMORY.md", "inbox", "inflight", "read", "runs", "sent", "work"]
    assert w.read("ops/MEMORY.md") == ""


def test_can_hire_is_coerced_to_a_bool_and_max_children_must_be_a_number(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.", can_hire=1, max_children=3)  # type: ignore[arg-type]
    assert (meta_of(w, "ops")["can_hire"], meta_of(w, "ops")["max_children"]) == (True, 3)  # "3" is refused now: see A3 below


def test_the_defaults_are_a_report_that_cannot_hire(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.")
    meta = meta_of(w, "ops")
    assert (meta["can_hire"], meta["max_children"], meta["tools"], meta["hired_by"]) == (False, 0, [], "root")  # no right, no limit
    assert not {"model", "workspace", "inputs"} & set(meta)


def test_the_hirer_is_recorded(w: HierarchyWorld) -> None:
    w.hiring.hire("ceo", "qa", "QA", "Test things.")
    assert meta_of(w, "ceo/qa")["hired_by"] == "ceo"


# ------------------------------------------------------------------------------ tools and the model


def test_tools_are_sorted_and_deduplicated(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.", tools=["write", "shell", "read", "read", "write"])
    assert meta_of(w, "ops")["tools"] == ["read", "shell", "write"]


def test_a_model_that_is_given_is_pinned(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.", model="claude-opus-5.5")
    assert meta_of(w, "ops")["model"] == "claude-opus-5.5"


def test_without_a_model_the_charter_is_unpinned_so_the_default_of_the_org_applies(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.")
    assert "model" not in meta_of(w, "ops")


# ------------------------------------------------------------------------------ the model floor (docs/design/org-agent-model-floor.md)

PAIR = "claude-sonnet-5.5, claude-opus-5.5"


def m1(model: str, allowed: str = PAIR) -> str:
    return f'model "{model}" is not allowed for org agents; allowed: {allowed} (only the user can widen this set)'


@pytest.mark.parametrize("model", ["claude-haiku-4.5", "claude-sonnet-4.6"])
def test_a_model_outside_the_allowed_set_is_refused(w: HierarchyWorld, model: str) -> None:
    before = w.listing("")
    assert refusal(w, "root", "ops", "Ops", "c", model=model) == m1(model)
    assert not w.agents.exists("ops") and w.listing("") == before and w.events.events == []


@pytest.mark.parametrize("model", ["claude-sonnet-5.5", "claude-opus-5.5"])
def test_the_floor_models_are_admitted_and_pinned(w: HierarchyWorld, model: str) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.", model=model)
    assert meta_of(w, "ops")["model"] == model


def test_without_a_model_a_default_model_outside_the_set_is_refused(w: HierarchyWorld) -> None:
    w.configure("---\nmission: m\ndefault_model: claude-haiku-4.5\n---\nrules\n")
    assert refusal(w, "root", "ops", "Ops", "c") == "default_model: " + m1("claude-haiku-4.5")
    assert not w.agents.exists("ops") and w.events.events == []


def test_a_model_inside_the_set_is_admitted_whatever_the_default_is(w: HierarchyWorld) -> None:
    w.configure("---\nmission: m\ndefault_model: claude-haiku-4.5\n---\nrules\n")
    w.hiring.hire("root", "ops", "Ops", "Run things.", model="claude-opus-5.5")
    assert meta_of(w, "ops")["model"] == "claude-opus-5.5"


def test_a_widened_set_admits_its_extra_model(w: HierarchyWorld) -> None:
    w.configure("---\nmission: m\nextra_allowed_models: [claude-sonnet-4.6]\n---\nrules\n")
    w.hiring.hire("root", "ops", "Ops", "Run things.", model="claude-sonnet-4.6")
    assert meta_of(w, "ops")["model"] == "claude-sonnet-4.6"
    assert refusal(w, "root", "pm", "PM", "c", model="claude-haiku-4.5") == m1("claude-haiku-4.5", PAIR + ", claude-sonnet-4.6")


def test_an_approved_hire_below_the_floor_is_refused_too(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo", "ops", "Ops", "c", model="claude-haiku-4.5", approved=True) == m1("claude-haiku-4.5")
    assert not w.agents.exists("ceo/ops")


def test_an_ORG_md_that_cannot_be_parsed_refuses_the_hire_in_words_that_name_it(w: HierarchyWorld) -> None:
    """The refusal is not the parser's own text, whether a model is given or not; nothing is created."""
    w.configure("---\nmax_depth: 4\nextra_allowed_models: [claude-sonnet-4.6\n---\nrules\n")
    for model in ("claude-opus-5.5", None):
        message = refusal(w, "root", "ops", "Ops", "c", model=model)
        assert message.startswith("ORG.md cannot be read") and "while parsing" not in message
    assert not w.agents.exists("ops") and w.events.events == []


# ------------------------------------------------------------------------------ names


@pytest.mark.parametrize("name", ["Ops", "ops\n", "o ps", "", "1ops", "-ops", "ops_x", "a" * 33, "o/ps", "ops.", "ÖPS"])
def test_a_name_must_be_lowercase_letters_digits_and_dashes(w: HierarchyWorld, name: str) -> None:
    assert refusal(w, "root", name, "R", "c") == "name must be lowercase letters, digits and dashes (max 32), and not a reserved word"
    assert w.agents.children("root") == ["ceo"]


@pytest.mark.parametrize("name", sorted(n for n in RESERVED if n[0].isalpha()))
def test_a_reserved_word_is_not_a_name(w: HierarchyWorld, name: str) -> None:
    assert refusal(w, "root", name, "R", "c") == "name must be lowercase letters, digits and dashes (max 32), and not a reserved word"


def test_a_name_of_32_characters_is_fine(w: HierarchyWorld) -> None:
    name = "a" + "b-1" * 10 + "c"
    assert len(name) == 32 and w.hiring.hire("root", name, "R", "c") == name


def test_a_name_that_is_taken_is_refused(w: HierarchyWorld) -> None:
    assert refusal(w, "root", "ceo", "R", "c") == "ceo already exists"
    assert refusal(w, "ceo", "eng", "R", "c") == "ceo/eng already exists"


def test_a_stray_directory_in_the_place_of_the_agent_counts_as_taken(w: HierarchyWorld) -> None:
    w.put_dir("stray")
    assert refusal(w, "root", "stray", "R", "c") == "stray already exists"
    assert not w.agents.exists("stray") and w.listing("stray") == []


def test_an_actor_that_does_not_exist_is_refused_before_the_name_is_looked_at(w: HierarchyWorld) -> None:
    assert refusal(w, "ghost", "Bad Name", "R", "c") == "no such agent: ghost"


# ------------------------------------------------------------------------------ the hirer's rights


def test_a_hirer_without_can_hire_is_refused(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo/eng", "intern", "Intern", "Help.") == "your charter does not allow hiring"
    assert not w.agents.exists("ceo/eng/intern")


def test_the_maximum_of_direct_reports_is_enforced(w: HierarchyWorld) -> None:
    w.hiring.hire("ceo", "ops", "Ops", "Run things.")
    assert refusal(w, "ceo", "qa", "QA", "Test things.") == "you already have the maximum of 2 direct reports"
    assert not w.agents.exists("ceo/qa")


def test_a_hirer_without_a_limit_in_its_charter_may_have_five(w: HierarchyWorld) -> None:
    w.agent("lead", {"role": "Lead", "tools": [], "can_hire": True})
    for n in range(5):
        w.hiring.hire("lead", f"r{n}", "R", "c")
    assert refusal(w, "lead", "r5", "R", "c") == "you already have the maximum of 5 direct reports"


def test_root_may_hire_without_a_charter_that_says_so(w: HierarchyWorld) -> None:
    for n in range(8):  # root has no maximum
        w.hiring.hire("root", f"r{n}", "R", "c")
    assert len(w.agents.children("root")) == 9


def test_a_hirer_cannot_grant_tools_it_does_not_have(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo", "ops", "Ops", "c", tools=["shell", "read"]) == "you cannot grant tools you do not have yourself: read, shell"
    w.agent("ceo", {"role": "Chief", "tools": ["read"], "can_hire": True, "max_children": 2})
    w.hiring.hire("ceo", "ops", "Ops", "c", tools=["read"])
    assert meta_of(w, "ceo/ops")["tools"] == ["read"]


def test_root_may_grant_any_tool(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "c", tools=["shell", "anything"])
    assert meta_of(w, "ops")["tools"] == ["anything", "shell"]


def test_a_workspace_must_be_inside_the_hirer_s_own(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo", "ops", "Ops", "c", workspace=outside(w, "ws")) == "you have no workspace, so you cannot assign one"
    mine = outside(w, "mine")
    w.agent("ceo", {"role": "Chief", "tools": [], "can_hire": True, "max_children": 2, "workspace": mine})
    assert refusal(w, "ceo", "ops", "Ops", "c", workspace=outside(w, "other")) == f"a report's workspace must be inside yours ({mine})"
    w.hiring.hire("ceo", "ops", "Ops", "c", workspace=f"{mine}/sub")
    assert meta_of(w, "ceo/ops")["workspace"] == f"{mine}/sub"


# ------------------------------------------------------------------------------ inputs


def test_inputs_are_checked_and_written(w: HierarchyWorld) -> None:
    data = outside(w, "data")
    w.hiring.hire("root", "reader", "R", "c", tools=["read"], inputs=[f" {data} "])
    assert meta_of(w, "reader")["inputs"] == [data]


def test_an_input_must_be_an_absolute_path_outside_the_organization(w: HierarchyWorld) -> None:
    assert "an input must be an absolute path (got `docs`)" == refusal(w, "root", "a", "R", "c", inputs=["docs"])
    assert refusal(w, "root", "b", "R", "c", inputs=[str(w.root / "ceo")]).startswith("an input must not overlap the organization directory")
    assert refusal(w, "root", "c", "R", "c", inputs=[str(w.root.parent)]).startswith("an input must not overlap the organization directory")
    assert w.agents.children("root") == ["ceo"]


def test_the_inputs_are_checked_before_the_hirer_s_right_to_hire(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo/eng", "intern", "I", "c", inputs=["relative"]) == "an input must be an absolute path (got `relative`)"


def test_a_hirer_may_only_hand_down_inputs_it_can_see(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo", "ops", "Ops", "c", inputs=[outside(w, "data")]) == "you have no workspace or inputs, so you cannot assign inputs"
    mine = outside(w, "handbook")
    w.agent("ceo", {"role": "Chief", "tools": ["read"], "can_hire": True, "max_children": 2, "inputs": [mine]})
    with pytest.raises(OrgError, match="a report's inputs must be inside your inputs or workspace"):
        w.hiring.hire("ceo", "ops", "Ops", "c", inputs=[outside(w, "elsewhere")])
    w.hiring.hire("ceo", "ops", "Ops", "c", inputs=[f"{mine}/hr"])
    assert meta_of(w, "ceo/ops")["inputs"] == [f"{mine}/hr"]


def test_a_confined_hirer_never_hands_down_an_unconfined_read(w: HierarchyWorld) -> None:
    mine = outside(w, "handbook")
    w.agent("ceo", {"role": "Chief", "tools": ["read"], "can_hire": True, "max_children": 2, "inputs": [mine]})
    w.hiring.hire("ceo", "reader", "R", "c", tools=["read"])  # no workspace, no inputs given
    assert meta_of(w, "ceo/reader")["inputs"] == []


def test_root_s_own_hire_keeps_the_legacy_shape_of_a_read_charter(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "old", "Old", "c", tools=["read"])
    assert "inputs" not in meta_of(w, "old")


def test_a_legacy_hirer_may_hand_down_an_unconfined_read(w: HierarchyWorld) -> None:
    w.agent("ceo", {"role": "Chief", "tools": ["read"], "can_hire": True, "max_children": 2})  # read, no workspace, no `inputs` key
    w.hiring.hire("ceo", "reader", "R", "c", tools=["read"])
    assert "inputs" not in meta_of(w, "ceo/reader")


def test_a_read_with_a_workspace_needs_no_inputs(w: HierarchyWorld) -> None:
    mine = outside(w, "mine")
    w.agent("ceo", {"role": "Chief", "tools": ["read"], "can_hire": True, "max_children": 2, "workspace": mine})
    w.hiring.hire("ceo", "reader", "R", "c", tools=["read"], workspace=mine)
    assert "inputs" not in meta_of(w, "ceo/reader")


def test_inputs_that_are_given_empty_stay_empty(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "reader", "R", "c", tools=["read"], inputs=[])
    assert meta_of(w, "reader")["inputs"] == []


# ------------------------------------------------------------------------------ depth


def test_the_organization_is_limited_to_its_depth(w: HierarchyWorld) -> None:
    w.configure("---\nmission: m\nmax_depth: 2\n---\nrules\n")
    w.agent("ceo/eng", {"role": "Lead", "tools": [], "can_hire": True, "hired_by": "ceo"})
    assert refusal(w, "ceo/eng", "dev", "D", "c") == "the organization is limited to depth 2"
    assert not w.agents.exists("ceo/eng/dev")


def test_the_default_depth_allows_four_levels(w: HierarchyWorld) -> None:
    for parent, name in (("ceo/eng", "a"), ("ceo/eng/a", "b")):
        w.agent(parent, {"role": "Lead", "tools": [], "can_hire": True})
        w.hiring.hire(parent, name, "R", "c")
    w.agent("ceo/eng/a/b", {"role": "Lead", "tools": [], "can_hire": True})
    assert refusal(w, "ceo/eng/a/b", "c", "R", "c") == "the organization is limited to depth 4"


# ------------------------------------------------------------------------------ the event


def test_one_event_says_who_hired_whom(w: HierarchyWorld) -> None:
    w.hiring.hire("ceo", "qa", "  Tester ", "Test things.", model="claude-opus-5.5")
    (event,) = w.events.events
    assert event.kind == "agent.hire" and event.actor == "ceo"
    assert event.fields == {"agent": "ceo/qa", "by": "ceo", "role": "Tester", "model": "claude-opus-5.5", "tools": []}


def test_the_event_carries_the_model_the_agent_will_run_with(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.")
    (event,) = w.events.events
    assert event.fields["model"] == "claude-sonnet-5.5"  # the default of the organization
    w.configure("---\nmission: m\ndefault_model: claude-opus-5.5\n---\nrules\n")
    w.hiring.hire("root", "pm", "PM", "Plan.")
    assert w.events.events[-1].fields["model"] == "claude-opus-5.5"


def test_the_event_lists_the_tools_sorted(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "ops", "Ops", "Run things.", tools=["write", "read", "read"])
    assert w.events.events[0].fields["tools"] == ["read", "write"]


def test_a_long_role_is_clipped_in_the_event_not_in_the_charter(w: HierarchyWorld) -> None:
    role = "R" * 400
    w.hiring.hire("root", "ops", role, "Run things.")
    shown = w.events.events[0].fields["role"]
    assert isinstance(shown, str) and len(shown) < len(role) and shown.endswith("…")
    assert meta_of(w, "ops")["role"] == role


def test_a_refused_hire_leaves_no_event_and_no_trace(w: HierarchyWorld) -> None:
    before = w.listing("")
    refusal(w, "ceo/eng", "intern", "I", "c")
    refusal(w, "root", "Bad", "I", "c")
    refusal(w, "root", "ceo", "I", "c")
    assert w.events.events == [] and w.listing("") == before


# ------------------------------------------------------------------------------ the authority bound (A1, A3) and max_children without can_hire

A3 = "max_children must be a whole number >= 0"
A1 = (
    "refused: you cannot grant `can_hire: true`: only the user (root) or an approved plan gives an agent the right to hire. "
    "Hire it with can_hire false. A change of your team's limits is the user's decision: the retro brief shows them the evidence, so do not ask for it."
)


@pytest.mark.parametrize("hirer", ["root", "ceo"])
@pytest.mark.parametrize("value", [True, -1, "3", 2.5, None])
@pytest.mark.parametrize("can_hire", [False, True])
def test_a3_for_every_hirer_root_included(w: HierarchyWorld, hirer: str, value: object, can_hire: bool) -> None:
    assert refusal(w, hirer, "ops", "Ops", "c", can_hire=can_hire, max_children=value, approved=True) == A3
    assert refusal(w, hirer, "ops", "Ops", "c", can_hire=can_hire, max_children=value) == A3
    assert not w.agents.exists(f"{hirer}/ops" if hirer != "root" else "ops") and w.events.events == []


def test_a3_is_checked_before_the_hirer_s_right_to_hire(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo/eng", "intern", "I", "c", max_children=-1) == A3  # ceo/eng cannot hire, but A3 comes first


@pytest.mark.parametrize("hirer", ["root", "ceo"])
@pytest.mark.parametrize("asked", [5, 3, 0])
def test_a_report_without_can_hire_gets_max_children_0_root_and_non_root(w: HierarchyWorld, hirer: str, asked: int) -> None:
    addr = w.hiring.hire(hirer, "a", "A", "c", can_hire=False, max_children=asked)
    assert (meta_of(w, addr)["can_hire"], meta_of(w, addr)["max_children"]) == (False, 0)


def test_the_default_max_children_of_a_report_that_cannot_hire_is_0(w: HierarchyWorld) -> None:
    addr = w.hiring.hire("ceo", "a", "A", "c")  # the default max_children is 5
    assert meta_of(w, addr)["max_children"] == 0


def test_root_keeps_the_max_children_of_a_report_that_can_hire(w: HierarchyWorld) -> None:
    w.hiring.hire("root", "lead", "Lead", "c", can_hire=True, max_children=3)
    assert meta_of(w, "lead")["max_children"] == 3


def test_a_non_root_hirer_granting_can_hire_is_a1(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo", "lead", "Lead", "c", can_hire=True) == A1
    assert refusal(w, "ceo", "lead", "Lead", "c", can_hire=True, max_children=1) == A1
    assert not w.agents.exists("ceo/lead") and w.events.events == []


def test_approved_skips_only_the_grant_check(w: HierarchyWorld) -> None:
    w.hiring.hire("ceo", "lead", "Lead", "c", can_hire=True, max_children=9, approved=True)  # ceo's own limit is 2
    assert (meta_of(w, "ceo/lead")["can_hire"], meta_of(w, "ceo/lead")["max_children"]) == (True, 9)


def test_capacity_and_authority_checks_still_run_when_approved(w: HierarchyWorld) -> None:
    assert refusal(w, "ceo/eng", "intern", "I", "c", can_hire=True, approved=True) == "your charter does not allow hiring"
    assert refusal(w, "ceo", "ops", "Ops", "c", tools=["shell"], can_hire=True, approved=True) == (
        "you cannot grant tools you do not have yourself: shell"
    )
    w.hiring.hire("ceo", "ops", "Ops", "c", can_hire=True, approved=True)
    assert refusal(w, "ceo", "qa", "QA", "c", can_hire=True, approved=True) == "you already have the maximum of 2 direct reports"
    assert refusal(w, "ceo", "qa", "QA", "c", approved=True, max_children=-1) == A3
