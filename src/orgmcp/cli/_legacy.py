"""The old module-level names of ``orgmcp.cli``: ``main``, the entry point the tests, ``python -m orgmcp`` and the console script call.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). The program is built by the composition root (``orgmcp.app.wire_cli``), which an entry point may not
import: it is looked up when ``main`` runs, so importing ``orgmcp.cli`` loads no other part of the application.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    """Run the command line: parse ``argv`` (default ``sys.argv[1:]``), run the command, record it, map an ``OrgError`` to ``error: ...`` and exit status 1."""
    importlib.import_module("orgmcp.app.wire_cli").run_cli(argv)
