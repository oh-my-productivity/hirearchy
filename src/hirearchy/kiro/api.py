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
from ._launch import READ_ONLY_TOOL_IDS, THROTTLE_EXIT, throttled_without_effect

__all__ = [
    "CHARTER_TOOLS",
    "FILE_TOOLS",
    "READINESS_TIMEOUT",
    "READ_ONLY_TOOL_IDS",
    "START_DEADLINE",
    "THROTTLE_EXIT",
    "CliResult",
    "Confinement",
    "ConfinementPolicy",
    "KiroCli",
    "KiroHomeAudit",
    "KiroPlaces",
    "KiroRunRefused",
    "KiroStateDirs",
    "McpServerLocator",
    "ProfileProvisioner",
    "ProfileStore",
    "RunCommand",
    "RunCommandBuilder",
    "RuntimeReadiness",
    "throttled_without_effect",
]

CHARTER_TOOLS = ("read", "write", "shell", "web_search", "web_fetch")  # the charter names kiro maps (design 4.2)
FILE_TOOLS = ("read", "write")  # kiro built-ins whose reach can be limited by path (shell cannot)
START_DEADLINE = 60.0  # seconds a run has to emit ``runStarted`` before the launcher gives up (design 5.1)
# Seconds one kiro-cli call of the readiness check may take (design 9). Three calls plus 2.5 s must fit in the daemon's startup window:
# pinned by app/tests/test_wire_kiro.py::test_readiness_fits_in_the_start_window (3 * READINESS_TIMEOUT + 2.5 <= STARTUP_SECONDS).
READINESS_TIMEOUT = 2.5


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
        """``kiro-cli chat --no-interactive --agent <profile> --model <model> --effort <effort>`` for ``addr``; the prompt goes on stdin, not in the
        command. An ORG.md effort outside high, xhigh and max refuses the run (``KiroRunRefused``)."""
        ...


@runtime_checkable
class KiroPlaces(Protocol):
    """Where hirearchy keeps the kiro home and the working directories of one organization (computing them touches no file).

    ``<state>/kiro-home/<org-id>`` is ``KIRO_HOME``; ``<state>/kiro-cwd/<org-id>/<agent-key>`` is a run's working directory. Every
    path is absolute and ``realpath``ed; the environment and the home directory are asked on every call."""

    def home(self) -> Path:
        """``KIRO_HOME`` of this organization."""
        ...

    def scratch(self, addr: str) -> Path:
        """The working directory of ``addr``'s runs (emptied before every run)."""
        ...

    def roots(self) -> tuple[Path, Path]:
        """``(<state>/kiro-home, <state>/kiro-cwd)``: shared by every organization of this user (the placement check, design 8.3)."""
        ...

    def problem(self) -> str | None:
        """Why these places cannot be used (a relative ``HIREARCHY_STATE_DIR``, a home that is the user's home or above it, a path kiro
        cannot match literally) as one line, else ``None``."""
        ...


@runtime_checkable
class KiroStateDirs(Protocol):
    def private_dir(self, path: Path) -> None:
        """Create ``path`` (and its parents) with mode ``0700``; ``OSError`` when it is a symlink."""
        ...

    def fresh(self, path: Path) -> None:
        """Make ``path`` an empty directory (``0700``), removing whatever was there; ``OSError`` when that cannot be done safely
        (a symlinked component, a platform whose ``rmtree`` follows symlinks)."""
        ...


@runtime_checkable
class KiroHomeAudit(Protocol):
    def planted(self, home: Path) -> list[str]:
        """What ``home`` holds that kiro-cli would load into every agent and hirearchy did not put there, relative to ``home`` and sorted."""
        ...


@dataclass(frozen=True)
class CliResult:
    """What a short kiro-cli command answered: its exit code and its output (both streams, decoded with replacement, at most 64 KB)."""

    code: int
    output: str


@runtime_checkable
class KiroCli(Protocol):
    def run(self, argv: Sequence[str], env: Mapping[str, str], timeout: float) -> CliResult | None:
        """Run a short kiro-cli command with stdin closed and ``env`` as its whole environment, in its own session.

        ``None`` when it cannot start or does not finish within ``timeout`` seconds (its whole process group is killed then)."""
        ...


@runtime_checkable
class RuntimeReadiness(Protocol):
    def state_problem(self) -> str | None:
        """Why the kiro state cannot be used (places, placement, the kiro home and its audit; design 9 steps 1-3) as one line, else ``None``.
        Makes no kiro-cli call and never raises."""
        ...

    def check(self, kiro_bin: str) -> str | None:
        """``state_problem``, then whether ``kiro_bin`` is usable, offers the V3 engine and has credentials (design 9 steps 1-6) as one
        line, else ``None``. Never raises."""
        ...
