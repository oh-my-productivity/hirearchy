"""``tools/relocate_tests.py``: the AST-based mover of ``tests/test_*.py`` into their destinations (ARCHITECTURE.md 7.3, step E0).

The unit tests work on small synthetic repositories (``make_repo``); the last tests run the tool on the real sources of this repository.
"""

from __future__ import annotations

import ast
import itertools
import shutil
import textwrap
from pathlib import Path
from typing import Any

import pytest

from . import relocate_tool
from .paths import REPO

pytestmark = pytest.mark.architecture

RED = pytest.mark.xfail(strict=True, reason="red: E0")

# One source file that exercises everything: imports, a constant, a __file__ path, helpers, fixtures (one needs the other), a comment,
# a parametrized test. Its tests go to four destinations in four groups.
SOURCE = '''\
"""Tests of everything."""
import json
import os
from pathlib import Path

import pytest

LIMIT = 3
FAKE = str(Path(__file__).with_name("fake_agent.py"))


def double(x):
    return 2 * x


def triple(x):
    return double(x) + x


@pytest.fixture
def box(tmp_path):
    return tmp_path / "box"


@pytest.fixture
def tall(box):
    return box / "tall"


def test_alpha(tall):
    assert triple(LIMIT) == 9 and tall


# a comment that belongs to beta
def test_beta():
    assert json.dumps(1) == "1"


@pytest.mark.parametrize("n", [1, 2, 3])
def test_gamma(n):
    assert os.sep and double(n)


def test_delta():
    assert FAKE
'''

BUDGET = "src/orgmcp/budget/tests/test_alpha.py"  # group b
KERNEL = "src/orgmcp/kernel/tests/test_beta.py"  # group a
HEALTH = "src/orgmcp/health/tests/test_gamma.py"  # group c
E2E = "tests/e2e/test_delta.py"  # group e

SPLIT = {
    BUDGET: ("b", {"tests/test_synth.py": ["test_alpha"]}),
    KERNEL: ("a", {"tests/test_synth.py": ["test_beta"]}),
    HEALTH: ("c", {"tests/test_synth.py": [{"test_gamma": 3}]}),
    E2E: ("e", {"tests/test_synth.py": ["test_delta"]}),
}


def manifest_dict(destinations: dict[str, tuple[str, dict[str, list[Any]]]]) -> dict[str, Any]:
    return {"version": 1, "destinations": {dest: {"group": group, "sources": sources} for dest, (group, sources) in destinations.items()}}


def make_repo(tmp_path: Path, sources: dict[str, str], existing: dict[str, str] | None = None) -> Path:
    repo = tmp_path / "repo"
    for pkg in ("kernel", "budget", "health", "blueprint", "scheduler"):
        (repo / "src" / "orgmcp" / pkg).mkdir(parents=True)
        (repo / "src" / "orgmcp" / pkg / "__init__.py").write_text("", encoding="utf-8")
    (repo / "tests").mkdir()
    for name, text in {**{f"tests/{n}": t for n, t in sources.items()}, **(existing or {})}.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return repo


