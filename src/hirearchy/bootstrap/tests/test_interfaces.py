"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6)."""

from __future__ import annotations

import pytest

from hirearchy.bootstrap import OrgInitializer
from hirearchy.bootstrap._initializer import FsOrgInitializer
from hirearchy.bootstrap.testing import MemoryOrgInitializer


@pytest.mark.parametrize("implementation", [FsOrgInitializer, MemoryOrgInitializer])
def test_the_class_subclasses_its_port(implementation: type) -> None:
    assert OrgInitializer in implementation.__mro__
