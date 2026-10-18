"""Every symbol of the legacy modules appears in the mapping table of ARCHITECTURE.md section 5 (R: nothing is forgotten).

The document lists, per legacy module, every module-level function/class/constant and every method of ``Org``, ``Message``,
``Scheduler``, ``DashData`` and ``LenientOrg``; this test walks the AST of the legacy modules and fails for a symbol the table does
not mention. A symbol that a step has already moved away is simply no longer found in the module: the check only shrinks.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from . import document, legacy_symbols
from .paths import SRC

pytestmark = pytest.mark.architecture


def test_the_mapping_table_mentions_every_symbol_of_the_legacy_modules(architecture_text):
    missing = legacy_symbols.missing_from_mapping(SRC, architecture_text)
    assert not missing, "not in ARCHITECTURE.md section 5 (the manager adds the row):\n  " + "\n  ".join(missing)


def test_a_symbol_that_the_table_does_not_mention_is_reported(tmp_path, architecture_text):
    (tmp_path / "core.py").write_text(textwrap.dedent('''
        def utcnow(): ...
        def brand_new_helper(): ...
        class Org:
            def hire(self): ...
            def invented_method(self): ...
        '''), encoding="utf-8")
    missing = legacy_symbols.missing_from_mapping(tmp_path, architecture_text)
    assert missing == ["core.brand_new_helper", "core.Org.invented_method"]


def test_the_sections_of_the_document_are_found(architecture_text):
    symbols = document.mapping_symbols(architecture_text)
    assert {"5.1", "5.3", "5.5", "5.14"} <= set(symbols)
    assert "hire" in symbols["5.3"] and "utcnow" in symbols["5.1"] and "OrgBinding" in symbols["5.6"]


def test_every_legacy_module_has_a_section():
    assert set(legacy_symbols.SECTIONS) == {
        "core", "scheduler", "server", "cli", "cli_obs", "__init__", "__main__", "services", "telemetry", "observe", "progress",
        "health", "review", "blueprint", "blueprint_examples", "templates", "upgrade", "skill", "dashboard_events",
        "dashboard_data", "dashboard"}
    assert Path(SRC / "core.py").exists()
