"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6)."""

from __future__ import annotations

from orgmcp.upgrade import RulesUpgrader
from orgmcp.upgrade._upgrader import TemplateRulesUpgrader


def test_the_class_subclasses_its_port() -> None:
    assert RulesUpgrader in TemplateRulesUpgrader.__mro__
