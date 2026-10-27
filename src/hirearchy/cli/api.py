"""The public surface of ``cli``: the command line of the human (root) and of the runtime.

``hirearchy [--root DIR] COMMAND ...``: 27 commands that read or change the organization at the root (the global ``--root``, else ``$ORG_ROOT``, else
the nearest directory above the working directory that has an ORG.md). The entry point publishes one interface, ``CliApp``: it parses the command line,
runs the command, records a ``cli.command`` event for it and turns an ``OrgError`` into the message ``error: ...`` on the standard error and the exit
status 1. Every command, the ports it consumes (the organization it opens, the other entry points it launches, the terminal) and the parser are private
(``_commands_*``, ``_ports``, ``_parser``): the console script ``hirearchy`` and ``python -m hirearchy`` call the application the composition root builds.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

__all__ = ["CliApp"]


@runtime_checkable
class CliApp(Protocol):
    def main(self, argv: Sequence[str] | None = None) -> None:
        """Parse ``argv`` (default ``sys.argv[1:]``), run the command, record the ``cli.command`` event, and map an ``OrgError`` to ``error: <message>`` on
        the standard error and ``SystemExit(1)``. A command that exits by itself (``plan`` with errors, ``check`` that fails) keeps its status, and any other
        exception is recorded and raised again."""
        ...
