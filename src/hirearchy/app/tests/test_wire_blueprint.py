"""``wire_blueprint``: the providers of the ports of ``blueprint`` and the roles directory (risk 8).

Risk 8 of ARCHITECTURE.md (path arithmetic that depends on file depth): on ``main`` the role templates were found with
``Path(__file__).parent / "roles"`` from ``hirearchy/blueprint.py``. The code that reads them moved one directory deeper (``hirearchy/blueprint/``), so the
directory is found in the wiring from the ``hirearchy`` package, and these tests prove that it is the same directory, in a checkout and in an installed
wheel (whose layout is rebuilt here; a real wheel was built with ``uv build`` and inspected by hand, see the report of the step)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import hirearchy
import hirearchy.blueprint as bpm
from hirearchy.app import wire_blueprint, wiring
from hirearchy.app._builder import Builder
from hirearchy.blueprint import (
    BlueprintApplier,
    BlueprintExamples,
    BlueprintLoader,
    BlueprintValidator,
    PlanIdentity,
    PlanRenderer,
    RoleLibrary,
    WorkspaceProvisioner,
)
from hirearchy.blueprint._applier import HiringBlueprintApplier
from hirearchy.blueprint._examples import TemplateBlueprintExamples
from hirearchy.blueprint._identity import HashPlanIdentity
from hirearchy.blueprint._loader import YamlBlueprintLoader
from hirearchy.blueprint._provision import FsWorkspaceProvisioner
from hirearchy.blueprint._render import TextPlanRenderer
from hirearchy.blueprint._roles import PackagedRoleLibrary
from hirearchy.blueprint._validator import RuleBlueprintValidator
from hirearchy.blueprint.testing import ScriptedConfinementPolicy
from hirearchy.blueprint.tests import _corpus
from testkit.blueprint_world import with_user_words
from hirearchy.kiro import ConfinementPolicy

REPO = Path(__file__).resolve().parents[4]


def main_roles_dir(package: Path) -> Path:
    """The expression of ``main`` (blueprint.py: ``ROLES_DIR = Path(__file__).parent / "roles"``), for a package directory."""
    return (package / "blueprint.py").parent / "roles"


def test_the_package_directory_is_the_one_of_the_hirearchy_module() -> None:
    assert wire_blueprint.package_dir() == Path(hirearchy.__file__).resolve().parent


def test_the_roles_directory_of_the_checkout_is_the_value_of_main() -> None:
    assert wire_blueprint.roles_dir() == main_roles_dir(wire_blueprint.package_dir()) == (REPO / "src" / "hirearchy" / "roles").resolve()
    assert {p.stem for p in wire_blueprint.roles_dir().glob("*.md")} >= {"manager", "researcher", "writer", "engineer"}


@pytest.mark.parametrize("layout", ["repo/src/hirearchy", "venv/lib/python3.11/site-packages/hirearchy", "a/b/c/d/e/site-packages/hirearchy"])
def test_the_roles_directory_of_any_layout_is_the_value_of_main(tmp_path: Path, layout: str) -> None:
    package = (tmp_path / layout).resolve()
    package.mkdir(parents=True)
    assert wire_blueprint.roles_dir_of(package) == main_roles_dir(package) == package / "roles"


def test_the_role_library_of_the_runtime_reads_the_packaged_templates(tmp_path: Path) -> None:
    library = Builder(tmp_path, None, wiring.providers()).get(RoleLibrary)
    assert isinstance(library, PackagedRoleLibrary)
    roles = wire_blueprint.roles_dir()
    assert library.role_names() == sorted(p.stem for p in roles.glob("*.md")) and library.get_role("manager") == PackagedRoleLibrary(roles).get_role("manager")
    manager = library.get_role("manager")
    assert manager is not None and manager.name == "manager" and library.get_role("nobody") is None


def test_the_loader_and_the_validator_of_the_runtime_are_the_real_ones(tmp_path: Path) -> None:
    b = Builder(tmp_path, None, wiring.providers())
    assert isinstance(b.get(BlueprintLoader), YamlBlueprintLoader) and isinstance(b.get(BlueprintValidator), RuleBlueprintValidator)
    assert b.get(BlueprintValidator) is b.get(BlueprintValidator)


def test_the_validator_of_the_runtime_knows_the_organization_it_is_built_for(tmp_path: Path) -> None:
    from hirearchy.app import Org

    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "lead", "Lead", "charter", can_hire=True)
    bp = {"mission": "m", "agents": [{"name": "lead", "template": "manager"}]}
    validator = Builder(org.root, None, wiring.providers()).get(BlueprintValidator)
    assert "exists" in {i.code for i in validator.validate(bp, org_exists=True, allowed_roots=[tmp_path])}
    assert "exists" not in {i.code for i in validator.validate(bp, allowed_roots=[tmp_path])}


OPEN = (Path("/hirearchy-org-root"),)


def test_the_validator_of_the_runtime_asks_the_confinement_policy_of_the_runtime(tmp_path: Path) -> None:
    policy = ScriptedConfinementPolicy(read=OPEN)
    runtime = wiring.open_runtime(tmp_path, {ConfinementPolicy: policy})
    bp = _corpus.documents(tmp_path)  # the writer leaves its work in the org; the reviewer holds the built-in read
    issues = runtime.blueprint_validator.validate(bp, allowed_roots=[tmp_path])
    assert policy.calls and policy.calls[0][1] == ["read"]
    assert "verifier-cannot-read" not in {i.code for i in issues}
    policy.read = ()  # the policy now hides the organization from the built-in read
    assert "verifier-cannot-read" in {i.code for i in runtime.blueprint_validator.validate(bp, allowed_roots=[tmp_path])}


def test_the_roots_of_the_runtime_use_the_temp_directory_of_the_moment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HIREARCHY_WORKSPACE_ROOTS", raising=False)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path / "t"))
    roots = wire_blueprint._checking(Builder(tmp_path, None, wiring.providers())).roots
    assert (tmp_path / "t").resolve() in roots.roots()


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
    from hirearchy.app import Org

    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "lead", "Lead", "charter", can_hire=True)
    base = tmp_path / "base"
    (base / "deliverables").mkdir(parents=True)
    bp = org.runtime.blueprint_loader.load_text(org.runtime.blueprint_examples.example("research", str(base)))
    plan = org.runtime.plan_renderer.render_plan(bp, allowed_roots=[base])
    assert "already exists" in plan  # the runtime knows the agents of its organization: the name of the lead is taken
    with pytest.raises(bpm.BlueprintError, match="already exists"):
        org.runtime.blueprint_applier.apply(bp, allowed_roots=[base])


def test_the_applier_of_the_runtime_builds_with_the_ports_it_is_given(tmp_path: Path) -> None:
    from hirearchy.app import Org
    from hirearchy.blueprint.testing import FlakyHiring
    from hirearchy.hierarchy import Hiring
    from hirearchy.kernel import OrgError

    org = Org.init(tmp_path / "org", "mission")
    flaky = FlakyHiring(org.runtime.hiring, fail_on=2)
    runtime = wiring.open_runtime(org.root, {Hiring: flaky})
    base = tmp_path / "base"
    (base / "deliverables").mkdir(parents=True)
    bp = runtime.blueprint_loader.load_text(with_user_words(runtime.blueprint_examples.example("research", str(base))))
    with pytest.raises(OrgError, match="disk full"):
        runtime.blueprint_applier.apply(bp, allowed_roots=[base])
    assert org.agents() == []  # the first hire was taken back

