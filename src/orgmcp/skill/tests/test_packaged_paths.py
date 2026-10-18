"""Risk 8 of ARCHITECTURE.md (path arithmetic that depends on file depth): the skill is found from a checkout AND from a wheel.

The values are those of ``main``: ``orgmcp/_skill/SKILL.md`` next to the package (the wheel) and ``<package>/../../skills/orgmcp/
SKILL.md`` (the checkout), computed from the package directory, not from the file that holds the code. A real wheel was built with
``uv build`` and inspected by hand (see the report of the step); here its layout is rebuilt from the ``force-include`` table of
``pyproject.toml`` so that the test needs no network and no build backend.
"""

from __future__ import annotations

import importlib.util
import shutil
import tomllib
from pathlib import Path

from orgmcp.skill import skill_source
from orgmcp.skill._source import PackagedSkillSource

REPO = Path(__file__).resolve().parents[4]


def orgmcp_dir() -> Path:
    """The directory of the ``orgmcp`` package as the import system knows it (the root package is not imported here)."""
    spec = importlib.util.find_spec("orgmcp")
    assert spec is not None and spec.origin is not None
    return Path(spec.origin).resolve().parent


PACKAGE = orgmcp_dir()
SHIPPED = REPO / "skills" / "orgmcp" / "SKILL.md"


def force_include() -> dict[str, str]:
    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    table: dict[str, str] = config["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    return table


def test_the_legacy_function_resolves_to_the_value_of_main() -> None:
    assert skill_source() == PACKAGE.parent.parent / "skills" / "orgmcp" / "SKILL.md"  # main: here.parent.parent / "skills" / ...
    assert skill_source() == SHIPPED.resolve()


def test_the_wheel_ships_the_skill_beside_the_package() -> None:
    assert force_include() == {"skills/orgmcp/SKILL.md": "orgmcp/_skill/SKILL.md"}


def test_the_source_of_a_checkout_resolves_to_the_value_of_main() -> None:
    assert PackagedSkillSource(PACKAGE).path() == PACKAGE.parent.parent / "skills" / "orgmcp" / "SKILL.md"


def test_the_source_of_a_wheel_resolves_to_the_forced_file(tmp_path: Path) -> None:
    site = tmp_path / "site-packages"
    for shipped, destination in force_include().items():
        (site / destination).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / shipped, site / destination)
    (site / "orgmcp").mkdir(exist_ok=True)
    source = PackagedSkillSource(site / "orgmcp")
    assert source.path() == (site / "orgmcp" / "_skill" / "SKILL.md").resolve()
    assert source.read() == SHIPPED.read_text(encoding="utf-8")


def test_the_wheel_copy_is_found_even_when_no_checkout_is_above_it(tmp_path: Path) -> None:
    site = tmp_path / "a" / "b" / "c" / "site-packages"
    (site / "orgmcp" / "_skill").mkdir(parents=True)
    (site / "orgmcp" / "_skill" / "SKILL.md").write_text("wheel", encoding="utf-8")
    assert PackagedSkillSource(site / "orgmcp").read() == "wheel"
