"""``wire_blueprint``: the providers of the three ports of the first half of ``blueprint``, the roles directory (risk 8) and the legacy parts.

Risk 8 of ARCHITECTURE.md (path arithmetic that depends on file depth): on ``main`` the role templates were found with
``Path(__file__).parent / "roles"`` from ``orgmcp/blueprint.py``. The code that reads them moved one directory deeper (``orgmcp/blueprint/``), so the
directory is found in the wiring from the ``orgmcp`` package, and these tests prove that it is the same directory, in a checkout and in an installed
wheel (whose layout is rebuilt here; a real wheel was built with ``uv build`` and inspected by hand, see the report of the step)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import orgmcp
import orgmcp.blueprint as bpm
from orgmcp import blueprint_examples
import orgmcp.scheduler as scheduler
from orgmcp.app import wire_blueprint, wiring
from orgmcp.app._builder import Builder
from orgmcp.blueprint import (
    BlueprintApplier,
    BlueprintExamples,
    BlueprintLoader,
    BlueprintValidator,
    PlanIdentity,
    PlanRenderer,
    RoleLibrary,
    WorkspaceProvisioner,
)
from orgmcp.blueprint import _assembly
from orgmcp.blueprint._applier import HiringBlueprintApplier
from orgmcp.blueprint._examples import TemplateBlueprintExamples
from orgmcp.blueprint._files import FsTextFiles
from orgmcp.blueprint._identity import HashPlanIdentity
from orgmcp.blueprint._loader import YamlBlueprintLoader
from orgmcp.blueprint._provision import FsWorkspaceProvisioner
from orgmcp.blueprint._render import TextPlanRenderer
from orgmcp.blueprint._roles import PackagedRoleLibrary
from orgmcp.blueprint._validator import RuleBlueprintValidator
from orgmcp.kernel import Environment
from orgmcp.kiro import ConfinementPolicy
from orgmcp.services import ContractNormalizer

REPO = Path(__file__).resolve().parents[4]


def main_roles_dir(package: Path) -> Path:
    """The expression of ``main`` (blueprint.py: ``ROLES_DIR = Path(__file__).parent / "roles"``), for a package directory."""
    return (package / "blueprint.py").parent / "roles"


def test_the_package_directory_is_the_one_of_the_orgmcp_module() -> None:
    assert wire_blueprint.package_dir() == Path(orgmcp.__file__).resolve().parent


def test_the_roles_directory_of_the_checkout_is_the_value_of_main() -> None:
    assert wire_blueprint.roles_dir() == main_roles_dir(wire_blueprint.package_dir()) == (REPO / "src" / "orgmcp" / "roles").resolve()
    assert bpm.ROLES_DIR.resolve() == wire_blueprint.roles_dir()
    assert {p.stem for p in wire_blueprint.roles_dir().glob("*.md")} >= {"manager", "researcher", "writer", "engineer"}


@pytest.mark.parametrize("layout", ["repo/src/orgmcp", "venv/lib/python3.11/site-packages/orgmcp", "a/b/c/d/e/site-packages/orgmcp"])
def test_the_roles_directory_of_any_layout_is_the_value_of_main(tmp_path: Path, layout: str) -> None:
    package = (tmp_path / layout).resolve()
    package.mkdir(parents=True)
    assert wire_blueprint.roles_dir_of(package) == main_roles_dir(package) == package / "roles"


def test_the_role_library_of_the_runtime_reads_the_packaged_templates(tmp_path: Path) -> None:
    library = Builder(tmp_path, None, wiring.providers()).get(RoleLibrary)
    assert isinstance(library, PackagedRoleLibrary)
    assert library.role_names() == bpm.role_names() and library.get_role("manager") == bpm.get_role("manager")


def test_the_loader_and_the_validator_of_the_runtime_are_the_real_ones(tmp_path: Path) -> None:
    b = Builder(tmp_path, None, wiring.providers())
    assert isinstance(b.get(BlueprintLoader), YamlBlueprintLoader) and isinstance(b.get(BlueprintValidator), RuleBlueprintValidator)
    assert b.get(BlueprintValidator) is b.get(BlueprintValidator)


def test_the_validator_of_the_runtime_knows_the_organization_it_is_built_for(tmp_path: Path) -> None:
    from orgmcp.app import Org

    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "lead", "Lead", "charter", can_hire=True)
    bp = {"mission": "m", "agents": [{"name": "lead", "template": "manager"}]}
    validator = Builder(org.root, None, wiring.providers()).get(BlueprintValidator)
    assert "exists" in {i.code for i in validator.validate(bp, org_exists=True, allowed_roots=[tmp_path])}
    assert "exists" not in {i.code for i in validator.validate(bp, allowed_roots=[tmp_path])}


def test_the_legacy_parts_are_the_process_and_the_roles_directory() -> None:
    parts = wire_blueprint.legacy_parts()
    assert isinstance(parts.environment, Environment) and isinstance(parts.contract_normalizer, ContractNormalizer)
    assert isinstance(parts.confinement_policy, wire_blueprint.PatchPointConfinementPolicy) and isinstance(parts.confinement_policy, ConfinementPolicy)
    assert parts.roles_dir == wire_blueprint.roles_dir()


def test_the_legacy_parts_follow_the_environment_of_the_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "h"))
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", "/a:/b")
    env = wire_blueprint.legacy_parts().environment
    assert env.home() == Path(str(tmp_path / "h")) and env.get("ORGMCP_WORKSPACE_ROOTS") == "/a:/b"


def test_the_confinement_policy_of_the_legacy_parts_is_whatever_scheduler_file_confinement_is(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[Path, list[str], Path | None, list[Path]]] = []

    def stub(org_root: Path, tools: list[str], workspace: Path | None, inputs: list[Path]) -> tuple[list[str], dict[str, object]]:
        seen.append((org_root, tools, workspace, inputs))
        return ["stub"], {"stub": True}

    policy = wire_blueprint.legacy_parts().confinement_policy
    monkeypatch.setattr(scheduler, "file_confinement", stub)
    assert policy.file_confinement(Path("/o"), ("read",), Path("/w"), (Path("/i"),)) == (["stub"], {"stub": True})
    assert seen == [(Path("/o"), ["read"], Path("/w"), [Path("/i")])]


def test_the_application_package_installs_the_legacy_parts_when_it_is_loaded() -> None:
    parts = _assembly.legacy_parts()
    assert isinstance(parts.confinement_policy, wire_blueprint.PatchPointConfinementPolicy)
    assert parts.roles_dir == wire_blueprint.roles_dir() and parts.environment.home() == Path.home()


def test_the_legacy_roots_use_the_temp_directory_of_the_moment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ORGMCP_WORKSPACE_ROOTS", raising=False)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path / "t"))
    assembly = _assembly.assembly_of(None)
    assert (tmp_path / "t").resolve() in assembly.roots.roots()


def test_the_runtime_has_the_eight_ports_of_blueprint(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.role_library, PackagedRoleLibrary) and isinstance(runtime.blueprint_loader, YamlBlueprintLoader)
    assert isinstance(runtime.blueprint_validator, RuleBlueprintValidator) and isinstance(runtime.plan_renderer, TextPlanRenderer)
    assert isinstance(runtime.plan_identity, HashPlanIdentity) and isinstance(runtime.blueprint_applier, HiringBlueprintApplier)
    assert isinstance(runtime.blueprint_examples, TemplateBlueprintExamples) and isinstance(runtime.workspace_provisioner, FsWorkspaceProvisioner)
    for port, made in ((RoleLibrary, runtime.role_library), (BlueprintLoader, runtime.blueprint_loader), (BlueprintValidator, runtime.blueprint_validator),
                       (PlanRenderer, runtime.plan_renderer), (PlanIdentity, runtime.plan_identity), (BlueprintApplier, runtime.blueprint_applier),
                       (BlueprintExamples, runtime.blueprint_examples), (WorkspaceProvisioner, runtime.workspace_provisioner)):
        assert isinstance(made, port)
    assert list(tmp_path.iterdir()) == []  # building the ports does no I/O


def test_the_renderer_and_the_applier_of_the_runtime_are_for_the_organization_it_is_built_for(tmp_path: Path) -> None:
    from orgmcp.app import Org

    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "lead", "Lead", "charter", can_hire=True)
    base = tmp_path / "base"
    (base / "deliverables").mkdir(parents=True)
    bp = bpm.load_text(blueprint_examples.example("research", str(base)))
    plan = org.runtime.plan_renderer.render_plan(bp, allowed_roots=[base])
    assert "already exists" in plan  # the runtime knows the agents of its organization: the name of the lead is taken
    with pytest.raises(bpm.BlueprintError, match="already exists"):
        org.runtime.blueprint_applier.apply(bp, allowed_roots=[base])


def test_the_applier_of_the_runtime_builds_with_the_ports_it_is_given(tmp_path: Path) -> None:
    from orgmcp.app import Org
    from orgmcp.blueprint.testing import FlakyHiring
    from orgmcp.hierarchy import Hiring
    from orgmcp.kernel import OrgError

    org = Org.init(tmp_path / "org", "mission")
    flaky = FlakyHiring(org.runtime.hiring, fail_on=2)
    runtime = wiring.open_runtime(org.root, {Hiring: flaky})
    base = tmp_path / "base"
    (base / "deliverables").mkdir(parents=True)
    bp = bpm.load_text(blueprint_examples.example("research", str(base)))
    with pytest.raises(OrgError, match="disk full"):
        runtime.blueprint_applier.apply(bp, allowed_roots=[base])
    assert org.agents() == []  # the first hire was taken back


def test_the_legacy_examples_module_is_given_the_templates_when_the_application_package_is_loaded() -> None:
    assert isinstance(blueprint_examples._installed, TemplateBlueprintExamples)
    assert blueprint_examples.example("code", "/b") == TemplateBlueprintExamples().example("code", "/b")
