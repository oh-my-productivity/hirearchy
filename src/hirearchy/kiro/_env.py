"""``run_environment``: the environment kiro-cli sees, for runs and for the readiness check (docs/design/kiro-runtime-v3.md 5)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

# Set, these would add MCP servers to every agent or write requests, configuration and transcripts to a directory of the user's choosing.
SCRUBBED_VARIABLES = (
    "ASBX_KIRO_MANDATORY_MCPS",
    "KIRO_CHAT_LOG_FILE",
    "KIRO_DUMP_CONFIGURATION",
    "KIRO_DUMP_CONFIGURATION_DIR",
    "KIRO_DUMP_REQUESTS",
    "KIRO_DUMP_REQUESTS_DIR",
)
SCRUBBED_PREFIX = "KIRO_FEATURE_"


def run_environment(variables: Mapping[str, str], home: Path) -> dict[str, str]:
    """A copy of ``variables`` without the scrubbed names and with ``KIRO_HOME`` set to ``home`` (an inherited value never survives).

    Everything else is kept, ``KIRO_API_KEY``, ``KIRO_LOG_LEVEL`` and the session variables of a parent kiro session included."""
    env = {n: v for n, v in variables.items() if n not in SCRUBBED_VARIABLES and not n.startswith(SCRUBBED_PREFIX)}
    env["KIRO_HOME"] = str(home)
    return env
