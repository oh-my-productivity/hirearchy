"""The wiring of ``bootstrap`` and of the facade's ``Org.init``: the runtime carries the real initializer, and the whole contract suite of
``OrgInitializer`` passes over the real ports (the files of the organization, the ``git`` program). The bytes are those of ``main``."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from orgmcp.app import Org, wiring
from orgmcp.bootstrap import OrgInitializer
from orgmcp.bootstrap._initializer import FsOrgInitializer
from orgmcp.kernel import OrgError
from orgmcp.bootstrap.testing import InitHarness, directories_below
from orgmcp.bootstrap.tests._cases import CASES, Case, expected
from orgmcp.bootstrap.tests.test_contract_org_initializer import (  # the contract suite, run here over the real ports
    test_a_second_init_is_refused,
    test_an_existing_org_md_is_refused_and_nothing_is_changed,
    test_gitignore_starts_with_the_initial_lines,
    test_org_md_is_the_settings_over_the_defaults_and_the_rules,
    test_the_first_commit_is_init_organization,
    test_the_root_gets_its_four_boxes_and_the_runtime_directory,
    test_without_git_everything_but_the_repository_is_made,
)

__all__ = [
    "test_a_second_init_is_refused", "test_an_existing_org_md_is_refused_and_nothing_is_changed",
    "test_gitignore_starts_with_the_initial_lines", "test_org_md_is_the_settings_over_the_defaults_and_the_rules",
    "test_the_first_commit_is_init_organization", "test_the_root_gets_its_four_boxes_and_the_runtime_directory",
    "test_without_git_everything_but_the_repository_is_made",
]


@pytest.fixture(autouse=True)
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")


def subjects(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    return subprocess.run(["git", "log", "--reverse", "--format=%s"], cwd=root, capture_output=True, text=True, check=False).stdout.splitlines()


def wired(tmp_path: Path) -> InitHarness:
    root = tmp_path / "org"
    runtime = wiring.open_runtime(root)

    def read(name: str) -> str | None:
        return (root / name).read_bytes().decode("utf-8") if (root / name).is_file() else None

    def put_org_md(text: str) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "ORG.md").write_text(text, encoding="utf-8")

    return InitHarness(
        runtime.org_initializer, root, lambda: read("ORG.md"), lambda: directories_below(root), lambda: read(".gitignore"),
        lambda: subjects(root), lambda: (root / ".git").exists(), put_org_md,
    )


@pytest.fixture
def h(tmp_path: Path) -> InitHarness:
    return wired(tmp_path)


@pytest.fixture
def no_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> InitHarness:
    nowhere = tmp_path / "no-programs"
    nowhere.mkdir()
    monkeypatch.setenv("PATH", str(nowhere))  # the git program does not exist
    return wired(tmp_path / "work")


def listing(root: Path) -> str:
    entries = sorted(p.relative_to(root) for p in root.rglob("*") if p.relative_to(root).parts[0] != ".git")
    return "".join(f"{p}{'/' if (root / p).is_dir() else ''}\n" for p in entries)


def test_the_runtime_has_the_real_initializer(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.org_initializer, FsOrgInitializer) and isinstance(runtime.org_initializer, OrgInitializer)


def test_opening_a_runtime_makes_nothing(tmp_path: Path) -> None:
    wiring.open_runtime(tmp_path / "nowhere")
    assert not (tmp_path / "nowhere").exists()


def test_the_initializer_works_with_the_ports_of_its_runtime(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "org")
    runtime.org_initializer.init(tmp_path / "org", "UNIQUE-MISSION", {"max_depth": 7})
    assert "UNIQUE-MISSION" in runtime.settings.rules() and runtime.settings.config()["max_depth"] == 7
    assert runtime.documents.exists() and (tmp_path / "org" / ".git").is_dir()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_org_init_writes_the_bytes_of_main(tmp_path: Path, case: Case) -> None:
    org = Org.init(tmp_path / "org", case.mission, case.config)
    assert (org.root / "ORG.md").read_bytes().decode("utf-8") == expected(f"org_md_{case.name}.md")


def test_org_init_makes_the_tree_of_main(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org")
    assert listing(org.root) == expected("layout.txt")
    assert (org.root / ".gitignore").read_bytes().decode("utf-8") == expected("gitignore.txt")
    assert subjects(org.root) == ["init organization"]


def test_org_init_without_git_makes_no_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nowhere = tmp_path / "no-programs"
    nowhere.mkdir()
    monkeypatch.setenv("PATH", str(nowhere))
    org = Org.init(tmp_path / "work" / "org", "m")
    assert listing(org.root) == expected("layout.txt")
    assert not (org.root / ".git").exists()


def test_org_init_resolves_the_root_and_returns_an_org_of_the_class_it_was_called_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Child(Org):
        pass

    monkeypatch.chdir(tmp_path)
    org = Child.init("rel/../made", "m")
    assert type(org) is Child and org.root == (tmp_path / "made").resolve()


def test_org_init_expands_the_home_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    org = Org.init("~/home-org", "m")
    assert org.root == (tmp_path / "home-org").resolve()


def test_org_init_refuses_an_organization_with_the_text_of_main(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "m")
    with pytest.raises(OrgError, match=f"^already an organization: {org.root}$"):
        Org.init(tmp_path / "org", "AGAIN-MISSION")
    assert "AGAIN-MISSION" not in (org.root / "ORG.md").read_text()


def test_initialize_org_makes_the_organization_and_returns_its_resolved_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from orgmcp.app.wire_bootstrap import initialize_org

    monkeypatch.chdir(tmp_path)
    root = initialize_org("rel/../made", "a mission", {"max_hops": 5})
    assert root == (tmp_path / "made").resolve() and (root / "ORG.md").is_file()
    assert Org(root).config["max_hops"] == 5 and "a mission" in Org(root).rules()


def test_initialize_org_refuses_an_organization_with_the_text_of_main(tmp_path: Path) -> None:
    from orgmcp.app.wire_bootstrap import initialize_org

    root = initialize_org(tmp_path / "org")
    with pytest.raises(OrgError, match=f"^already an organization: {root}$"):
        initialize_org(root, "AGAIN")
