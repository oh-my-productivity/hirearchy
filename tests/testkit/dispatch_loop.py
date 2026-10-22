"""The scheduler's loop over the runtime of an organization, for the dispatch tests that need a whole scheduler pass (qa4: an oversized message must not
wedge the agent) with a stand-in binary instead of kiro-cli.

The run command is the real one (``KiroRunCommandBuilder`` over the ports of the runtime, with ``kiro_bin`` as the binary, started through the V3 launcher);
the stand-in must therefore speak V3 as far as a run needs: the stub ``kiro-cli`` of the ``isolated_kiro`` fixture does (``runStarted``, ``runFinished``),
``true`` does not (the launcher counts a kiro that ends before ``runStarted`` as a failed run). The profile the command asks for is written to a
``MemoryProfileStore``, not to the kiro home of the organization (what the patch of ``scheduler.ensure_kiro_profile`` kept the test from doing).
"""

from __future__ import annotations

from hirearchy.app import wire_kiro, wire_scheduler, wiring
from hirearchy.kernel._system import SystemClock
from hirearchy.kiro import McpServerLocator, ProfileStore
from hirearchy.kiro.testing import MemoryProfileStore, StaticMcpServerLocator
from hirearchy.scheduler._loop import HeartbeatLoop
from hirearchy.scheduler._run import LoopState
from hirearchy.scheduler.testing import RecordingConsole


def loop_over(org, kiro_bin: str) -> HeartbeatLoop:
    """The loop of ``org`` (whose runtime now writes its kiro profiles to memory) that runs ``kiro_bin`` for every agent."""
    org.runtime = wiring.open_runtime(org.root, {ProfileStore: MemoryProfileStore(), McpServerLocator: StaticMcpServerLocator()})
    commands = wire_kiro.run_command_builder(org.runtime, kiro_bin, org.runtime.profile_provisioner)
    return wire_scheduler.loop_of(org.runtime, commands, RecordingConsole(), SystemClock(), LoopState())
