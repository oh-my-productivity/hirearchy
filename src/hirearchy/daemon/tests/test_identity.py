"""``SchedulerIdentity``: does a command line plausibly start the scheduler of the organization at a root?

It needs the ``run`` subcommand and either the organization's root path or a ``hirearchy`` program. A ``--root`` that is another organization (or cannot
be compared, being relative) is a no. The same directory under another spelling (macOS ``/tmp`` -> ``/private/tmp``, ``~``) is the same organization;
and the command lines of the old ``hirearchy --root X run ...`` form are still recognised."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from hirearchy.daemon._identity import SchedulerIdentity

ROOT = Path("/orgs/one")

OK = [
    "/v/bin/python /v/bin/hirearchy --root /orgs/one run",
    "/v/bin/hirearchy --root /orgs/one run --max-runs 3",
    "/v/bin/hirearchy --root /orgs/one run --until-done",
    "/v/bin/hirearchy --root=/orgs/one run",
    "/usr/bin/python3 -m hirearchy run --until-idle",  # started from inside the org (no --root)
    "python3 /x/serve.py run /orgs/one",  # the root is named, whatever the program
]
NO = [
    "sleep 60",
    "vim /orgs/one/ORG.md",
    "/v/bin/hirearchy mcp",
    "/v/bin/hirearchy --root /orgs/two run",
    "/v/bin/hirearchy --root=/orgs/two run",
    "/v/bin/hirearchy --root org run",  # relative to the other process's directory: cannot be compared
    "/v/bin/hirearchy --root=org run",
    "python -m http.server run",
    "/v/bin/hirearchy --root /orgs/one mcp",  # not the scheduler
    "",
]


@pytest.mark.parametrize("command", OK)
def test_the_command_lines_of_this_organizations_scheduler_are_recognised(command: str) -> None:
    assert SchedulerIdentity().recognises(command, ROOT) is True


@pytest.mark.parametrize("command", NO)
def test_other_command_lines_are_not(command: str) -> None:
    assert SchedulerIdentity().recognises(command, ROOT) is False


def test_another_spelling_of_the_same_directory_is_the_same_organization(tmp_path: Path) -> None:
    real = tmp_path / "real" / "org"
    real.mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "real")  # like /tmp -> /private/tmp: the command line has one spelling, the org another
    assert SchedulerIdentity().recognises(f"/v/bin/hirearchy --root {link}/org run --until-idle", real) is True
    assert SchedulerIdentity().recognises(f"/v/bin/hirearchy --root={link}/org run", real) is True
    assert SchedulerIdentity().recognises(f"/v/bin/hirearchy --root {link}/org mcp", real) is False


def test_another_directory_is_another_organization(tmp_path: Path) -> None:
    real = tmp_path / "real" / "org"
    other = tmp_path / "other"
    real.mkdir(parents=True)
    other.mkdir()
    assert SchedulerIdentity().recognises(f"/v/bin/hirearchy --root {other} run", real) is False


def test_a_root_that_the_user_spelled_with_a_home_prefix_is_expanded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    org = tmp_path / "org"
    org.mkdir()
    assert SchedulerIdentity().recognises("/v/bin/hirearchy --root ~/org run", org) is True


def test_a_root_that_cannot_be_resolved_is_not_the_organization(tmp_path: Path) -> None:
    assert SchedulerIdentity().recognises("/v/bin/hirearchy --root ~nosuchuser-zz/org run", tmp_path / "org") is False


def test_a_flag_without_a_value_does_not_name_a_root() -> None:
    assert SchedulerIdentity().recognises("/v/bin/hirearchy run --root", ROOT) is False


@pytest.mark.skipif(not Path("/tmp").is_symlink(), reason="/tmp is not a symlink on this system (it is on macOS: /tmp -> /private/tmp)")
def test_the_system_tmp_directory_and_its_real_path_are_the_same_organization() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as made:
        spelled = Path(made)  # /tmp/tmpabc
        org = spelled.resolve() / "org"  # /private/tmp/tmpabc/org
        org.mkdir()
        assert str(org) != str(spelled / "org")
        assert SchedulerIdentity().recognises(f"/v/bin/hirearchy --root {spelled}/org run --until-idle", org) is True
        assert SchedulerIdentity().recognises(f"/v/bin/hirearchy --root={spelled}/org run", org) is True
        assert SchedulerIdentity().recognises(f"/v/bin/hirearchy --root {spelled}/other run", org) is False
