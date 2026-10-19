"""The legacy functions of the second half of ``orgmcp.blueprint`` over a real ``Org``, and the legacy module of the examples.

``apply`` builds with the ports its ``Org`` has *now* (``org.runtime``): an ``Org`` whose runtime was opened with other ports applies through them
(this is how the tests make a step fail)."""

from __future__ import annotations

from pathlib import Path

import pytest

import orgmcp.blueprint as bpm
from orgmcp import blueprint_examples
from orgmcp.app import Org, wiring
from orgmcp.blueprint import api
from orgmcp.blueprint.testing import FlakyHiring, FlakyServiceCommands, FlakyTaskAssigner
from orgmcp.dispatch import TaskAssigner
from orgmcp.hierarchy import Hiring
from orgmcp.kernel import OrgError
from orgmcp.services import ServiceCommands

from orgmcp.blueprint.tests._plans import KEYS, base_dir, golden, scrub, template_at


def bp_of(key: str, base: Path) -> dict[str, object]:
    label, _, variant = key.partition("/")
    return bpm.load_text(template_at(label, variant, base))


def test_propose_and_propose_text_with_an_organization(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    org = Org.init(tmp_path / "org", "m")
    org.hire("root", "lead", "x", "y", can_hire=True)
    bp = bp_of("research/filled", base)
    expected = golden()["with_org"]
    assert scrub(bpm.propose_text(bp, org, allowed_roots=[base]), base) == expected["propose"]
    assert scrub(bpm.render_plan(bp, org=org, allowed_roots=[base]), base) == expected["details"]
    assert scrub(bpm.propose(bp, org=org, allowed_roots=[base]), base) == expected["details"]


# ------------------------------------------------------------------------------------------------ apply through the ports of the runtime


def org_with(tmp: Path, overrides: dict[type, object]) -> Org:
    org = Org.init(tmp / "org", "m")
    org.runtime = wiring.open_runtime(org.root, overrides)
    return org


def test_apply_hires_through_the_hiring_port_of_the_runtime_of_the_org(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    org = Org.init(tmp_path / "org", "m")
    org.runtime = wiring.open_runtime(org.root, {Hiring: FlakyHiring(org.runtime.hiring, fail_on=3)})
    with pytest.raises(OrgError, match="disk full"):
        bpm.apply(org, bp_of("research/filled", base), allowed_roots=[base])
    assert org.agents() == []


def test_apply_delegates_through_the_task_port_of_the_runtime_of_the_org(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    org = Org.init(tmp_path / "org", "m")
    org.runtime = wiring.open_runtime(org.root, {TaskAssigner: FlakyTaskAssigner(org.runtime.task_assigner)})
    with pytest.raises(OrgError, match="delegate failed"):
        bpm.apply(org, bp_of("research/filled", base), allowed_roots=[base])
    assert org.agents() == []


def test_apply_defines_services_through_the_service_port_of_the_runtime_of_the_org(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    org = Org.init(tmp_path / "org", "m")
    org.runtime = wiring.open_runtime(org.root, {ServiceCommands: FlakyServiceCommands(org.runtime.service_commands, fail_define_on=1)})
    with pytest.raises(OrgError, match="disk full"):
        bpm.apply(org, bp_of("research-service/filled", base), allowed_roots=[base])
    assert org.agents() == []


# ------------------------------------------------------------------------------------------------ the examples module


def test_the_examples_module_serves_the_templates_of_the_package() -> None:
    assert blueprint_examples.KINDS == api.EXAMPLE_KINDS
    for label in KEYS[::2]:
        name = label.split("/")[0]
        kind, _, service = name.partition("-")
        assert blueprint_examples.example(kind, "/golden/base", bool(service)) == golden()["examples"][name]


def test_the_examples_module_defines_no_template_text() -> None:
    names = set(vars(blueprint_examples))
    assert not {"SCHEMA", "RESEARCH", "DOCUMENTS", "CODE", "ANALYSIS", "TEMPLATES", "SERVICE_SCHEMA", "SERVICE_HEAD", "SERVICE_TAIL", "SERVICE_BODIES",
                "SERVICE_BUDGETS"} & names
