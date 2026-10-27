"""Plan 7, check 4: the item modules of ``services`` name no domain. A needle test over the new production modules (``testkit.domain_words``)."""

from __future__ import annotations

from pathlib import Path

from testkit.domain_words import violations

import hirearchy.services

MODULES = ("_items.py",)
PACKAGE = Path(hirearchy.services.__file__).resolve().parent


def test_the_item_modules_name_no_domain() -> None:
    found = [v for module in MODULES for v in violations(PACKAGE / module)]
    assert found == [], "the core is domain-agnostic: " + "; ".join(found)
