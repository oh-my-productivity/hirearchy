"""``FsOrgInitializer``: which directories it makes, and in which order it uses its ports (the golden bytes of the whole tree: ``app/tests/test_wire_bootstrap.py``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from orgmcp.bootstrap import INITIAL_IGNORE_LINES, OrgInitializer
from orgmcp.bootstrap._initializer import FsOrgInitializer
from orgmcp.kernel import OrgError
from orgmcp.snapshots import IgnoreList, OrgSnapshotter
from orgmcp.templates import DocumentTemplates
from orgmcp.templates.testing import static_document_templates

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-bootstrap", raises=NotImplementedError)


def test_an_existing_empty_directory_becomes_the_organization(tmp_path: Path) -> None:
    root = tmp_path / "org"
    root.mkdir()
    FsOrgInitializer(_NoDocument(), static_document_templates(), _Journal(), _Journal()).init(root, "m")
    assert (root / "inbox").is_dir()


def test_missing_parent_directories_are_made(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "org"
    FsOrgInitializer(_NoDocument(), static_document_templates(), _Journal(), _Journal()).init(deep, "m")
    assert (deep / "inbox").is_dir() and (deep / ".runtime").is_dir()


# ----------------------------------------------------------------------------------------------- the order of the ports


class _Journal(OrgSnapshotter, IgnoreList):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def init_repository(self) -> None:
        self.calls.append("init_repository")

    def commit(self, message: str) -> None:
        self.calls.append(f"commit {message}")

    def write_initial(self, lines: Sequence[str]) -> None:
        self.calls.append("write_initial " + ",".join(lines))

    def ensure(self, lines: Sequence[str]) -> None:
        self.calls.append("ensure")

    def ensure_runtime_files(self) -> None:
        self.calls.append("ensure_runtime_files")


class _NoDocument:
    def exists(self) -> bool:
        return False

    def read_raw(self) -> str:
        raise FileNotFoundError("ORG.md")

    def write_raw(self, text: str) -> None:
        pass


class _Documents(_NoDocument):
    def __init__(self, journal: list[str], exists: bool = False) -> None:
        self._journal = journal
        self._exists = exists

    def exists(self) -> bool:
        self._journal.append("exists")
        return self._exists

    def write_raw(self, text: str) -> None:
        self._journal.append("write_raw")
        self.written = text


class _Templates(DocumentTemplates):
    def __init__(self) -> None:
        self.missions: list[str | None] = []

    def org_rules(self, mission: str | None) -> str:
        self.missions.append(mission)
        return f"RULES for {mission}\n\n\n"

    def charter_body(self, role: str, charter: str) -> str:
        raise AssertionError("not used")

    def task_body(self, goal: str, acceptance: str, inputs: Sequence[str]) -> str:
        raise AssertionError("not used")

    def result_body(self, summary: str, artifacts: Sequence[str], lessons: str = "") -> str:
        raise AssertionError("not used")


def make(tmp_path: Path, exists: bool = False) -> tuple[OrgInitializer, _Documents, _Journal, _Templates, list[str]]:
    journal: list[str] = []
    documents, ports, templates = _Documents(journal, exists), _Journal(), _Templates()
    ports.calls = journal
    return FsOrgInitializer(documents, templates, ports, ports), documents, ports, templates, journal


def test_org_md_goes_first_then_the_gitignore_then_the_repository_then_the_commit(tmp_path: Path) -> None:
    initializer, _, _, _, journal = make(tmp_path)
    initializer.init(tmp_path / "org", "m")
    assert journal == ["exists", "write_raw", "write_initial " + ",".join(INITIAL_IGNORE_LINES), "init_repository", "commit init organization"]


def test_the_directories_are_made_after_org_md_and_before_the_gitignore(tmp_path: Path) -> None:
    initializer, documents, _, _, _ = make(tmp_path)
    root = tmp_path / "org"
    seen: list[bool] = []
    original = documents.write_raw

    def write_raw(text: str) -> None:
        original(text)
        seen.append(root.is_dir() and not (root / "inbox").exists())

    documents.write_raw = write_raw  # type: ignore[method-assign]
    initializer.init(root, "m")
    assert seen == [True]
    assert all((root / name).is_dir() for name in ("inbox", "inflight", "read", "sent", ".runtime"))


def test_the_text_is_the_config_over_the_defaults_with_the_rules_of_the_mission(tmp_path: Path) -> None:
    initializer, documents, _, templates, _ = make(tmp_path)
    initializer.init(tmp_path / "org", "the mission", {"max_depth": 9, "extra": "x"})
    text = documents.written
    assert templates.missions == ["the mission"]
    front, _, body = text.partition("\n---\n")
    assert body == "RULES for the mission\n"  # one trailing newline, as every frontmatter file
    assert "max_depth: 9\n" in front and "extra: x\n" in front and "max_hops: 40\n" in front


def test_an_existing_org_md_is_refused_before_anything_is_touched(tmp_path: Path) -> None:
    initializer, _, _, _, journal = make(tmp_path, exists=True)
    root = tmp_path / "org"
    with pytest.raises(OrgError, match=f"already an organization: {root}"):
        initializer.init(root, "m")
    assert journal == ["exists"]
    assert not root.exists()


def test_the_config_may_be_any_mapping(tmp_path: Path) -> None:
    initializer, documents, _, _, _ = make(tmp_path)
    config: Mapping[str, object] = {"poll_seconds": 5}
    initializer.init(tmp_path / "org", None, config)
    assert "poll_seconds: 5\n" in documents.written
