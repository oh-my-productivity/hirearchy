"""The organizations the golden files were captured from (before the move, from ``Org.init`` of ``main``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

EXPECTED = Path(__file__).resolve().parent / "expected"

DIRECTORIES = [".runtime/", "inbox/", "inflight/", "read/", "sent/"]
MISSION = "Study octopuses.\n\n## Findings so far\nThey have three hearts."
CONFIG = {"poll_seconds": 0.05, "default_model": "claude-opus-5.5", "events": False, "max_depth": 2}


@dataclass(frozen=True)
class Case:
    name: str  # the golden file is expected/org_md_<name>.md
    mission: str | None
    config: dict[str, object] | None = field(default=None)


CASES = [
    Case("no_mission", None),
    Case("mission", MISSION),
    Case("config", "m", CONFIG),
]


def expected(name: str) -> str:
    """The text captured before the move, decoded without any newline translation."""
    return (EXPECTED / name).read_bytes().decode("utf-8")
