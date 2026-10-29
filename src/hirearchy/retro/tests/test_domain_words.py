"""I9, design 15.1: the retro modules name no domain. A needle test over the production modules of ``retro`` (each commit adds its own).

``_texts.py`` and ``_render.py`` are not on the list: they hold the design's fixed texts, among them the heading ``Objection test``, a word of the
process and not of a domain."""

from __future__ import annotations

from pathlib import Path

from testkit.domain_words import violations

import hirearchy.retro

MODULES = ("api.py", "_thresholds.py", "_ledger.py", "_views.py", "_shapes.py", "_ports.py", "_changes.py", "_readings.py", "_facts.py", "_effect.py", "_signals.py", "_items.py", "_ladder.py", "_brief.py", "_sources.py")
PACKAGE = Path(hirearchy.retro.__file__).resolve().parent


def test_the_retro_modules_name_no_domain() -> None:
    found = [v for module in MODULES for v in violations(PACKAGE / module)]
    assert found == [], "the core is domain-agnostic: " + "; ".join(found)
