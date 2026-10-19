"""``VenvMcpServerLocator``: how kiro starts the orgmcp MCP server."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..kernel import Provider
from .api import McpServerLocator


class VenvMcpServerLocator(McpServerLocator):
    def __init__(self, executable: Provider[Path], project_dir: Path, which: Callable[[str], str | None]) -> None:
        self._executable = executable  # the running interpreter
        self._project_dir = project_dir  # the checkout that ``uv --directory`` runs in when no console script is installed
        self._which = which

    def command(self) -> dict[str, object]:
        raise NotImplementedError
