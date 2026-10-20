"""The compatibility surface (README: ``orgmcp.core``, ``orgmcp.progress.progress``, ``orgmcp.main``) and the shape of ``src/orgmcp``.

Everything else of the migration is gone; what stays is stated once, in ``compat_surface.py``, and these tests pin it: it neither
shrinks nor grows by accident, and the seeded violations below prove that each check can fail.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from . import checks, compat_surface
from .paths import REPO, SRC

pytestmark = pytest.mark.architecture


def tree_of(tmp_path: Path, *modules: str) -> Path:
    root = tmp_path / "orgmcp"
    root.mkdir()
    for module in modules:
        target = root / module
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    return root


# ------------------------------------------------------------------------------------------------------------ real code


def test_the_source_tree_has_only_the_permitted_flat_modules_and_no_legacy_module():
    assert compat_surface.layout_problems(SRC) == []


def test_orgmcp_core_exports_exactly_the_recorded_names():
    import orgmcp.core

    assert compat_surface.core_problems(orgmcp.core) == []


def test_the_entry_points_are_the_console_script_and_python_dash_m():
    assert compat_surface.entry_point_problems(REPO) == []


def test_progress_is_callable_as_documented():
    assert compat_surface.progress_problems() == []


def test_the_readme_documents_the_compatibility_surface():
    assert compat_surface.readme_problems(REPO / "README.md") == []


def test_init_reexports_takes_its_exceptions_from_the_compatibility_surface(real_tree):
    assert checks.init_reexports(real_tree, compat_surface.PACKAGE_EXPORTS) == []
    bare = checks.init_reexports(real_tree)  # without the surface the one extra export of `progress` is a violation
    assert [v.where for v in bare] == ["progress.__init__"] and "progress" in bare[0].message


def test_the_only_package_with_extra_exports_is_progress():
    assert {name: set(extra) for name, extra in compat_surface.PACKAGE_EXPORTS.items()} == {"progress": {"progress"}}


# ------------------------------------------------------------------------------------------ seeded violations: each fails


def test_a_legacy_module_is_flagged_wherever_it_hides(tmp_path):
    root = tree_of(tmp_path, "__init__.py", "__main__.py", "core.py", "mail/__init__.py", "mail/_legacy.py", "health/_legacy/__init__.py")
    problems = compat_surface.layout_problems(root)
    assert any("mail/_legacy.py" in p for p in problems) and any("health/_legacy" in p for p in problems), problems


def test_a_flat_module_other_than_core_is_flagged(tmp_path):
    root = tree_of(tmp_path, "__init__.py", "__main__.py", "core.py", "server.py", "observe.py")
    problems = compat_surface.layout_problems(root)
    assert [p for p in problems if "server.py" in p] and [p for p in problems if "observe.py" in p], problems
    assert not any(p.startswith(("core.py", "__main__.py", "__init__.py")) for p in problems)


def test_a_missing_core_is_flagged(tmp_path):
    assert any("core.py" in p for p in compat_surface.layout_problems(tree_of(tmp_path, "__init__.py", "__main__.py")))


def test_a_core_that_gained_or_lost_a_name_is_flagged():
    fake = types.ModuleType("orgmcp.core")
    for name in compat_surface.CORE_NAMES - {"Org"}:
        setattr(fake, name, object())
    fake.sneaked_in = object()  # type: ignore[attr-defined]
    problems = compat_surface.core_problems(fake)
    assert any("Org" in p and "missing" in p for p in problems) and any("sneaked_in" in p for p in problems), problems


def test_an_entry_point_that_moved_is_flagged(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project.scripts]\norgmcp = "orgmcp.cli:main"\n', encoding="utf-8")
    (tmp_path / "src" / "orgmcp").mkdir(parents=True)
    (tmp_path / "src" / "orgmcp" / "__main__.py").write_text("print('hi')\n", encoding="utf-8")
    problems = compat_surface.entry_point_problems(tmp_path)
    assert any("orgmcp:main" in p for p in problems) and any("__main__" in p for p in problems), problems


def test_a_readme_that_forgot_the_surface_is_flagged(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# orgmcp\nnothing here\n", encoding="utf-8")
    problems = compat_surface.readme_problems(readme)
    assert len(problems) >= 3, problems
