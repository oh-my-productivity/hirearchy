"""Root's ``whoami`` and ``status`` over a wired server name a stale installed skill (``~/.kiro`` is a temporary HOME: never the real one)."""

from __future__ import annotations

from pathlib import Path

import pytest
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.skill_world import build_server, skill_source

from ._support import call


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


def installed(home: Path) -> Path:
    return home / ".kiro" / "skills" / "hirearchy" / "SKILL.md"


def put(home: Path, text: str) -> Path:
    target = installed(home)
    target.parent.mkdir(parents=True)
    target.write_text(text, encoding="utf-8")
    return target


def note(target: Path) -> str:
    return f"Note: the installed skill at {target} is out of date: run `hirearchy install-skill --force`"


def test_a_different_installed_copy_is_named_by_whoami_and_status(home: Path, tmp_path: Path) -> None:
    target = put(home, "an older version\n")
    server = build_server(Org.init(tmp_path / "o", "m"), ROOT)
    for tool in ("whoami", "status"):
        assert note(target) in call(server, tool), tool


def test_an_agent_is_never_told(home: Path, tmp_path: Path) -> None:
    put(home, "an older version\n")
    org = Org.init(tmp_path / "o", "m")
    org.hire(ROOT, "ceo", "Lead", "Lead the work.")
    server = build_server(org, "ceo")
    for tool in ("whoami", "status"):
        assert "installed skill" not in call(server, tool), tool


def test_an_identical_copy_is_not_mentioned(home: Path, tmp_path: Path) -> None:
    put(home, skill_source().read_text(encoding="utf-8"))
    server = build_server(Org.init(tmp_path / "o", "m"), ROOT)
    for tool in ("whoami", "status"):
        assert "installed skill" not in call(server, tool), tool


def test_no_installed_copy_is_not_mentioned(home: Path, tmp_path: Path) -> None:
    server = build_server(Org.init(tmp_path / "o", "m"), ROOT)
    for tool in ("whoami", "status"):
        assert "installed skill" not in call(server, tool), tool
    assert not installed(home).exists()  # looking never installs


def test_setup_mode_names_it_too(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from testkit.mcp_server_world import build_server as build, resolve_binding

    target = put(home, "an older version\n")
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "fresh" / "org"))
    server = build(*resolve_binding())
    for tool in ("whoami", "status"):
        out = call(server, tool)
        assert out.startswith("Setup: no organization exists at") and note(target) in out, tool
