"""The public surface of ``kiro``: how the organization is adapted to the kiro-cli agent runtime.

Five roles, one small interface each: which built-in tools kiro may use on which paths (``ConfinementPolicy``), where the profiles
live (``ProfileStore``), which profile an organization's agents run with (``ProfileProvisioner``), how kiro starts the hirearchy server
(``McpServerLocator``), and the command that runs one agent (``RunCommandBuilder``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = [
    "FILE_TOOLS",
    "ConfinementPolicy",
    "McpServerLocator",
    "ProfileProvisioner",
    "ProfileStore",
    "RunCommand",
    "RunCommandBuilder",
]

FILE_TOOLS = ("read", "write")  # kiro built-ins whose reach can be limited by path (shell cannot)


@dataclass(frozen=True)
class RunCommand:
    """What the scheduler starts for one run: the command line (the prompt is not in it: it goes on stdin), where, and with which environment."""

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]


@runtime_checkable
class ConfinementPolicy(Protocol):
    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        """``(allowedTools, toolsSettings)`` confining kiro's built-in ``read``/``write`` by path (pure; verified against kiro-cli 2.29.1)."""
        ...


@runtime_checkable
class ProfileStore(Protocol):
    """The directory of kiro agent profiles (``~/.kiro/agents``), resolved when it is used, not when the store is made."""

    def read(self, name: str) -> dict[str, object] | None:
        """The profile ``name``; ``None`` when it is missing, unreadable or not a JSON object."""
        ...

    def write(self, name: str, data: Mapping[str, object]) -> None:
        """Replace the profile ``name`` (atomic: a reader never sees half a profile)."""
        ...


@runtime_checkable
class ProfileProvisioner(Protocol):
    def profile_name(self, tools: Sequence[str]) -> str:
        """``hirearchy-<org slug>-<6 hex of the org root path>[-<tools>]``, lowercase ``[a-z0-9-]``: one name per organization and tool set."""
        ...

    def ensure_profile(
        self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None, confine: bool = False
    ) -> str:
        """Write the organization's profile when it is missing or different; returns its name. ``confine``: built-in ``read``/``write``
        limited by path, and ``-x<8 hex>`` (a hash of that access) appended to the name."""
        ...


@runtime_checkable
class McpServerLocator(Protocol):
    def command(self) -> dict[str, object]:
        """``{"command", "args"}`` that start ``hirearchy mcp``: the console script of the running interpreter's environment, else ``uv run``."""
        ...


@runtime_checkable
class RunCommandBuilder(Protocol):
    def build(self, addr: str, prompt: str) -> RunCommand:
        """``kiro-cli chat --no-interactive --agent <profile> --model <model>`` for ``addr``; the prompt goes on stdin, not in the command."""
        ...
