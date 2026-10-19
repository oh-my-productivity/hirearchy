"""The real organization, for the tests that run the real program.

``Org`` is the facade of the composition root; the tests of an entry point may not import ``orgmcp.app`` (layers: an entry point does not know the composition
root), so it is looked up when a test needs it. Only tests that build a world for the real command line use it; the unit tests of the commands use fakes.
"""

from __future__ import annotations

import importlib
from typing import Any

Org = Any  # (the facade: an alias for the annotations of the tests)


def facade() -> Any:
    """The class ``orgmcp.app.Org``."""
    return importlib.import_module("orgmcp.app").Org


def process_resources() -> Any:
    """The resources of this process (``orgmcp.app.wiring.process_resources()``)."""
    return importlib.import_module("orgmcp.app.wiring").process_resources()
