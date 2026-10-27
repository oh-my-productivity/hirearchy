"""I9, plan 7.4: the quality rules of ``reflection`` name no domain. A needle test over the new production modules."""

from __future__ import annotations

from pathlib import Path

from testkit.domain_words import WORDS, violations

import hirearchy.reflection

MODULES = ("_causes.py", "_quality_rules.py", "_marks.py", "_records.py")
PACKAGE = Path(hirearchy.reflection.__file__).resolve().parent


def test_the_quality_modules_name_no_domain() -> None:
    found = [v for module in MODULES for v in violations(PACKAGE / module)]
    assert found == [], "the core is domain-agnostic: " + "; ".join(found)


def test_the_needle_catches_each_word_in_an_identifier_and_in_a_string(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("\n".join(f'{w.replace(" ", "_")}_count = 1\nSTRING_{i} = "a {w.upper()} here"' for i, w in enumerate(WORDS)), encoding="utf-8")
    found = violations(sample)
    assert len(found) == 2 * len(WORDS) and all(any(w in line for line in found) for w in WORDS)
    docs = tmp_path / "docs.py"
    docs.write_text('"""A memo and a test."""\n\n\ndef contested() -> str:\n    """A meeting about code."""\n    return "contract"  # a ticket\n', encoding="utf-8")
    assert violations(docs) == []  # documentation is not read; "contested" and "contract" hold none of the words as whole words


def test_the_watch_module_names_no_domain() -> None:
    """The watch (design 8) is domain-agnostic: ``_watch.py`` holds no word of the work it was first measured on."""
    found = violations(PACKAGE / "_watch.py")
    assert found == [], "the core is domain-agnostic: " + "; ".join(found)
