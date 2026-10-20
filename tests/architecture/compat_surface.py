"""The permanent compatibility surface of orgmcp, stated once (ARCHITECTURE.md 6.5), and the checks that keep it exactly that.

Everything the migration needed is gone; what a user, a script or a kiro profile can still rely on is:

* ``orgmcp.core`` -- the facade module (``Org``, ``DEFAULT_MODEL``, ``Message``, ``OrgError``, ...). Every public name is permanent and
  documented in the README; ``CORE_NAMES`` records them, so a name can neither disappear nor be added without editing this file.
* ``orgmcp.progress.progress(org, task_id=None)`` -- the Python entry point of the progress report (README). It is the one name that the
  ``__init__`` of a package exports besides its ``api`` (``PACKAGE_EXPORTS``: rule R1, ``checks.init_reexports``, takes its exceptions
  from here).
* ``orgmcp.main`` -- the console script (``orgmcp = "orgmcp:main"``) and ``python -m orgmcp``.

And the shape of ``src/orgmcp``: the only flat modules are ``__init__``, ``__main__`` and ``core``, and no module named ``_legacy``
exists anywhere (the strangler phase is over; a new flat module or a ``_legacy`` shim is a new, unreviewed public surface).
"""

from __future__ import annotations

import inspect
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

from .paths import SRC

FLAT_MODULES = frozenset({"__init__.py", "__main__.py", "core.py"})
FORBIDDEN_MODULE_NAMES = frozenset({"_legacy"})

CORE_NAMES = frozenset({
    "BOXES", "DEFAULT_CONFIG", "DEFAULT_MODEL", "LESSONS_MAX_CHARS", "MESSAGE_TYPES", "Message", "NAME_RE", "Org", "OrgError", "Path",
    "RENDER_BODY_CHARS", "RESERVED", "RESULT_STATUSES", "ROOT", "RUNTIME", "RUNTIME_NAMES", "Retired", "annotations", "atomic_write",
    "charter_change_note", "config_default_model", "datetime", "join_frontmatter", "latest_results", "os", "process_resources", "secrets",
    "split_frontmatter", "telemetry", "templates", "timezone", "utcnow", "word_count",
})

# package -> the names its __init__ exports in addition to api.__all__
PACKAGE_EXPORTS: Mapping[str, frozenset[str]] = {"progress": frozenset({"progress"})}

# What the README must say about the surface (a fragment each).
README_MENTIONS = ("orgmcp.core", "orgmcp.progress.progress", "orgmcp.core.Org")


def layout_problems(src: Path = SRC) -> list[str]:
    """Flat modules other than ``__init__``/``__main__``/``core`` and modules named ``_legacy`` (file or package) under ``src``."""
    problems = []
    flat = {p.name for p in src.glob("*.py")}
    problems += [f"{name}: a flat module under {src.name}/ (only {', '.join(sorted(FLAT_MODULES))} may exist; "
                 "a feature is a package with an api.py)" for name in sorted(flat - FLAT_MODULES)]
    problems += [f"{name}: the compatibility facade module is missing" for name in sorted(FLAT_MODULES - flat)]
    for path in sorted(src.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(src)
        if path.stem in FORBIDDEN_MODULE_NAMES and (path.suffix == ".py" or path.is_dir()):
            problems.append(f"{relative.as_posix()}: no module is named {path.stem} any more (the migration layer is gone)")
    return problems


def core_problems(core: ModuleType) -> list[str]:
    """Public names of ``orgmcp.core`` that are missing from, or not recorded in, ``CORE_NAMES``."""
    public = {name for name in vars(core) if not name.startswith("_")}
    return [f"orgmcp.core.{name} is missing: the facade module keeps every name" for name in sorted(CORE_NAMES - public)] + \
           [f"orgmcp.core.{name} is public but not recorded in compat_surface.CORE_NAMES" for name in sorted(public - CORE_NAMES)]


def entry_point_problems(repo: Path) -> list[str]:
    """The console script is ``orgmcp:main`` and ``python -m orgmcp`` runs it."""
    problems = []
    scripts = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8")).get("project", {}).get("scripts", {})
    if scripts.get("orgmcp") != "orgmcp:main":
        problems.append(f"[project.scripts] orgmcp must be 'orgmcp:main', is {scripts.get('orgmcp')!r}")
    main_module = repo / "src" / "orgmcp" / "__main__.py"
    text = main_module.read_text(encoding="utf-8") if main_module.is_file() else ""
    if not (re.search(r"from \. import main\b", text) and re.search(r"^main\(\)", text, re.MULTILINE)):
        problems.append("src/orgmcp/__main__.py must be 'from . import main' followed by 'main()'")
    return problems


def progress_problems() -> list[str]:
    """``orgmcp.progress.progress(org, task_id=None)`` exists with the documented signature; ``orgmcp.main`` is callable."""
    import orgmcp
    import orgmcp.progress

    problems = []
    if not callable(orgmcp.main):
        problems.append("orgmcp.main is not callable")
    function = getattr(orgmcp.progress, "progress", None)
    if not callable(function):
        return [*problems, "orgmcp.progress.progress is missing"]
    parameters = list(inspect.signature(function).parameters.values())
    if [p.name for p in parameters[:2]] != ["org", "task_id"] or parameters[1].default is not None:
        problems.append("orgmcp.progress.progress must start with (org, task_id=None)")
    return problems


def readme_problems(readme: Path) -> list[str]:
    text = readme.read_text(encoding="utf-8")
    return [f"README.md does not mention {fragment}" for fragment in README_MENTIONS if fragment not in text]
