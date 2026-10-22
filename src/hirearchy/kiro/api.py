"""The public surface of ``kiro``: how the organization is adapted to the kiro-cli agent runtime.

Five roles, one small interface each: which tools kiro may use on which paths (``ConfinementPolicy``), where the profiles
live (``ProfileStore``), which profile an organization's agents run with (``ProfileProvisioner``), how kiro starts the hirearchy server
(``McpServerLocator``), and the command that runs one agent (``RunCommandBuilder``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, OrgError

__all__ = [
    "CHARTER_TOOLS",
    "FILE_TOOLS",
    "Confinement",
    "ConfinementPolicy",
    "KiroRunRefused",
    "McpServerLocator",
    "ProfileProvisioner",
    "ProfileStore",
    "RunCommand",
    "RunCommandBuilder",
]

CHARTER_TOOLS = ("read", "write", "shell", "web_search", "web_fetch")  # the charter names kiro maps (design 4.2)
FILE_TOOLS = ("read", "write")  # kiro built-ins whose reach can be limited by path (shell cannot)


@dataclass(frozen=True)
class RunCommand:
    """What the scheduler starts for one run: the command line (the prompt is not in it: it goes on stdin), where, and with which environment."""

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]


@dataclass(frozen=True)
class Confinement:
    """What one agent's kiro run may reach, as kiro-cli V3 enforces it (verified against kiro-cli 2.33.0 / KAS 0.66.48).

    With ``problem`` set, the other fields are computed from the valid part of the grant as if the invalid part were absent (unknown
    tool names dropped; a workspace or input with a refused character dropped; the org root kept, so ``read`` still names it); the
    run command builder never uses them (it refuses the run), only the blueprint's access report reads ``read``. ``tools`` always
    starts with ``"@hirearchy"``.
    """

    tools: tuple[str, ...]  # the profile's "tools" selector
    rules: tuple[JsonObject, ...]  # the profile's "permissions.rules", in order
    read: tuple[Path, ...]  # where kiro's read tools may read (resolved; empty: nowhere)
    write: Path | None  # the one directory kiro's write tools may change (None: nowhere)
    problem: str | None = None  # why this access cannot be enforced (unknown tool, path kiro cannot match); then refuse


class KiroRunRefused(OrgError):
    """A run that kiro-cli could not run confined, or that kiro's state forbids; the message says why."""


@runtime_checkable
class ConfinementPolicy(Protocol):
    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> Confinement:
        """The V3 ``tools`` selector and permission rules of this grant, and what they let kiro read and write (pure; verified against
        kiro-cli 2.33.0 / KAS 0.66.48)."""
        ...


@runtime_checkable
class ProfileStore(Protocol):
    """The directory of kiro agent profiles, resolved when it is used, not when the store is made."""

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

    def ensure_profile(self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None) -> str:
        """Write the organization's V3 profile for this grant and access when it is missing or different; returns its name.

        Every profile is V3 and confined by its grant (``ConfinementPolicy``); one with built-in ``read``/``write`` has ``-x<8 hex>``
        (a hash of its rules) appended to the name. ``KiroRunRefused`` when the grant cannot be confined; nothing is written then."""
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
