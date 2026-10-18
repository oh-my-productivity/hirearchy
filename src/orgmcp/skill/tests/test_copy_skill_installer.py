"""``CopySkillInstaller``: the order in which it asks its two collaborators, seen through recording doubles."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.skill import SkillSource, SkillStore
from orgmcp.skill._install import CopySkillInstaller


class Source(SkillSource):
    def __init__(self, calls: list[str], text: str | None) -> None:
        self.calls, self.text = calls, text

    def read(self) -> str:
        self.calls.append("source.read")
        if self.text is None:
            raise OrgError("no source")
        return self.text


class Store(SkillStore):
    def __init__(self, calls: list[str], existing: str | OrgError | None = None) -> None:
        self.calls, self.existing = calls, existing
        self.written: list[tuple[Path | None, str]] = []

    def target(self, dest: Path | None) -> Path:
        self.calls.append(f"store.target({dest})")
        return Path("/skills/orgmcp/SKILL.md")

    def read_existing(self, dest: Path | None) -> str | None:
        self.calls.append(f"store.read_existing({dest})")
        if isinstance(self.existing, OrgError):
            raise self.existing
        return self.existing

    def write(self, dest: Path | None, text: str) -> str:
        self.calls.append(f"store.write({dest})")
        self.written.append((dest, text))
        return "/skills/orgmcp/SKILL.md"


def test_the_source_is_read_before_the_store_is_touched() -> None:
    calls: list[str] = []
    with pytest.raises(OrgError, match="no source"):
        CopySkillInstaller(Source(calls, None), Store(calls)).install_skill("/x")
    assert calls == ["source.read"]


def test_a_fresh_install_reads_the_store_once_and_writes_once() -> None:
    calls: list[str] = []
    store = Store(calls)
    CopySkillInstaller(Source(calls, "text"), store).install_skill("/x")
    assert calls[0] == "source.read" and calls.count("store.read_existing(/x)") == 1 and calls.count("store.write(/x)") == 1
    assert store.written == [(Path("/x"), "text")]


def test_an_up_to_date_file_is_not_written() -> None:
    calls: list[str] = []
    store = Store(calls, existing="text")
    assert CopySkillInstaller(Source(calls, "text"), store).install_skill("/x", force=True).endswith("already installed and up to date")
    assert store.written == []


def test_a_refused_overwrite_writes_nothing() -> None:
    calls: list[str] = []
    store = Store(calls, existing="other")
    with pytest.raises(OrgError, match="--force"):
        CopySkillInstaller(Source(calls, "text"), store).install_skill("/x")
    assert store.written == []


def test_an_error_of_the_store_is_not_turned_into_anything_else() -> None:
    calls: list[str] = []
    store = Store(calls, existing=OrgError("exactly this"))
    with pytest.raises(OrgError, match="^exactly this$"):
        CopySkillInstaller(Source(calls, "text"), store).install_skill("/x", force=True)
    assert store.written == []


def test_the_destination_reaches_the_store_as_a_path_and_none_stays_none() -> None:
    calls: list[str] = []
    store = Store(calls)
    installer = CopySkillInstaller(Source(calls, "text"), store)
    installer.install_skill("~/a")
    installer.install_skill(None)
    installer.install_skill("")
    assert [dest for dest, _ in store.written] == [Path("~/a"), None, None]
