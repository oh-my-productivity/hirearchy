# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from pathlib import Path

import pytest
from testkit.legacy.orgmcp.app.wire_daemon import identity


def _looks_like_scheduler_of(command, root):
    """Does this command line plausibly start the scheduler of the organization at ``root``? (``SchedulerIdentity``)"""
    return identity().recognises(command, root)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)


def test_command_line_verification():
    root = Path("/orgs/one")
    ok = [
        "/v/bin/python /v/bin/orgmcp --root /orgs/one run",
        "/v/bin/orgmcp --root /orgs/one run --max-runs 3",
        "/usr/bin/python3 -m orgmcp run --until-idle",  # started from inside the org (no --root)
        "python3 /x/serve.py run /orgs/one",
    ]
    bad = [
        "sleep 60", "vim /orgs/one/ORG.md", "/v/bin/orgmcp mcp", "/v/bin/orgmcp --root /orgs/two run",
        "/v/bin/orgmcp --root org run", "python -m http.server run", "",
    ]
    assert all(_looks_like_scheduler_of(c, root) for c in ok)
    assert not any(_looks_like_scheduler_of(c, root) for c in bad)


def test_command_line_verification_follows_symlinks_and_rejects_other_dirs(tmp_path):
    real = tmp_path / "real" / "org"
    real.mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "real")  # like /tmp -> /private/tmp: the command line has one spelling, the org another
    other = tmp_path / "other"
    other.mkdir()
    assert _looks_like_scheduler_of(f"/v/bin/orgmcp --root {link}/org run --until-idle", real)
    assert _looks_like_scheduler_of(f"/v/bin/orgmcp --root={link}/org run", real)
    assert not _looks_like_scheduler_of(f"/v/bin/orgmcp --root {other} run", real)
    assert not _looks_like_scheduler_of(f"/v/bin/orgmcp --root {link}/org mcp", real)
