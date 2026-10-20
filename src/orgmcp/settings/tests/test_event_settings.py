# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import shutil

import pytest
from testkit.reach.orgmcp.app import wiring


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    wiring.process_resources().reset()
    return org


def test_new_config_keys_have_defaults(org):
    cfg = org.config
    assert cfg["events"] is True and cfg["events_keep_days"] == 30 and cfg["heartbeat_seconds"] == 60
