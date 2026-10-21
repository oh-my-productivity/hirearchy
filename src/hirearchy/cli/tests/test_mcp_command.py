"""``mcp``: serves the tools of the identity the environment names, over stdio, without an organization being named on the command line (characterization)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from hirearchy.kernel import ROOT

from ._org import Org, facade


@pytest.fixture
def org(tmp_path: Path) -> Org:
    org = facade().init(tmp_path / "org", "A mission.")
    org.hire(ROOT, "ceo", "Chief", "Run it.")
    return org


def run_mcp(env_extra: dict[str, str], drop: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **env_extra}
    for var in drop:
        env.pop(var, None)
    return subprocess.run([sys.executable, "-m", "hirearchy", "mcp"], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)


def test_the_server_of_an_agent_starts_and_ends_with_its_input(org: Org) -> None:
    done = run_mcp({"ORG_ROOT": str(org.root), "ORG_AGENT": "ceo"}, drop=("ORG_REQUIRE_AGENT",))
    assert done.returncode == 0 and done.stdout == "" and "error" not in done.stderr.lower()


def test_the_server_of_root_starts_in_an_existing_organization(org: Org) -> None:
    done = run_mcp({"ORG_ROOT": str(org.root)}, drop=("ORG_REQUIRE_AGENT", "ORG_AGENT"))
    assert done.returncode == 0 and "error" not in done.stderr.lower()


def test_an_agent_without_its_organization_fails_at_once(tmp_path: Path) -> None:
    done = run_mcp({"ORG_ROOT": str(tmp_path / "nope"), "ORG_AGENT": "ceo"})
    assert done.returncode == 1 and "not an organization" in done.stderr
