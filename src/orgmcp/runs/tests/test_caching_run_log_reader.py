"""``CachingRunLogReader``: the run counter of the dashboard, cached per directory mtime (what ``LenientOrg.runs_used`` did)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import FakeClock, system_clock
from orgmcp.runs import RunLogReader
from orgmcp.runs._caching import CachingRunLogReader, DirectoryStamps, FsDirectoryStamps
from orgmcp.runs._reader import FsRunLogReader

from . import _oracle
from ._reach import reach

NS = 1_000_000_000
QUIET = 10 * NS  # a directory that was last modified this long before it was listed is trusted


class CountingReader(FsRunLogReader):
    def __init__(self, paths: OrgPaths) -> None:
        super().__init__(paths)
        self.counted = 0

    def count(self, addr: str) -> int:
        self.counted += 1
        return super().count(addr)


class StubStamps(DirectoryStamps):
    """The mtime of every directory is whatever the test says."""

    def __init__(self) -> None:
        self.mtimes: dict[tuple[str, str], int] = {}

    def mtime(self, addr: str, name: str) -> int:
        return self.mtimes.get((addr, name), -1)


def make_log(root: Path, addr: str, stem: str) -> None:
    runs = root / addr / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{stem}.log").write_text("x", encoding="utf-8")


@pytest.fixture
def org(tmp_path: Path) -> Path:
    (tmp_path / "ceo").mkdir()
    return tmp_path


def now_ns(clock: FakeClock) -> int:
    return int(clock.time() * NS)


def test_it_is_a_reader(org: Path) -> None:
    clock = FakeClock()
    assert isinstance(CachingRunLogReader(FsRunLogReader(OrgPaths(org)), StubStamps(), clock), RunLogReader)


def test_a_directory_that_does_not_exist_has_no_runs_and_is_not_listed(org: Path) -> None:
    inner = CountingReader(OrgPaths(org))
    assert CachingRunLogReader(inner, StubStamps(), FakeClock()).count("ceo") == 0 and inner.counted == 0


def test_a_quiet_directory_is_listed_once(org: Path) -> None:
    make_log(org, "ceo", "20261018T100000000001")
    clock, stamps, inner = FakeClock(), StubStamps(), CountingReader(OrgPaths(org))
    stamps.mtimes[("ceo", "runs")] = now_ns(clock) - QUIET
    reader = CachingRunLogReader(inner, stamps, clock)
    assert [reader.count("ceo"), reader.count("ceo"), reader.count("ceo")] == [1, 1, 1] and inner.counted == 1


def test_a_changed_directory_is_listed_again(org: Path) -> None:
    make_log(org, "ceo", "20261018T100000000001")
    clock, stamps, inner = FakeClock(), StubStamps(), CountingReader(OrgPaths(org))
    stamps.mtimes[("ceo", "runs")] = now_ns(clock) - QUIET
    reader = CachingRunLogReader(inner, stamps, clock)
    assert reader.count("ceo") == 1
    make_log(org, "ceo", "20261018T100000000002")
    assert reader.count("ceo") == 1  # the directory looks unchanged: the cached number is trusted
    stamps.mtimes[("ceo", "runs")] += 1
    assert reader.count("ceo") == 2 and inner.counted == 2


def test_a_directory_changed_a_moment_ago_is_not_trusted(org: Path) -> None:
    """Coarse file system times: a listing of a directory modified within 2 s of the listing may miss a change in that same tick."""
    make_log(org, "ceo", "20261018T100000000001")
    clock, stamps, inner = FakeClock(), StubStamps(), CountingReader(OrgPaths(org))
    stamps.mtimes[("ceo", "runs")] = now_ns(clock) - 1 * NS
    reader = CachingRunLogReader(inner, stamps, clock)
    reader.count("ceo")
    make_log(org, "ceo", "20261018T100000000002")
    assert reader.count("ceo") == 2 and inner.counted == 2


def test_a_directory_quiet_for_just_over_two_seconds_is_trusted_and_just_under_is_not(org: Path) -> None:
    make_log(org, "ceo", "20261018T100000000001")
    clock, stamps, inner = FakeClock(), StubStamps(), CountingReader(OrgPaths(org))
    reader = CachingRunLogReader(inner, stamps, clock)
    stamps.mtimes[("ceo", "runs")] = now_ns(clock) - int(2.01 * NS)
    reader.count("ceo")
    reader.count("ceo")
    assert inner.counted == 1
    stamps.mtimes[("ceo", "runs")] = now_ns(clock) - int(1.99 * NS)
    reader.count("ceo")
    reader.count("ceo")
    assert inner.counted == 3


def test_every_agent_has_its_own_entry_and_the_address_is_normalised(org: Path) -> None:
    make_log(org, "ceo", "20261018T100000000001")
    (org / "ops").mkdir()
    make_log(org, "ops", "20261018T100000000001")
    make_log(org, "ops", "20261018T100000000002")
    clock, stamps, inner = FakeClock(), StubStamps(), CountingReader(OrgPaths(org))
    for key in (("ceo", "runs"), ("ops", "runs")):
        stamps.mtimes[key] = now_ns(clock) - QUIET
    reader = CachingRunLogReader(inner, stamps, clock)
    assert (reader.count("ceo"), reader.count("ops"), reader.count("ceo"), reader.count("ops")) == (1, 2, 1, 2) and inner.counted == 2
    reader.count(" /ceo/ ")
    assert inner.counted == 2


def test_everything_but_the_count_is_the_inner_readers(org: Path) -> None:
    make_log(org, "ceo", "20261018T100000000001")
    inner = FsRunLogReader(OrgPaths(org))
    reader = CachingRunLogReader(inner, StubStamps(), FakeClock())
    path = org / "ceo" / "runs" / "20261018T100000000001.log"
    assert reader.files("ceo") == inner.files("ceo") and reader.windows("ceo") == inner.windows("ceo")
    assert reader.outcomes("ceo") == inner.outcomes("ceo") and reader.last_end("ceo") == inner.last_end("ceo")
    assert reader.facts(path) == inner.facts(path) and reader.tail(path, 10, 10) == inner.tail(path, 10, 10)
    assert reader.head(path, 10) == inner.head(path, 10)


def test_the_stamps_are_the_modification_times_of_the_directories_of_the_organization(org: Path) -> None:
    stamps = FsDirectoryStamps(OrgPaths(org))
    assert isinstance(stamps, DirectoryStamps) and stamps.mtime("ceo", "runs") == -1
    make_log(org, "ceo", "20261018T100000000001")
    assert stamps.mtime("ceo", "runs") == (org / "ceo" / "runs").stat().st_mtime_ns
    assert stamps.mtime("ceo", "") == (org / "ceo").stat().st_mtime_ns
    assert stamps.mtime("root", "") == org.stat().st_mtime_ns and stamps.mtime("root", "ceo") == (org / "ceo").stat().st_mtime_ns


def test_it_counts_as_the_dashboard_org_did_in_every_situation(tmp_path: Path) -> None:
    """Characterization of ``LenientOrg.runs_used`` (frozen in ``_oracle.LenientRuns``): same numbers, also while the cache is stale."""
    root = reach("core").Org.init(tmp_path / "org", "mission").root
    (root / "ceo").mkdir()
    lenient = _oracle.LenientRuns(root)
    paths = OrgPaths(root)
    reader = CachingRunLogReader(FsRunLogReader(paths), FsDirectoryStamps(paths), system_clock(tmp_path))
    runs = root / "ceo" / "runs"

    def both() -> tuple[int, int]:
        lenient.tick()
        return lenient.runs_used("ceo"), reader.count("ceo")

    def quiet(seconds: float) -> int:
        stamp = time.time_ns() - int(seconds * NS)
        os.utime(runs, ns=(stamp, stamp))
        return stamp

    assert both() == (0, 0)
    make_log(root, "ceo", "20261018T100000000001")
    assert both() == (1, 1)
    make_log(root, "ceo", "20261018T100000000002")
    assert both() == (2, 2)
    stamp = quiet(30)  # the directory has been quiet for 30 s: listings are trusted from now on
    assert both() == (2, 2)
    make_log(root, "ceo", "20261018T100000000003")
    os.utime(runs, ns=(stamp, stamp))  # ... and a change that does not show in the directory time is not seen, by either
    assert both() == (2, 2)
    quiet(20)  # now it does show
    assert both() == (3, 3)
    (runs / "20261018T100000000003.log").unlink()
    quiet(10)
    assert both() == (2, 2)
