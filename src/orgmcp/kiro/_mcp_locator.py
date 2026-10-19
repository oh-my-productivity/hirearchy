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
        """How kiro should start the orgmcp MCP server (prefer the venv's console script)."""
        script = self._executable().with_name("orgmcp")
        if script.exists():
            return {"command": str(script), "args": ["mcp"]}
        return {"command": self._which("uv") or "uv", "args": ["--directory", str(self._project_dir), "run", "orgmcp", "mcp"]}
