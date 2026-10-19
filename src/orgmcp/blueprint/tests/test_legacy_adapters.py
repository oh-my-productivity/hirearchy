"""The old module-level functions of ``orgmcp.blueprint`` (the part that moved) are adapters over the classes of the package.

They read the process through the *legacy parts* that ``orgmcp.app`` installs when it is loaded (the environment, the confinement policy, the
contract normalizer, the roles directory), so a test that installs other parts runs the old functions over its own fakes. The old private helpers
that the classes replaced are gone from ``_legacy``."""

from __future__ import annotations

import ast
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

import orgmcp.blueprint as bpm
from orgmcp.blueprint import _legacy, api
from orgmcp.blueprint._assembly import LegacyParts, install_legacy_parts, legacy_parts
from orgmcp.blueprint.testing import ScriptedConfinementPolicy
from orgmcp.kernel.testing import DictEnvironment
from orgmcp.services.testing import normalizer

from . import _corpus


OPEN = {"read": {"allowedPaths": ["/orgmcp-org-root", "/orgmcp-org-root/**"], "deniedPaths": []}}


class Installed:
    def __init__(self, parts: LegacyParts, policy: ScriptedConfinementPolicy, home: Path) -> None:
        self.parts = parts
        self.policy = policy
        self.home = home


@pytest.fixture
def installed(tmp_path: Path) -> Iterator[Installed]:
    """Other legacy parts than the real ones, for the length of a test."""
    before = legacy_parts()
    home, roles = tmp_path / "fakehome", tmp_path / "roles"
    home.mkdir()
    shutil.copytree(_legacy.ROLES_DIR, roles)  # the packaged templates, in a directory the test may add to
    policy = ScriptedConfinementPolicy(OPEN)
    parts = LegacyParts(DictEnvironment(home=home, cwd=tmp_path), policy, normalizer(tmp_path), roles)
    install_legacy_parts(parts)
    yield Installed(parts, policy, home)
    install_legacy_parts(before)


def test_the_parts_that_were_installed_are_the_parts_in_force(installed: Installed) -> None:
    assert legacy_parts() is installed.parts


def test_the_role_functions_read_the_roles_directory_of_the_parts(installed: Installed) -> None:
    before = bpm.role_names()
    assert before == sorted(p.stem for p in installed.parts.roles_dir.glob("*.md")) and "poet" not in before and bpm.get_role("poet") is None
    (installed.parts.roles_dir / "poet.md").write_text("---\ntitle: Poet\nkind: author\ntools: [read]\nbase_runs: 5\n---\nRhyme.\n", encoding="utf-8")
    assert bpm.role_names() == sorted([*before, "poet"])
    assert bpm.get_role("poet") == api.Role("poet", "Poet", "author", "cheap", ("read",), 5, "", "Rhyme.")


def test_validate_asks_the_environment_of_the_parts_for_the_home_directory(installed: Installed, tmp_path: Path) -> None:
    bp = _corpus.code(tmp_path)
    bp["needs"]["workspace"] = str(installed.home / ".kiro" / "work")  # type: ignore[index]
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    assert any(i.code == "path-root" and "is inside ~/.kiro" in i.message for i in issues)


def test_validate_asks_the_confinement_policy_of_the_parts_whether_a_reviewer_can_read_the_organization(installed: Installed, tmp_path: Path) -> None:
    bp = _corpus.documents(tmp_path)  # the writer leaves its work in the org; the reviewer holds the built-in read
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    assert installed.policy.calls and installed.policy.calls[0][1] == ["read"]
    assert "verifier-cannot-read" not in {i.code for i in issues}
    installed.policy.settings = {}  # the policy now hides the organization from the built-in read
    assert "verifier-cannot-read" in {i.code for i in bpm.validate(bp, allowed_roots=[tmp_path])}


def test_the_access_functions_ask_the_confinement_policy_of_the_parts(installed: Installed) -> None:
    a = api.Agent(addr="lead/rev", name="rev", parent="lead", where="agents[rev]", kind="verifier", tools=["read"], workspace="/ws")
    assert bpm.org_files_readable(a) and bpm._access(a) == "kiro read only in /ws and in the organization's own files (read-only)"
    installed.policy.settings = {}
    assert not bpm.org_files_readable(a) and bpm._access(a) == "kiro read only in /ws"


MOVED = [
    "_s", "_list", "_unknown", "_needs", "_deliverable", "_criteria", "_services", "_svc_deliverable", "_svc_criteria", "_cap", "_cfg",
    "_walk", "_within", "_default_roots", "_check_path", "_input_entries", "_verifier_inputs", "_review_required", "_has_ws_tools", "_vague",
    "_delivers_directly", "_validate_services", "_validate_request", "_parse", "_normalize", "_ORG_PLACEHOLDER",
    "_WEB_STRONG", "_WEB_WEAK", "_NO_WEB", "_CODE", "_VAGUE", "_TIERED", "_NEG_BEFORE", "_EDITS_OTHERS", "_has_plain_task",
]


def defined_in_legacy() -> set[str]:
    """The names the legacy module DEFINES at module level (an import, even under another name, defines nothing)."""
    names: set[str] = set()
    for node in ast.parse(Path(_legacy.__file__).read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(sub.id for target in targets for sub in ast.walk(target) if isinstance(sub, ast.Name))
    return names


@pytest.mark.parametrize("name", MOVED)
def test_a_private_helper_that_a_class_replaced_is_not_defined_in_the_legacy_module_any_more(name: str) -> None:
    assert name not in defined_in_legacy()


def test_what_the_legacy_module_still_defines_are_the_adapters_and_the_second_half() -> None:
    adapters = {"role_names", "get_role", "load", "load_text", "_resolve", "validate", "org_files_readable", "access_facts", "_access", "estimate",
                "planned_total", "budget_split", "service_budget", "_svc_budgets"}
    assert adapters <= defined_in_legacy() and {"ROLES_DIR", "plan_id", "render_plan", "apply", "Summary"} <= defined_in_legacy()


def test_the_constants_the_legacy_module_exports_are_the_ones_of_the_classes() -> None:
    from orgmcp.blueprint import _budgeting, _view

    assert (bpm.SLACK, bpm.TIGHT, bpm.REWORK_RUNS, bpm.KINDS) == (_budgeting.SLACK, _budgeting.TIGHT, _budgeting.REWORK_RUNS, _budgeting.KINDS)
    assert bpm.NEEDS_KEYS is _view.NEEDS_KEYS and bpm.AGENT_KEYS is _view.AGENT_KEYS and bpm.WRITE_TOOLS is _view.WRITE_TOOLS


def test_a_template_is_the_one_of_the_roles_directory_of_the_parts(installed: Installed, tmp_path: Path) -> None:
    (installed.parts.roles_dir / "poet.md").write_text("---\ntitle: Poet\nkind: author\n---\nRhyme.\n", encoding="utf-8")
    bp: dict[str, object] = {"mission": "m", "agents": [{"name": "lead", "template": "poet"}]}
    agents = bpm._resolve(bp, None, [tmp_path], [])
    assert [(a.addr, a.template and a.template.title) for a in agents] == [("lead", "Poet")]
