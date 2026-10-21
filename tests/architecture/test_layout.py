import tomllib

import testkit

ROOT = testkit.REPO
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_colocated_test_directories_are_packages():
    """Two features may both have ``tests/test_api.py``: that works only when each ``tests/`` is a package (pytest then
    names the modules ``hirearchy.<feature>.tests.test_api`` instead of ``test_api``)."""
    missing = [str(d.relative_to(ROOT)) for d in sorted((ROOT / "src" / "hirearchy").rglob("tests")) if d.is_dir()
               and not (d / "__init__.py").is_file()]
    assert not missing, f"add an __init__.py to: {missing}"


def test_the_wheel_excludes_every_tests_directory_under_src():
    wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert "**/tests/**" in wheel["exclude"]


def test_pytest_collects_tests_dir_and_src():
    ini = PYPROJECT["tool"]["pytest"]["ini_options"]
    assert ini["testpaths"] == ["tests", "src/hirearchy"] and ini["pythonpath"] == ["tests"]
