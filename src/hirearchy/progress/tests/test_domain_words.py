"""I9, plan 7.4: the quality view of ``progress`` names no domain. A needle test over the new production modules."""

from __future__ import annotations

from pathlib import Path

from testkit.domain_words import violations

import hirearchy.progress

MODULES = ("_quality.py", "_quality_render.py", "_quality_facts.py")
PACKAGE = Path(hirearchy.progress.__file__).resolve().parent


def test_the_quality_modules_name_no_domain() -> None:
    found = [v for module in MODULES for v in violations(PACKAGE / module)]
    assert found == [], "the core is domain-agnostic: " + "; ".join(found)
