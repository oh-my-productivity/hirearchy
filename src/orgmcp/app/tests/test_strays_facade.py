"""The strays slice of the ``Org`` facade: ``stray_notice`` behaves as it always did (green before and after), and now goes through
the registry of the runtime."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from pathlib import Path

import pytest

from orgmcp.app import Org
from orgmcp.strays import StrayRegistry

RED = pytest.mark.xfail(strict=True, reason="red: B-strays")


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "dev", "Developer", "Code.", tools=["write"], workspace=str(tmp_path / "ws"))
    made.hire("root", "plain", "Plain", "Plain.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_there_is_no_notice_without_a_recorded_stray(org: Org) -> None:
    assert org.stray_notice("dev") == "" and org.ledger("strays") == {}


def test_the_notice_comes_once_and_marks_the_ledger(org: Org) -> None:
    org.save_ledger("strays", {"dev": {"paths": ["/x/dev", "/x/dev/MEMORY.md"], "told": False}, "other": {"paths": ["/o"], "told": False}})
    text = org.stray_notice("dev")
    assert text.startswith("# Notice from the runtime (shown once)\n") and "`/x/dev`, `/x/dev/MEMORY.md`" in text
    assert "`@orgmcp/org_write`" in text and 'path="dev/MEMORY.md"' in text
    assert org.ledger("strays") == {"dev": {"paths": ["/x/dev", "/x/dev/MEMORY.md"], "told": True}, "other": {"paths": ["/o"], "told": False}}
    assert org.stray_notice("dev") == ""


def test_an_agent_without_the_built_in_write_is_told_the_plain_tool_name(org: Org) -> None:
    org.save_ledger("strays", {"plain": {"paths": ["/x/plain"], "told": False}})
    assert "`@orgmcp/write`" in org.stray_notice("plain")


# -------------------------------------------------------------------------------------------- through the ports (red until wired)


class FixedRegistry(StrayRegistry):
    def __init__(self) -> None:
        self.asked: list[str] = []

    def record(self, addr: str, paths: Sequence[str]) -> None:
        raise AssertionError("the facade only asks for notices")

    def take_notice(self, addr: str) -> str:
        self.asked.append(addr)
        return f"NOTICE for {addr}"


@RED
def test_the_notice_comes_from_the_stray_registry_of_the_runtime(org: Org) -> None:
    fixed = FixedRegistry()
    org.runtime = dataclasses.replace(org.runtime, stray_registry=fixed)
    assert org.stray_notice("dev") == "NOTICE for dev" and fixed.asked == ["dev"]
    assert org.ledger("strays") == {}  # the facade no longer touches the ledger itself
