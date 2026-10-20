# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import shutil
import subprocess

import pytest
from testkit.legacy.orgmcp.app import wiring
from testkit.legacy.orgmcp.core import ROOT, Org


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    wiring.process_resources().reset()
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def test_new_orgs_ignore_the_events_in_git(tmp_path):
    org = Org.init(tmp_path / "fresh", "m")
    assert ".runtime/events/" in (org.root / ".gitignore").read_text().split()
    org.hire(ROOT, "ceo", "CEO", "c", can_hire=True)
    org.send(ROOT, "ceo", "hi")
    org.commit("after events")
    tracked = subprocess.run(["git", "ls-files"], cwd=org.root, capture_output=True, text=True).stdout
    assert event_files(org) and ".runtime/events" not in tracked


def test_existing_orgs_get_the_ignore_line_from_the_scheduler_and_from_the_first_event(tmp_path):
    org = Org.init(tmp_path / "old", "m")
    (org.root / ".gitignore").write_text(".tmp-*\nruns/\n.kiro/\n.runtime/scheduler.pid\n")
    org.runtime.ignore_list.ensure_runtime_files()
    assert ".runtime/events/" in (org.root / ".gitignore").read_text().split()
    (org.root / ".gitignore").write_text(".tmp-*\nruns/\n")
    org.emit("custom.kind")  # the first event of an org that predates the event log
    assert ".runtime/events/" in (org.root / ".gitignore").read_text().split()
