"""``StateDirPlaces``: where hirearchy keeps the kiro homes and working directories (docs/design/kiro-runtime-v3.md 8.1)."""

from __future__ import annotations

import os
from pathlib import Path

from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import DictEnvironment
from hirearchy.kiro._places import StateDirPlaces


def real(path: Path | str) -> Path:
    return Path(os.path.realpath(path))


def places(tmp_path: Path, variables: dict[str, str] | None = None, platform: str = "linux", org: str = "org") -> StateDirPlaces:
    environment = DictEnvironment(variables or {}, home=tmp_path / "user")
    return StateDirPlaces(OrgPaths(tmp_path / org), environment, platform)


def test_on_macos_the_state_is_under_application_support(tmp_path: Path) -> None:
    p = places(tmp_path, platform="darwin")  # "Application Support" holds a space: accepted
    state = real(tmp_path / "user" / "Library" / "Application Support" / "hirearchy")
    assert p.roots() == (state / "kiro-home", state / "kiro-cwd") and p.problem() is None


def test_elsewhere_an_absolute_xdg_state_home_is_used(tmp_path: Path) -> None:
    p = places(tmp_path, {"XDG_STATE_HOME": str(tmp_path / "xdg")})
    assert p.roots()[0] == real(tmp_path / "xdg" / "hirearchy" / "kiro-home") and p.problem() is None


def test_a_relative_xdg_state_home_is_ignored(tmp_path: Path) -> None:
    p = places(tmp_path, {"XDG_STATE_HOME": "relative/xdg"})
    assert p.roots()[0] == real(tmp_path / "user" / ".local" / "state" / "hirearchy" / "kiro-home") and p.problem() is None


def test_without_a_variable_the_fallback_is_under_the_home(tmp_path: Path) -> None:
    assert places(tmp_path).roots()[1] == real(tmp_path / "user" / ".local" / "state" / "hirearchy" / "kiro-cwd")


def test_hirearchy_state_dir_wins_on_every_platform(tmp_path: Path) -> None:
    for platform in ("darwin", "linux"):
        p = places(tmp_path, {"HIREARCHY_STATE_DIR": str(tmp_path / "st"), "XDG_STATE_HOME": str(tmp_path / "xdg")}, platform)
        assert p.roots() == (real(tmp_path / "st" / "kiro-home"), real(tmp_path / "st" / "kiro-cwd")) and p.problem() is None


def test_a_relative_state_dir_is_a_problem(tmp_path: Path) -> None:
    problem = places(tmp_path, {"HIREARCHY_STATE_DIR": "rel/state"}).problem()
    assert problem is not None and "HIREARCHY_STATE_DIR" in problem and "absolute" in problem and "\n" not in problem


def test_an_empty_state_dir_is_not_set(tmp_path: Path) -> None:
    p = places(tmp_path, {"HIREARCHY_STATE_DIR": ""})
    assert p.problem() is None and p.roots()[0].parent == real(tmp_path / "user" / ".local" / "state" / "hirearchy")


def test_a_home_that_is_the_users_home_is_a_problem(tmp_path: Path) -> None:
    home = places(tmp_path, {"HIREARCHY_STATE_DIR": str(tmp_path / "st")}).home()
    mine = StateDirPlaces(OrgPaths(tmp_path / "org"), DictEnvironment({"HIREARCHY_STATE_DIR": str(tmp_path / "st")}, home=home), "linux")
    problem = mine.problem()
    assert problem is not None and "kiro-cli would fall back to ~/.kiro" in problem and "\n" not in problem


def test_a_home_above_the_users_home_is_a_problem(tmp_path: Path) -> None:
    home = places(tmp_path, {"HIREARCHY_STATE_DIR": str(tmp_path / "st")}).home()
    deep = DictEnvironment({"HIREARCHY_STATE_DIR": str(tmp_path / "st")}, home=home / "nested" / "user")
    problem = StateDirPlaces(OrgPaths(tmp_path / "org"), deep, "linux").problem()
    assert problem is not None and "above" in problem


def test_a_refused_character_in_the_state_dir_is_the_message_m3(tmp_path: Path) -> None:
    problem = places(tmp_path, {"HIREARCHY_STATE_DIR": str(tmp_path / "s{t")}).problem()
    assert problem is not None and 's{t' in problem and 'contains "{"' in problem and "rename it" in problem


def test_a_control_character_is_written_as_hex(tmp_path: Path) -> None:
    problem = places(tmp_path, {"HIREARCHY_STATE_DIR": str(tmp_path / "s\nt")}).problem()
    assert problem is not None and "\n" not in problem and "\\x0a" in problem


def test_the_home_and_the_scratch_are_below_their_roots(tmp_path: Path) -> None:
    p = places(tmp_path)
    assert p.home().parent == p.roots()[0]
    assert p.scratch("ceo/eng").parent.parent == p.roots()[1] and p.scratch("ceo/eng").parent.name == p.home().name


def test_the_org_id_is_stable_and_distinct_for_two_org_directories(tmp_path: Path) -> None:
    a1, a2 = places(tmp_path / "a", org="org"), places(tmp_path / "a", org="org")
    b = places(tmp_path / "b", org="org")
    assert a1.home() == a2.home() and a1.home() != b.home()
    assert a1.home().name.startswith("a-org-") and len(a1.home().name.rsplit("-", 1)[1]) == 16


def test_agent_keys_differ_for_addresses_that_slug_alike(tmp_path: Path) -> None:
    p = places(tmp_path)
    assert p.scratch("a/b") != p.scratch("a-b") and p.scratch("a/b") == p.scratch("a/b")
    assert p.scratch("root").name.startswith("root-")


def test_an_agent_key_is_short(tmp_path: Path) -> None:
    assert len(places(tmp_path).scratch("a/" + "b" * 200).name) <= 40 + 1 + 8


def test_the_environment_is_asked_on_every_call(tmp_path: Path) -> None:
    environment = DictEnvironment({}, home=tmp_path / "one")
    p = StateDirPlaces(OrgPaths(tmp_path / "org"), environment, "linux")
    first = p.home()
    environment.set("HIREARCHY_STATE_DIR", str(tmp_path / "st"))
    assert p.home() != first and p.home().parent == real(tmp_path / "st" / "kiro-home")


def test_the_places_are_absolute_and_real_paths(tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "target", target_is_directory=False)
    p = places(tmp_path, {"HIREARCHY_STATE_DIR": str(link / "st")})
    assert p.home().is_absolute() and p.roots()[0] == real(tmp_path / "target" / "st" / "kiro-home")


def test_computing_the_places_touches_no_file(tmp_path: Path) -> None:
    p = places(tmp_path, {"HIREARCHY_STATE_DIR": str(tmp_path / "st")})
    before = sorted(tmp_path.rglob("*"))
    p.home(), p.scratch("x"), p.roots(), p.problem()
    assert sorted(tmp_path.rglob("*")) == before
