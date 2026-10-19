"""``RuntimeLaunchSite`` and ``ScrubbedLaunchEnvironment``: what a scheduler needs around it - a runtime directory, a log with a header, an environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.daemon._site import RuntimeLaunchSite, ScrubbedLaunchEnvironment
from orgmcp.daemon.testing import MemoryExitMarker
from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import DictEnvironment, FakeClock
from orgmcp.snapshots import RUNTIME_IGNORE_LINES
from orgmcp.snapshots.testing import MemoryIgnoreList


def site(tmp_path: Path) -> tuple[RuntimeLaunchSite, MemoryIgnoreList, MemoryExitMarker, Path]:
    root = tmp_path / "org"
    root.mkdir()
    ignore, marker = MemoryIgnoreList(), MemoryExitMarker("finished: no open tasks\n")
    return RuntimeLaunchSite(OrgPaths(root), ignore, marker, FakeClock()), ignore, marker, root


def test_prepare_makes_the_runtime_directory_and_returns_the_log(tmp_path: Path) -> None:
    launch, _, _, root = site(tmp_path)
    assert not (root / ".runtime").exists()
    assert launch.prepare() == root / ".runtime" / "scheduler.log"
    assert (root / ".runtime").is_dir()


def test_prepare_keeps_the_runtime_files_out_of_the_snapshots(tmp_path: Path) -> None:
    launch, ignore, _, _ = site(tmp_path)
    launch.prepare()
    assert ignore.text is not None and ignore.text.split() == list(RUNTIME_IGNORE_LINES)


def test_prepare_forgets_why_the_last_scheduler_exited(tmp_path: Path) -> None:
    launch, _, marker, _ = site(tmp_path)
    launch.prepare()
    assert marker.read() == ""


def test_prepare_is_repeatable(tmp_path: Path) -> None:
    launch, _, _, root = site(tmp_path)
    launch.prepare()
    launch.prepare()
    assert (root / ".runtime").is_dir()


def test_announce_appends_when_and_how_the_scheduler_was_started(tmp_path: Path) -> None:
    launch, _, _, root = site(tmp_path)
    log = launch.prepare()
    log.write_bytes(b"earlier output\n")
    launch.announce(log, ["/v/bin/orgmcp", "--root", str(root), "run", "--max-runs", "3"])
    assert log.read_text() == (
        f"earlier output\n\n# --- scheduler started 2026-10-18 10:00:00Z: /v/bin/orgmcp --root {root} run --max-runs 3\n"
    )


def test_announce_creates_the_log(tmp_path: Path) -> None:
    launch, _, _, _ = site(tmp_path)
    log = launch.prepare()
    launch.announce(log, ["orgmcp", "run"])
    assert log.read_text() == "\n# --- scheduler started 2026-10-18 10:00:00Z: orgmcp run\n"


def environment(variables: dict[str, str], root: Path) -> dict[str, str]:
    return ScrubbedLaunchEnvironment(OrgPaths(root), DictEnvironment(variables)).variables()


def test_the_environment_is_ours_bound_to_the_organization_and_unbuffered(tmp_path: Path) -> None:
    assert environment({"PATH": "/bin", "HOME": "/h"}, tmp_path) == {"PATH": "/bin", "HOME": "/h", "ORG_ROOT": str(tmp_path), "PYTHONUNBUFFERED": "1"}


def test_it_overrides_the_organization_and_buffering_of_ours(tmp_path: Path) -> None:
    got = environment({"ORG_ROOT": "/elsewhere", "PYTHONUNBUFFERED": "0"}, tmp_path)
    assert got["ORG_ROOT"] == str(tmp_path) and got["PYTHONUNBUFFERED"] == "1"


def test_it_carries_no_agent_identity(tmp_path: Path) -> None:
    got = environment({"ORG_AGENT": "ceo", "ORG_REQUIRE_AGENT": "1", "KEEP": "me"}, tmp_path)
    assert "ORG_AGENT" not in got and "ORG_REQUIRE_AGENT" not in got and got["KEEP"] == "me"


def test_it_is_a_copy(tmp_path: Path) -> None:
    source = DictEnvironment({"A": "1"})
    got = ScrubbedLaunchEnvironment(OrgPaths(tmp_path), source).variables()
    got["A"] = "2"
    assert source.get("A") == "1"
