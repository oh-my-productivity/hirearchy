"""``MemoryStrays``, the in-memory fake: both ports, and the means to prepare agents and workspace files."""

from __future__ import annotations

from pathlib import Path

from orgmcp.strays import StrayProbe, StrayRegistry
from orgmcp.strays.testing import MemoryStrays

from ._support import RED


def test_it_is_both_ports() -> None:
    fake = MemoryStrays()
    assert isinstance(fake, StrayProbe) and isinstance(fake, StrayRegistry)


@RED
def test_a_stray_goes_from_the_workspace_to_the_notice() -> None:
    fake = MemoryStrays()
    ws = Path("/w/dev").resolve()
    fake.put_agent("dev", {"role": "R", "tools": ["write"], "workspace": str(ws)})
    before = fake.probe("dev")
    fake.touch(ws / "dev", 10.0)
    fake.touch(ws / "dev" / "MEMORY.md", 11.0)
    found = fake.found_since(before, fake.probe("dev"))
    assert found == [str(ws / "dev")]
    fake.record("dev", found)
    assert f"`{ws / 'dev'}`" in fake.take_notice("dev") and fake.take_notice("dev") == ""


@RED
def test_it_touches_no_file(tmp_path: Path) -> None:
    fake = MemoryStrays()
    fake.put_agent("dev", {"role": "R", "tools": ["write"], "workspace": str(tmp_path / "ws")})
    fake.touch(tmp_path / "ws" / "dev", 1.0)
    fake.record("dev", ["/x"])
    fake.take_notice("dev")
    assert list(tmp_path.iterdir()) == []
