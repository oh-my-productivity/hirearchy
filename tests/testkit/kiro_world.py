"""The kiro adapter as the tests of ``kiro`` have always called it: ``kiro_runner()(org, addr, prompt)``, ``ensure_kiro_profile(tools, dir, org=org, ...)``,
``kiro_profile_name(org_root, tools)``, ``file_confinement(...)``, over the ports of the runtime (``run_command_builder``, ``profile_provisioner``,
``confinement_policy``).

The profile store is ``agents/`` of the kiro home of the organization (``kiro_home_agents_dir``), which the places resolve below ``$HOME`` when they are used
(``Environment.home()``), so the ``isolated_kiro`` fixture, which sets ``HOME``, is enough to keep a test out of the real ``~/.kiro``; a profile directory of
the test's own is the ``ProfileStore`` it puts into the runtime. The command a run is started with is the launcher, then ``--``, then the kiro command
(``kiro_part``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from hirearchy.app import wiring
from hirearchy.kernel._system import FsAtomicWriter
from hirearchy.kiro import Confinement, ProfileStore
from hirearchy.kiro._profiles import FsProfileStore

from .health_world import _OVERRIDES, with_ports

Runner = Callable[[Any, str, str], tuple[list[str], Path, dict[str, str]]]


def kiro_runner(kiro_bin: str = "kiro-cli") -> Runner:
    """``(org, addr, prompt) -> (argv, cwd, env)``: the command the runtime builds for one run of ``addr`` (the prompt goes on stdin, not in it)."""
    assert kiro_bin == "kiro-cli", "the runtime builds the command of kiro-cli"

    def build(org: Any, addr: str, prompt: str) -> tuple[list[str], Path, dict[str, str]]:
        command = org.runtime.run_command_builder.build(addr, prompt)
        return list(command.argv), command.cwd, dict(command.env)

    return build


def kiro_part(argv: Sequence[str]) -> list[str]:
    """The kiro command of a run command: what follows the ``--`` that ends the arguments of the launcher (``kiro-cli chat --no-interactive ...``)."""
    return list(argv[list(argv).index("--") + 1 :])


def kiro_home_agents_dir(org_root: str | Path) -> Path:
    """``agents/`` of the kiro home of the organization at ``org_root``, below the ``HOME`` in force: where its profiles are."""
    return wiring.open_runtime(Path(org_root)).kiro_places.home() / "agents"


def kiro_profile_name(org_root: str | Path, tools: Sequence[str]) -> str:
    """The name of the profile of the organization at ``org_root`` for ``tools`` (nothing is read or written)."""
    return wiring.open_runtime(Path(org_root)).profile_provisioner.profile_name(tools)  # type: ignore[no-any-return]


def profiles_in(org: Any, directory: Path) -> Any:
    """The profiles of ``org`` are written into ``directory`` (its runtime is opened again with a profile store there)."""
    store: ProfileStore = FsProfileStore(lambda: Path(directory), FsAtomicWriter())
    return with_ports(org, {ProfileStore: store})


def ensure_kiro_profile(
    tools: Sequence[str], agents_dir: Path | None = None, *, org: Any, workspace: Path | None = None, inputs: Sequence[Path] | None = None,
) -> str:
    """Write the profile of ``org`` into ``agents_dir`` (default: ``agents/`` of its kiro home, below the ``HOME`` in force); returns its name."""
    runtime = org.runtime
    if agents_dir is not None:
        store: ProfileStore = FsProfileStore(lambda: Path(agents_dir), FsAtomicWriter())
        runtime = wiring.open_runtime(org.root, {**getattr(org, _OVERRIDES, {}), ProfileStore: store})
    return runtime.profile_provisioner.ensure_profile(tools, workspace=workspace, inputs=inputs)  # type: ignore[no-any-return]


def file_confinement(
    org_root: str | Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
) -> Confinement:
    """The V3 ``tools`` selector, permission rules and reach that confine kiro's tools by path."""
    return wiring.open_runtime(Path(org_root)).confinement_policy.file_confinement(Path(org_root), tools, workspace, inputs)  # type: ignore[no-any-return]
