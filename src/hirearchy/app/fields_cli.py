"""Runtime fields of the ``cli`` entry point (ARCHITECTURE.md 6.3): none."""

from __future__ import annotations

from dataclasses import dataclass

STEP: str | None = "D-cli"  # set to the step's name when the step fills this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "CliApp": (
        "the program is built once per process by app.wire_cli.cli_app(): the organization a command works on is named by its arguments, so the commands "
        "are made before any runtime exists and reach the features of the organization they open through providers (a program, not a port every runtime has)"
    ),
}


@dataclass(frozen=True)
class Fields:
    """No field: the command line is built by ``wire_cli.cli_app`` and opens the runtime of the organization its arguments name."""
