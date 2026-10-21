"""The ORG.md files and reports captured from ``upgrade_rules`` of ``main`` (before the move)."""

from __future__ import annotations

from pathlib import Path

EXPECTED = Path(__file__).resolve().parent / "expected"

COMMIT = "root: upgrade ORG.md rules to the current template"
MISSION = "Study octopuses.\n\n## Findings so far\nThey have three hearts."


def expected(name: str) -> str:
    """The text captured before the move, decoded without any newline translation."""
    return (EXPECTED / name).read_bytes().decode("utf-8")
