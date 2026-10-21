import pytest
from testkit.e2e_world import load_message, observe
from testkit.obs_fixtures import freeze, run_ids, stamp_trace

from hirearchy.core import ROOT, Org


@pytest.fixture
def org(tmp_path, clock):  # (the clock first: the runtimes of the organization are opened with it)
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/testkit/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(process_overrides):
    return freeze(process_overrides)


def test_stamp_trace_helper_roundtrips_through_the_loader(org, clock):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    stamp_trace(org, task.id, task.id)
    loaded = load_message(org, next((org.dir("ceo") / "inbox").glob("*.md")))
    assert loaded.id == task.id  # the core loader ignores the unknown key
    assert observe.build_messages(observe.scan_messages(org))[task.id].trace == task.id


def test_run_ids_helper(org, clock):
    clock.at(0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    org.begin_run("ceo")
    p = org.start_run_log("ceo")
    assert run_ids(org, "ceo") == [f"ceo@{p.stem}"]
