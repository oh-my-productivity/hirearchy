"""``FsAgentDirectory`` over the directories of an organization."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory
from orgmcp.agents._directory import FsAgentDirectory
from orgmcp.kernel import OrgLayout, OrgPaths

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-agents")


class RecordingLayout(OrgLayout):
    """The paths of a real organization directory, remembering which agent directories were asked for."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.asked: list[str] = []
        self._paths = OrgPaths(root)

    def agent_dir(self, addr: str) -> Path:
        self.asked.append(addr)
        return self._paths.agent_dir(addr)

    def box(self, addr: str, box: str) -> Path:
        return self._paths.box(addr, box)

    def runtime_dir(self) -> Path:
        return self._paths.runtime_dir()

    def ledger_file(self, name: str) -> Path:
        return self._paths.ledger_file(name)

    def events_dir(self) -> Path:
        return self._paths.events_dir()

    def retired_dir(self) -> Path:
        return self._paths.retired_dir()

    def rel(self, path: Path) -> str:
        return self._paths.rel(path)


def test_it_is_an_agent_directory(tmp_path: Path) -> None:
    assert isinstance(FsAgentDirectory(OrgPaths(tmp_path)), AgentDirectory)


def test_building_it_looks_at_nothing(tmp_path: Path) -> None:
    layout = RecordingLayout(tmp_path / "does-not-exist")
    FsAgentDirectory(layout)
    assert layout.asked == []


def test_an_invalid_name_is_refused_without_looking_at_the_disk(tmp_path: Path) -> None:
    layout = RecordingLayout(tmp_path)
    directory = FsAgentDirectory(layout)
    assert [directory.exists(a) for a in ("Ceo", "ceo/work", "ops\n/x", "a//b")] == [False] * 4
    assert directory.exists("root") is True
    assert layout.asked == []


def test_a_valid_name_is_looked_up_under_its_normalized_address(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_text("---\nrole: R\n---\n", encoding="utf-8")
    layout = RecordingLayout(tmp_path)
    assert FsAgentDirectory(layout).exists(" /ceo/ ") is True
    assert layout.asked == ["ceo"]


def test_an_organization_directory_that_is_missing_has_no_agents(tmp_path: Path) -> None:
    directory = FsAgentDirectory(OrgPaths(tmp_path / "nowhere"))
    assert directory.children("root") == [] and directory.agents() == [] and directory.exists("ceo") is False
    assert directory.subtree("root") == ["root"]


def test_a_symbolic_link_to_a_directory_with_a_charter_is_an_agent(tmp_path: Path) -> None:
    real = tmp_path / "elsewhere" / "ceo"
    real.mkdir(parents=True)
    (real / "AGENT.md").write_text("---\nrole: R\n---\n", encoding="utf-8")
    (tmp_path / "org").mkdir()
    (tmp_path / "org" / "ceo").symlink_to(real, target_is_directory=True)
    directory = FsAgentDirectory(OrgPaths(tmp_path / "org"))
    assert directory.children("root") == ["ceo"] and directory.exists("ceo") is True


def test_require_names_the_normalized_address(tmp_path: Path) -> None:
    from orgmcp.kernel import OrgError

    with pytest.raises(OrgError, match=r"^no such agent: a/b$"):
        FsAgentDirectory(OrgPaths(tmp_path)).require(" /a/b/ ")
