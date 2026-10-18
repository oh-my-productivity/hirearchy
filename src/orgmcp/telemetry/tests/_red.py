"""The red phase of step A-telemetry: which parametrizations of a contract suite are still red (this module goes when they are green)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

import pytest
from _pytest.mark.structures import ParameterSet

RED = pytest.mark.xfail(strict=True, reason="red: A-telemetry")


def params(implementations: Sequence[Callable[..., object]], green: Iterable[str] = ()) -> list[ParameterSet]:
    """One parameter per implementation, red unless its name is in ``green`` (the kernel's own fakes pass already)."""
    done = set(green)
    return [pytest.param(factory, id=factory.__name__, marks=[] if factory.__name__ in done else [RED]) for factory in implementations]
