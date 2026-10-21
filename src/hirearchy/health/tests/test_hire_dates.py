"""``CharterHireDates`` and ``FsCharterStamp``: when an agent was hired - the ``created`` of its charter, else the time its charter file was written."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.agents.testing import MemoryAgents, fs_agents
from hirearchy.health._hired import CharterHireDates
from hirearchy.health._ports import CharterStamp, FsCharterStamp, HireDates
from hirearchy.health.testing import MemoryCharterStamps, at
from hirearchy.kernel import OrgPaths

WRITTEN = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)


def charter(created: str | None) -> str:
    line = "" if created is None else f"created: {created}\n"
    return f"---\nrole: Worker\n{line}---\n# Role: Worker\n\nDo the work.\n"


def test_the_charter_says_when(tmp_path: Path) -> None:
    agents = MemoryAgents()
    agents.put("ceo/AGENT.md", charter(f'"{at(1234).isoformat()}"'))
    hired = CharterHireDates(agents, MemoryCharterStamps())
    assert isinstance(hired, HireDates) and hired.hired("ceo") == at(1234)


def test_a_yaml_timestamp_without_a_zone_is_utc(tmp_path: Path) -> None:
    agents = MemoryAgents()
    agents.put("ceo/AGENT.md", charter("2026-01-01T12:00:10"))  # PyYAML reads it as a naive datetime
    assert CharterHireDates(agents, MemoryCharterStamps()).hired("ceo") == at(10)


@pytest.mark.parametrize("created", [None, "soon", '""', "[1, 2]"])
def test_without_a_usable_date_the_time_the_charter_was_written_counts(created: str | None) -> None:
    agents, stamps = MemoryAgents(), MemoryCharterStamps()
    agents.put("ceo/AGENT.md", charter(created))
    stamps.times["ceo"] = WRITTEN
    assert CharterHireDates(agents, stamps).hired("ceo") == WRITTEN


def test_a_charter_that_is_not_there_is_an_error_the_caller_sees() -> None:
    with pytest.raises(FileNotFoundError):
        CharterHireDates(MemoryAgents(), MemoryCharterStamps()).hired("ghost")


def test_the_file_stamp_is_the_modification_time_of_agent_md_in_utc(tmp_path: Path) -> None:
    disk = fs_agents(tmp_path)
    disk.put("ceo/AGENT.md", charter(None))
    os.utime(tmp_path / "ceo" / "AGENT.md", (WRITTEN.timestamp(), WRITTEN.timestamp()))
    stamp = FsCharterStamp(OrgPaths(tmp_path))
    assert isinstance(stamp, CharterStamp) and stamp.modified("ceo") == WRITTEN
    assert CharterHireDates(disk.charters, stamp).hired("ceo") == WRITTEN


def test_the_file_stamp_of_an_agent_without_a_charter_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        FsCharterStamp(OrgPaths(tmp_path)).modified("ceo")
