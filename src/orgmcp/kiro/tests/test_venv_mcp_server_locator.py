"""``VenvMcpServerLocator``: the console script beside the running interpreter, else ``uv --directory <project> run orgmcp mcp``."""

from __future__ import annotations

from pathlib import Path

from orgmcp.kiro import McpServerLocator
from orgmcp.kiro._mcp_locator import VenvMcpServerLocator

from ._support import red


def locator(tmp_path: Path, which: dict[str, str] | None = None) -> VenvMcpServerLocator:
    found = which or {}
    return VenvMcpServerLocator(lambda: tmp_path / "venv" / "bin" / "python", tmp_path / "project", lambda name: found.get(name))


def test_it_is_a_locator(tmp_path: Path) -> None:
    assert isinstance(locator(tmp_path), McpServerLocator)


@red
def test_the_console_script_beside_the_interpreter_is_preferred(tmp_path: Path) -> None:
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    (tmp_path / "venv" / "bin" / "orgmcp").write_text("#!/bin/sh\n", encoding="utf-8")
    assert locator(tmp_path, {"uv": "/usr/bin/uv"}).command() == {"command": str(tmp_path / "venv" / "bin" / "orgmcp"), "args": ["mcp"]}


@red
def test_without_a_script_uv_runs_it_in_the_project(tmp_path: Path) -> None:
    assert locator(tmp_path, {"uv": "/usr/bin/uv"}).command() == {
        "command": "/usr/bin/uv", "args": ["--directory", str(tmp_path / "project"), "run", "orgmcp", "mcp"]}


@red
def test_without_uv_on_the_path_the_command_is_uv(tmp_path: Path) -> None:
    assert locator(tmp_path).command()["command"] == "uv"


@red
def test_the_interpreter_is_asked_on_every_call(tmp_path: Path) -> None:
    current = {"python": tmp_path / "one" / "python"}
    found = VenvMcpServerLocator(lambda: current["python"], tmp_path / "project", lambda name: "uv")
    (tmp_path / "two").mkdir()
    (tmp_path / "two" / "orgmcp").write_text("", encoding="utf-8")
    assert found.command()["command"] == "uv"
    current["python"] = tmp_path / "two" / "python"
    assert found.command() == {"command": str(tmp_path / "two" / "orgmcp"), "args": ["mcp"]}


@red
def test_a_script_that_appears_later_is_found_by_the_next_call(tmp_path: Path) -> None:
    found = locator(tmp_path)
    assert found.command()["command"] == "uv"
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    (tmp_path / "venv" / "bin" / "orgmcp").write_text("", encoding="utf-8")
    assert found.command()["command"] == str(tmp_path / "venv" / "bin" / "orgmcp")