def tree(repo: Path) -> dict[str, str]:
    return {p.relative_to(repo).as_posix(): p.read_text(encoding="utf-8") for p in sorted(repo.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def names(text: str) -> set[str]:
    """Every name a module defines at its top level (functions, classes, assignments) - and the names of the test methods."""
    found: set[str] = set()
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.add(node.name)
        elif isinstance(node, ast.Assign):
            found.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return found


def imports(text: str) -> set[str]:
    found: set[str] = set()
    for node in ast.parse(text).body:
        if isinstance(node, ast.Import):
            found.update(a.asname or a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.update(a.asname or a.name for a in node.names)
    return found


def order(text: str, *wanted: str) -> list[str]:
    """``wanted`` in the order in which the module defines them."""
    return [n.name for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in wanted]


@pytest.fixture(scope="module")
def tool():  # type: ignore[no-untyped-def]
    return relocate_tool.load()


@pytest.fixture
def synth(tmp_path, tool):  # type: ignore[no-untyped-def]
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE})
    return repo, tool.Manifest.from_dict(manifest_dict(SPLIT))


def run(tool, repo: Path, manifest, verb: str, *groups: str) -> None:  # type: ignore[no-untyped-def]
    for group in groups:
        getattr(tool, f"{verb}_group")(repo, manifest, group)


# ----------------------------------------------------------------------------------------------------------------------------------
# plan


@RED
def test_the_plan_counts_tests_per_group_and_destination(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    plan = tool.make_plan(repo, manifest)
    text = plan.render()
    assert plan.errors == []
    assert "4 tests (6 collected)" in text and "4 destinations" in text
    assert "group b: 1 tests (1 collected) in 1 destinations" in text
    assert "group c: 1 tests (3 collected) in 1 destinations" in text
    assert f"{BUDGET} (new, 1 tests, 1 collected) <- tests/test_synth.py" in text


@RED
def test_a_test_that_no_destination_claims_is_an_error(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE})
    partial = {BUDGET: SPLIT[BUDGET], KERNEL: SPLIT[KERNEL], HEALTH: SPLIT[HEALTH]}
    plan = tool.make_plan(repo, tool.Manifest.from_dict(manifest_dict(partial)))
    assert any("unassigned" in e and "tests/test_synth.py::test_delta" in e for e in plan.errors), plan.errors


@RED
def test_a_test_claimed_twice_is_an_error(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE})
    twice = {**SPLIT, "src/orgmcp/budget/tests/test_again.py": ("b", {"tests/test_synth.py": ["test_alpha"]})}
    plan = tool.make_plan(repo, tool.Manifest.from_dict(manifest_dict(twice)))
    assert any("twice" in e and "test_alpha" in e for e in plan.errors), plan.errors


@RED
def test_a_test_that_exists_nowhere_is_an_error(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE})
    ghost = {**SPLIT, "src/orgmcp/budget/tests/test_ghost.py": ("b", {"tests/test_synth.py": ["test_vanished"]})}
    plan = tool.make_plan(repo, tool.Manifest.from_dict(manifest_dict(ghost)))
    assert any("test_vanished" in e and "nowhere" in e for e in plan.errors), plan.errors


@RED
def test_the_group_of_a_destination_is_the_group_of_its_package(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE})
    wrong = {**SPLIT, BUDGET: ("a", SPLIT[BUDGET][1])}
    plan = tool.make_plan(repo, tool.Manifest.from_dict(manifest_dict(wrong)))
    assert any(BUDGET in e and "group" in e and "'b'" in e for e in plan.errors), plan.errors


@RED
def test_a_destination_outside_the_known_places_is_an_error(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE})
    bad = {**SPLIT, E2E: ("e", SPLIT[E2E][1]), "src/orgmcp/nowhere/tests/test_x.py": ("a", {"tests/test_synth.py": ["test_beta"]})}
    del bad[KERNEL]
    plan = tool.make_plan(repo, tool.Manifest.from_dict(manifest_dict(bad)))
    assert any("nowhere" in e for e in plan.errors), plan.errors


