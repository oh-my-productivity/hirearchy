# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import shutil

from testkit.health_world import Scheduler, agent_health, org_health
from testkit.legacy.orgmcp.core import ROOT, join_frontmatter, split_frontmatter, utcnow

TRUE = shutil.which("true") or "/usr/bin/true"


def quiet_runner(argv=None):
    """A runner that execs a trivial command instead of kiro (no network, no ~/.kiro writes)."""

    def build(org, addr, prompt):
        return (argv or [TRUE]), org.dir(addr), dict(os.environ)

    return build


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def test_qa5_bad_health_threshold_does_not_crash_tick(org):
    configure(org, review_every_seconds=0, health={"idle_after_seconds": "1h"})
    sched = Scheduler(org, quiet_runner(), echo=lambda _: None)
    sched.tick()  # first tick starts the review clock
    sched.tick()  # review is due: must degrade (default threshold / OrgError), not raise TypeError
    org_health(org)  # same for `orgmcp health` / the health tool


def test_qa14_failed_runs_are_not_blamed_as_wasteful(org):
    org.send(ROOT, "ceo", "budget", budget=10)
    runs = org.dir("ceo") / "runs"
    for i in range(5):
        (runs / f"20260101T0000000000{i:02d}.log").write_text(f"# failed to start: kiro-cli not found\n")
    flags = agent_health(org, "ceo", utcnow()).flags
    assert "wasteful" not in flags
