# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json
import shutil

import pytest
from testkit.cli_world import main
from testkit.legacy.orgmcp.app import wiring
from testkit.legacy.orgmcp.core import Org


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    wiring.process_resources().reset()  # forget the open event files and counters of the process
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def read_events(org, kind=None):
    """Every event of the org, merged by time (the way a reader would)."""
    out = []
    for f in event_files(org):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))  # every line is a valid JSON object
    out.sort(key=lambda e: (e["ts"], e["seq"]))
    return [e for e in out if kind is None or e["kind"] == kind]


def test_cli_command_events(org):
    root = ["--root", str(org.root)]
    main([*root, "status"])
    with pytest.raises(SystemExit):
        main([*root, "send", "nobody", "hi"])
    ok, bad = [e for e in read_events(org, "cli.command")]
    assert (ok["command"], ok["ok"], ok["error"], ok["proc"], ok["actor"]) == ("status", True, None, "cli", "root")
    assert bad["command"] == "send" and bad["ok"] is False and "no such agent" in bad["error"]
    assert bad["error_type"] == "OrgError" and bad["ms"] >= 0


def test_cli_init_records_its_command_in_the_new_org(tmp_path):
    main(["init", str(tmp_path / "brand-new"), "--mission", "m"])
    (ev,) = read_events(Org(tmp_path / "brand-new"), "cli.command")
    assert ev["command"] == "init" and ev["ok"] is True
