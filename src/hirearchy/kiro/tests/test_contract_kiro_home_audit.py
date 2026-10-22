"""Contract of ``KiroHomeAudit``: what a kiro home holds that kiro-cli would load into every agent (docs/design/kiro-runtime-v3.md 8.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kiro import KiroHomeAudit
from hirearchy.kiro.testing import IMPLEMENTATIONS, StateHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[KiroHomeAudit], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StateHarness:
    made = make(request, tmp_path, StateHarness)
    assert isinstance(made.audit, KiroHomeAudit)
    return made


def test_a_clean_home_has_nothing_planted(h: StateHarness) -> None:
    home = h.base / "home"
    h.dirs.private_dir(home)
    assert h.audit.planted(home) == []


def test_a_planted_entry_is_listed(h: StateHarness) -> None:
    home = h.base / "home"
    h.dirs.private_dir(home)
    h.plant(home, "settings/mcp.json")
    assert h.audit.planted(home) == ["settings/mcp.json"]


def test_the_list_is_sorted_and_relative(h: StateHarness) -> None:
    home = h.base / "home"
    h.dirs.private_dir(home)
    for rel in ("steering", "AGENTS.md", "skills"):
        h.plant(home, rel)
    found = h.audit.planted(home)
    assert found == sorted(found) == ["AGENTS.md", "skills", "steering"]
    assert not any(Path(entry).is_absolute() for entry in found)


def test_another_home_is_not_affected(h: StateHarness) -> None:
    h.dirs.private_dir(h.base / "one")
    h.dirs.private_dir(h.base / "two")
    h.plant(h.base / "one", "skills")
    assert h.audit.planted(h.base / "two") == []
