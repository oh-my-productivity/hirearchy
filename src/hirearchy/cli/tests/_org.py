"""The real organization, for the tests that run the real program.

``Org`` is the facade of the composition root; the tests of an entry point may not import ``hirearchy.app`` (layers: an entry point does not know the composition
root), so it is looked up when a test needs it. Only tests that build a world for the real command line use it; the unit tests of the commands use fakes.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Any

Org = Any  # (the facade: an alias for the annotations of the tests)


def facade() -> Any:
    """The class ``hirearchy.app.Org``."""
    return importlib.import_module("hirearchy.app").Org


def process_resources() -> Any:
    """The resources of this process (``hirearchy.app.wiring.process_resources()``)."""
    return importlib.import_module("hirearchy.app.wiring").process_resources()


def overriding(overrides: Mapping[type, object]) -> AbstractContextManager[None]:
    """``hirearchy.app.wiring.overriding(overrides)``: the ports every runtime opened inside the block starts from (a fake ``Clock``, ``TokenSource`` ...)."""
    return importlib.import_module("hirearchy.app.wiring").overriding(overrides)  # type: ignore[no-any-return]
