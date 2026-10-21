"""The second half of ``hirearchy.blueprint`` (plan and applier) over the runtime of a real ``Org``.

The applier of a runtime builds with the ports that runtime was opened with: an ``Org`` whose runtime was opened with other ports applies through
them (this is how the tests make a step fail)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.app import Org, wiring
from hirearchy.blueprint.testing import FlakyHiring, FlakyServiceCommands, FlakyTaskAssigner
from hirearchy.dispatch import TaskAssigner
from hirearchy.hierarchy import Hiring
from hirearchy.kernel import OrgError
from hirearchy.services import ServiceCommands

from hirearchy.blueprint.tests._plans import base_dir, golden, load_text, scrub, template_at


def bp_of(key: str, base: Path) -> dict[str, object]:
    label, _, variant = key.partition("/")
    return load_text(template_at(label, variant, base))


def test_propose_and_propose_text_with_an_organization(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    org = Org.init(tmp_path / "org", "m")
    org.hire("root", "lead", "x", "y", can_hire=True)
    bp = bp_of("research/filled", base)
    expected = golden()["with_org"]
    renderer = org.runtime.plan_renderer
    assert scrub(renderer.propose_text(bp, allowed_roots=[base]), base) == expected["propose"]
    assert scrub(renderer.render_plan(bp, allowed_roots=[base]), base) == expected["details"]
    assert scrub(renderer.propose(bp, allowed_roots=[base]), base) == expected["details"]


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
        org.runtime.blueprint_applier.apply(bp_of("research/filled", base), allowed_roots=[base])
    assert org.agents() == []


def test_apply_delegates_through_the_task_port_of_the_runtime_of_the_org(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    org = Org.init(tmp_path / "org", "m")
    org.runtime = wiring.open_runtime(org.root, {TaskAssigner: FlakyTaskAssigner(org.runtime.task_assigner)})
    with pytest.raises(OrgError, match="delegate failed"):
        org.runtime.blueprint_applier.apply(bp_of("research/filled", base), allowed_roots=[base])
    assert org.agents() == []


def test_apply_defines_services_through_the_service_port_of_the_runtime_of_the_org(tmp_path: Path) -> None:
    base = base_dir(tmp_path)
    org = Org.init(tmp_path / "org", "m")
    org.runtime = wiring.open_runtime(org.root, {ServiceCommands: FlakyServiceCommands(org.runtime.service_commands, fail_define_on=1)})
    with pytest.raises(OrgError, match="disk full"):
        org.runtime.blueprint_applier.apply(bp_of("research-service/filled", base), allowed_roots=[base])
    assert org.agents() == []

