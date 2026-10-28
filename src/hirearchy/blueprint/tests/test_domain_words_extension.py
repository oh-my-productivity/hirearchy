"""I9, plan 7.4: the extension and provenance modules of ``blueprint`` name no domain. A needle test over the new production modules."""

from __future__ import annotations

from pathlib import Path

from testkit.domain_words import violations

import hirearchy.blueprint

MODULES = ("_provenance.py", "_extension.py", "_extension_form.py")
PACKAGE = Path(hirearchy.blueprint.__file__).resolve().parent


def test_the_extension_and_provenance_modules_name_no_domain() -> None:
    found = [v for module in MODULES for v in violations(PACKAGE / module)]
    assert found == [], "the core is domain-agnostic: " + "; ".join(found)
