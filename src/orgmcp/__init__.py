"""orgmcp: a file-based organization of agents, run over MCP."""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> None:
    """The command line: what the console script (``orgmcp = "orgmcp:main"``) and ``python -m orgmcp`` run.

    Parse ``argv`` (default ``sys.argv[1:]``), run the command, record it, map an ``OrgError`` to ``error: ...`` and exit status 1. The program is built by
    the composition root (``orgmcp.app.wire_cli.run_cli``), imported when the command runs: importing the package (``orgmcp.kernel``, ``orgmcp.telemetry``,
    ...) loads no other part of the application.
    """
    from .app.wire_cli import run_cli

    run_cli(argv)