@RED
def test_a_manifest_that_repeats_a_key_is_refused(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "m.yaml"
    path.write_text("version: 1\ndestinations:\n  a/b.py: {group: a, sources: {}}\n  a/b.py: {group: a, sources: {}}\n", encoding="utf-8")
    with pytest.raises(tool.ManifestError, match="duplicate"):
        tool.load_manifest(path)


# ----------------------------------------------------------------------------------------------------------------------------------
# apply: what moves and what goes with it


@RED
def test_a_test_takes_its_fixtures_and_helpers_with_it_and_keeps_source_order(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "apply", "b")
    text = (repo / BUDGET).read_text(encoding="utf-8")
    assert names(text) == {"LIMIT", "double", "triple", "box", "tall", "test_alpha"}
    assert order(text, "double", "triple", "box", "tall", "test_alpha") == ["double", "triple", "box", "tall", "test_alpha"]
    assert "def test_alpha(tall):\n    assert triple(LIMIT) == 9 and tall\n" in text  # moved verbatim


@RED
def test_the_destination_imports_only_what_it_uses(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "apply", "b", "a", "c")
    assert imports((repo / BUDGET).read_text(encoding="utf-8")) == {"pytest"}
    assert imports((repo / KERNEL).read_text(encoding="utf-8")) == {"json"}
    assert imports((repo / HEALTH).read_text(encoding="utf-8")) == {"os", "pytest"}


@RED
def test_decorators_comments_and_parametrize_move_with_the_test(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "apply", "c", "a")
    assert '@pytest.mark.parametrize("n", [1, 2, 3])\ndef test_gamma(n):' in (repo / HEALTH).read_text(encoding="utf-8")
    assert "# a comment that belongs to beta\ndef test_beta():" in (repo / KERNEL).read_text(encoding="utf-8")


@RED
def test_a_helper_that_several_destinations_need_is_copied_to_each(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "apply", "b", "c")
    assert "def double(x):" in (repo / BUDGET).read_text(encoding="utf-8")
    assert "def double(x):" in (repo / HEALTH).read_text(encoding="utf-8")


@RED
def test_the_source_loses_what_nothing_needs_any_more(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "apply", "b")
    left = (repo / "tests/test_synth.py").read_text(encoding="utf-8")
    assert names(left) == {"FAKE", "double", "test_beta", "test_gamma", "test_delta"}  # triple, box, tall, LIMIT went with alpha
    assert imports(left) == {"json", "os", "Path", "pytest"}
    assert left.startswith('"""Tests of everything."""')
    run(tool, repo, manifest, "apply", "a", "c")
    assert names((repo / "tests/test_synth.py").read_text(encoding="utf-8")) == {"FAKE", "test_delta"}
    assert imports((repo / "tests/test_synth.py").read_text(encoding="utf-8")) == {"Path"}


@RED
def test_a_source_without_tests_is_deleted(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "apply", "a", "b", "c", "e")
    assert not (repo / "tests/test_synth.py").exists()


@RED
def test_an_autouse_fixture_goes_with_every_test_of_its_module(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = textwrap.dedent('''\
        import pytest


        @pytest.fixture(autouse=True)
        def clean_env(monkeypatch):
            monkeypatch.delenv("X", raising=False)


        def test_one():
            assert True


        def test_two():
            assert True
        ''')
    repo = make_repo(tmp_path, {"test_auto.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({
        BUDGET: ("b", {"tests/test_auto.py": ["test_one"]}), KERNEL: ("a", {"tests/test_auto.py": ["test_two"]})}))
    run(tool, repo, manifest, "apply", "b")
    assert "def clean_env(monkeypatch):" in (repo / BUDGET).read_text(encoding="utf-8")
    assert "def clean_env(monkeypatch):" in (repo / "tests/test_auto.py").read_text(encoding="utf-8")  # test_two still needs it
    run(tool, repo, manifest, "apply", "a")
    assert "def clean_env(monkeypatch):" in (repo / KERNEL).read_text(encoding="utf-8")


@RED
def test_a_fixture_given_a_name_is_found_by_that_name(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = textwrap.dedent('''\
        import pytest


        @pytest.fixture(name="thing")
        def make_thing():
            return 1


        def test_one(thing):
            assert thing
        ''')
    repo = make_repo(tmp_path, {"test_named.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({BUDGET: ("b", {"tests/test_named.py": ["test_one"]})}))
    run(tool, repo, manifest, "apply", "b")
    assert 'name="thing"' in (repo / BUDGET).read_text(encoding="utf-8")


@RED
def test_a_test_class_is_split_by_method_and_keeps_its_other_members(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = textwrap.dedent('''\
        import pytest


        @pytest.mark.integration
        class TestBox:
            LIMIT = 2

            def helper(self):
                return self.LIMIT

            def test_one(self):
                assert self.helper() == 2

            def test_two(self):
                assert self.LIMIT
        ''')
    repo = make_repo(tmp_path, {"test_cls.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({
        BUDGET: ("b", {"tests/test_cls.py": ["TestBox::test_one"]}), KERNEL: ("a", {"tests/test_cls.py": ["TestBox::test_two"]})}))
    run(tool, repo, manifest, "apply", "b")
    one = (repo / BUDGET).read_text(encoding="utf-8")
    assert "@pytest.mark.integration\nclass TestBox:" in one and "def test_one(self):" in one and "def test_two" not in one
    assert "def helper(self):" in one and "LIMIT = 2" in one
    left = (repo / "tests/test_cls.py").read_text(encoding="utf-8")
    assert "def test_two(self):" in left and "def test_one" not in left
    run(tool, repo, manifest, "apply", "a")
    assert "def test_two(self):" in (repo / KERNEL).read_text(encoding="utf-8") and not (repo / "tests/test_cls.py").exists()


@RED
def test_an_async_test_moves_like_any_other(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = "async def press(app):\n    return app\n\n\nasync def test_one():\n    assert await press(1)\n"
    repo = make_repo(tmp_path, {"test_async.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({BUDGET: ("b", {"tests/test_async.py": ["test_one"]})}))
    run(tool, repo, manifest, "apply", "b")
    assert names((repo / BUDGET).read_text(encoding="utf-8")) == {"press", "test_one"}


@RED
def test_the_module_marks_go_with_a_source_that_has_its_destination_to_itself(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = "import pytest\n\npytestmark = pytest.mark.integration\n\n\ndef test_one():\n    assert True\n\n\ndef test_two():\n    assert True\n"
    repo = make_repo(tmp_path, {"test_marked.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({
        BUDGET: ("b", {"tests/test_marked.py": ["test_one"]}), KERNEL: ("a", {"tests/test_marked.py": ["test_two"]})}))
    run(tool, repo, manifest, "apply", "b", "a")
    assert "pytestmark = pytest.mark.integration" in (repo / BUDGET).read_text(encoding="utf-8")
    assert "pytestmark = pytest.mark.integration" in (repo / KERNEL).read_text(encoding="utf-8")


@RED
def test_module_marks_cannot_be_merged_into_a_destination_that_holds_other_tests(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    marked = "import pytest\n\npytestmark = pytest.mark.integration\n\n\ndef test_one():\n    assert True\n"
    repo = make_repo(tmp_path, {"test_marked.py": marked, "test_plain.py": "def test_two():\n    assert True\n"})
    manifest = tool.Manifest.from_dict(manifest_dict({
        BUDGET: ("b", {"tests/test_marked.py": ["test_one"], "tests/test_plain.py": ["test_two"]})}))
    with pytest.raises(tool.RelocationError, match="pytestmark"):
        tool.apply_group(repo, manifest, "b")
    assert (repo / "tests/test_marked.py").exists() and not (repo / BUDGET).exists()


@RED
def test_two_sources_share_a_destination_and_a_helper_with_the_same_text(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    one = "def helper():\n    return 1\n\n\ndef test_one():\n    assert helper()\n"
    two = "def helper():\n    return 1\n\n\ndef test_two():\n    assert helper()\n"
    repo = make_repo(tmp_path, {"test_one.py": one, "test_two.py": two})
    manifest = tool.Manifest.from_dict(manifest_dict({
        BUDGET: ("b", {"tests/test_one.py": ["test_one"], "tests/test_two.py": ["test_two"]})}))
    run(tool, repo, manifest, "apply", "b")
    text = (repo / BUDGET).read_text(encoding="utf-8")
    assert text.count("def helper") == 1 and order(text, "test_one", "test_two") == ["test_one", "test_two"]


@RED
def test_two_sources_with_different_helpers_of_one_name_cannot_share_a_destination(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    one = "def helper():\n    return 1\n\n\ndef test_one():\n    assert helper()\n"
    two = "def helper():\n    return 2\n\n\ndef test_two():\n    assert helper()\n"
    repo = make_repo(tmp_path, {"test_one.py": one, "test_two.py": two})
    manifest = tool.Manifest.from_dict(manifest_dict({
        BUDGET: ("b", {"tests/test_one.py": ["test_one"], "tests/test_two.py": ["test_two"]})}))
    with pytest.raises(tool.RelocationError, match="helper"):
        tool.apply_group(repo, manifest, "b")
    assert (repo / "tests/test_one.py").exists() and not (repo / BUDGET).exists()


# ----------------------------------------------------------------------------------------------------------------------------------
# apply: paths, existing destinations, clashes


@RED
def test_paths_relative_to_the_source_file_become_testkit_constants(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = textwrap.dedent('''\
        from pathlib import Path

        FAKE = str(Path(__file__).with_name("fake_agent.py"))
        TEAM = str(Path(__file__).resolve().with_name("fake_team_agent.py"))
        EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "blueprint-research.yaml"
        SKILL = (Path(__file__).resolve().parent.parent / "skills" / "orgmcp" / "SKILL.md").read_text()
        EXPECTED = Path(__file__).parent / "expected_dash"
        HERE = Path(__file__).parent


        def test_one():
            assert FAKE and TEAM and EXAMPLE and SKILL and EXPECTED and HERE
        ''')
    repo = make_repo(tmp_path, {"test_paths.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({E2E: ("e", {"tests/test_paths.py": ["test_one"]})}))
    run(tool, repo, manifest, "apply", "e")
    text = (repo / E2E).read_text(encoding="utf-8")
    assert 'FAKE = str(testkit.FAKE_AGENT)' in text and 'TEAM = str(testkit.FAKE_TEAM_AGENT)' in text
    assert 'EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"' in text
    assert 'SKILL = (testkit.REPO / "skills" / "orgmcp" / "SKILL.md").read_text()' in text
    assert "EXPECTED = testkit.EXPECTED_DASH" in text and "HERE = testkit.TESTS" in text
    assert "__file__" not in text and imports(text) == {"testkit"}


@RED
def test_the_old_places_of_the_support_modules_are_known_too(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Before the support modules moved into tests/testkit/ the same constants were spelled with the old file names."""
    source = 'from pathlib import Path\n\nFAKE = str(Path(__file__).with_name("fake_agent.py"))\n\n\ndef test_one():\n    assert FAKE\n'
    repo = make_repo(tmp_path, {"test_old.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({E2E: ("e", {"tests/test_old.py": ["test_one"]})}))
    run(tool, repo, manifest, "apply", "e")
    assert "FAKE = str(testkit.FAKE_AGENT)" in (repo / E2E).read_text(encoding="utf-8")


@RED
@pytest.mark.parametrize("expression", [
    "os.path.dirname(__file__)", "Path(__file__).read_text()", "Path(__file__).parent.parent.parent / 'elsewhere'", "open(__file__)"])
def test_a_use_of_file_the_tool_cannot_rewrite_is_an_error(tool, tmp_path, expression) -> None:  # type: ignore[no-untyped-def]
    source = f"import os\nfrom pathlib import Path\n\nWHERE = {expression}\n\n\ndef test_one():\n    assert WHERE\n"
    repo = make_repo(tmp_path, {"test_odd.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({E2E: ("e", {"tests/test_odd.py": ["test_one"]})}))
    with pytest.raises(tool.RelocationError, match="__file__"):
        tool.apply_group(repo, manifest, "e")
    assert not (repo / E2E).exists() and (repo / "tests/test_odd.py").read_text(encoding="utf-8") == source


@RED
def test_new_test_directories_become_packages(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "apply", "b", "e")
    assert (repo / "src/orgmcp/budget/tests/__init__.py").is_file() and (repo / "tests/e2e/__init__.py").is_file()


@RED
def test_an_existing_destination_is_extended_never_overwritten(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    existing = "import os\n\n\ndef helper_there():\n    return os.sep\n\n\ndef test_existing():\n    assert helper_there()\n"
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE}, {BUDGET: existing, "src/orgmcp/budget/tests/__init__.py": ""})
    manifest = tool.Manifest.from_dict(manifest_dict(SPLIT))
    run(tool, repo, manifest, "apply", "b")
    text = (repo / BUDGET).read_text(encoding="utf-8")
    assert "def helper_there():\n    return os.sep\n\n\ndef test_existing():\n    assert helper_there()\n" in text
    assert order(text, "test_existing", "test_alpha")[-1] == "test_alpha" and {"double", "triple", "box", "tall"} <= names(text)
    assert imports(text) == {"os", "pytest"}


@RED
def test_a_test_name_that_the_destination_already_has_is_an_error(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    existing = "def test_alpha():\n    assert False\n"
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE}, {BUDGET: existing, "src/orgmcp/budget/tests/__init__.py": ""})
    manifest = tool.Manifest.from_dict(manifest_dict(SPLIT))
    before = tree(repo)
    with pytest.raises(tool.RelocationError, match="test_alpha") as caught:
        tool.apply_group(repo, manifest, "b")
    assert "already" in str(caught.value) and tree(repo) == before  # nothing was written


@RED
def test_a_helper_name_that_the_destination_defines_differently_is_an_error(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    existing = "def double(x):\n    return x * 3\n"
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE}, {BUDGET: existing, "src/orgmcp/budget/tests/__init__.py": ""})
    manifest = tool.Manifest.from_dict(manifest_dict(SPLIT))
    with pytest.raises(tool.RelocationError, match="double"):
        tool.apply_group(repo, manifest, "b")


@RED
def test_a_top_level_statement_the_tool_does_not_understand_is_an_error(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = "import os\n\nif os.name == 'nt':\n    X = 1\n\n\ndef test_one():\n    assert os\n"
    repo = make_repo(tmp_path, {"test_if.py": source})
    manifest = tool.Manifest.from_dict(manifest_dict({BUDGET: ("b", {"tests/test_if.py": ["test_one"]})}))
    with pytest.raises(tool.RelocationError, match="test_if.py"):
        tool.apply_group(repo, manifest, "b")


# ----------------------------------------------------------------------------------------------------------------------------------
# prune, idempotence, order


@RED
def test_prune_removes_from_the_source_and_writes_no_destination(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, "prune", "b")
    assert not (repo / BUDGET).exists() and not (repo / "src/orgmcp/budget/tests").exists()
    assert "test_alpha" not in (repo / "tests/test_synth.py").read_text(encoding="utf-8")


@RED
def test_prune_gives_the_source_that_apply_gives(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The manager resolves a merge conflict in a shared source by taking the integration version and re-running ``prune``."""
    applied = make_repo(tmp_path / "applied", {"test_synth.py": SOURCE})
    pruned = make_repo(tmp_path / "pruned", {"test_synth.py": SOURCE})
    manifest = tool.Manifest.from_dict(manifest_dict(SPLIT))
    run(tool, applied, manifest, "apply", "b", "c")
    run(tool, pruned, manifest, "prune", "b", "c")
    assert tree(pruned)["tests/test_synth.py"] == tree(applied)["tests/test_synth.py"]


@RED
@pytest.mark.parametrize("verb", ["apply", "prune"])
def test_running_a_group_twice_changes_nothing(tool, synth, verb) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    run(tool, repo, manifest, verb, "b", "c")
    once = tree(repo)
    run(tool, repo, manifest, verb, "b", "c")
    assert tree(repo) == once


@RED
def test_the_groups_can_be_applied_in_any_order(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    manifest = tool.Manifest.from_dict(manifest_dict(SPLIT))
    results = []
    for i, groups in enumerate(itertools.permutations("abce")):
        repo = make_repo(tmp_path / str(i), {"test_synth.py": SOURCE})
        run(tool, repo, manifest, "apply", *groups)
        results.append(tree(repo))
    assert all(result == results[0] for result in results)


@RED
def test_the_groups_can_be_pruned_in_any_order_and_half_way(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    manifest = tool.Manifest.from_dict(manifest_dict(SPLIT))
    first = make_repo(tmp_path / "x", {"test_synth.py": SOURCE})
    second = make_repo(tmp_path / "y", {"test_synth.py": SOURCE})
    run(tool, first, manifest, "prune", "c", "b")
    run(tool, second, manifest, "prune", "b", "c")
    assert tree(first) == tree(second)
    assert "test_delta" in tree(first)["tests/test_synth.py"]  # groups a and e were not touched


@RED
def test_a_dry_run_changes_nothing(tool, synth) -> None:  # type: ignore[no-untyped-def]
    repo, manifest = synth
    before = tree(repo)
    changes = tool.apply_group(repo, manifest, "b", dry_run=True)
    assert tree(repo) == before and {c.path for c in changes} >= {BUDGET, "tests/test_synth.py"}


# ----------------------------------------------------------------------------------------------------------------------------------
# command line


@RED
def test_the_command_line_plans_applies_and_prunes(tool, synth, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    repo, _ = synth
    manifest_path = tmp_path / "relocation.yaml"
    import yaml

    manifest_path.write_text(yaml.safe_dump(manifest_dict(SPLIT)), encoding="utf-8")
    common = ["--repo", str(repo), "--manifest", str(manifest_path)]
    assert tool.main(["plan", *common]) == 0
    assert "group b: 1 tests" in capsys.readouterr().out
    assert tool.main(["apply", "--group", "b", *common]) == 0
    assert (repo / BUDGET).is_file()
    assert tool.main(["prune", "--group", "c", *common]) == 0
    assert not (repo / HEALTH).exists() and "test_gamma" not in (repo / "tests/test_synth.py").read_text(encoding="utf-8")


@RED
def test_the_command_line_exits_non_zero_and_says_why(tool, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    repo = make_repo(tmp_path, {"test_synth.py": SOURCE})
    import yaml

    manifest_path = tmp_path / "relocation.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest_dict({BUDGET: SPLIT[BUDGET]})), encoding="utf-8")
    assert tool.main(["plan", "--repo", str(repo), "--manifest", str(manifest_path)]) == 1
    assert "unassigned" in capsys.readouterr().out
    assert tool.main(["apply", "--group", "z", "--repo", str(repo), "--manifest", str(manifest_path)]) != 0


# ----------------------------------------------------------------------------------------------------------------------------------
# the tool on the real sources


def real_copy(tool, tmp_path: Path) -> tuple[Path, Any]:  # type: ignore[no-untyped-def]
    """A copy of the sources of ``tests/test_*.py`` and of the destinations that exist already, enough for the tool to work on."""
    manifest = tool.load_manifest(relocate_tool.MANIFEST)
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    for source in sorted((REPO / "tests").glob("test_*.py")):
        shutil.copy(source, repo / "tests" / source.name)
    for destination in manifest.destinations:
        package = Path(destination).parts[:3]
        if package[0] == "src":
            (repo / Path(*package)).mkdir(parents=True, exist_ok=True)
            (repo / Path(*package) / "__init__.py").touch()
        if (REPO / destination).is_file():
            (repo / destination).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / destination, repo / destination)
    return repo, manifest


@RED
def test_the_real_manifest_makes_a_clean_plan(tool) -> None:  # type: ignore[no-untyped-def]
    plan = tool.make_plan(REPO, tool.load_manifest(relocate_tool.MANIFEST))
    assert plan.errors == []


@RED
def test_applying_the_real_groups_in_two_orders_gives_the_same_tree(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    forward, manifest = real_copy(tool, tmp_path / "forward")
    backward, _ = real_copy(tool, tmp_path / "backward")
    run(tool, forward, manifest, "apply", "a", "b")
    run(tool, backward, manifest, "apply", "b", "a")
    assert tree(forward) == tree(backward)
    run(tool, forward, manifest, "apply", "c", "d", "e")
    run(tool, backward, manifest, "apply", "e", "d", "c")
    assert tree(forward) == tree(backward)
    assert not list((forward / "tests").glob("test_*.py"))  # every source is empty and gone
    for path, text in tree(forward).items():
        if path.endswith(".py"):
            compile(text, path, "exec")  # every produced file is valid Python


@RED
def test_pruning_the_real_sources_in_two_orders_gives_the_same_tree(tool, tmp_path) -> None:  # type: ignore[no-untyped-def]
    one, manifest = real_copy(tool, tmp_path / "one")
    two, _ = real_copy(tool, tmp_path / "two")
    run(tool, one, manifest, "prune", "c", "e", "a")
    run(tool, two, manifest, "prune", "a", "c", "e")
    assert tree(one) == tree(two)
    once = tree(one)
    run(tool, one, manifest, "prune", "c", "e", "a")
    assert tree(one) == once


def test_the_tool_is_dev_tooling_that_nothing_in_src_imports() -> None:
    offenders = []
    for path in sorted((REPO / "src").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            if any(m.split(".")[0] in ("tools", "relocate_tests") for m in modules):
                offenders.append(str(path.relative_to(REPO)))
    assert offenders == []
