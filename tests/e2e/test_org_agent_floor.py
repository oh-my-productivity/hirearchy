"""The org-agent floor, end to end (docs/design/org-agent-model-floor.md, owner decision D-E4-9): every org-agent run passes ``--effort`` (``high``
unless ORG.md says ``xhigh`` or ``max``), the allowed models are claude-sonnet-5.5 and claude-opus-5.5 (only the user widens the set), and an agent
that already runs below the floor keeps running and is named to root. The scheduler runs against the stub kiro-cli of the ``isolated_kiro`` fixture;
the calls under test go through the in-process MCP servers. Every test builds its own organization in its own ``tmp_path``.
"""

import time

from testkit.health_world import Scheduler
from testkit.kiro_world import kiro_runner

from hirearchy.core import ROOT
from hirearchy.kernel import join_frontmatter, split_frontmatter


def run_to_idle(sched, limit=5.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.01)


def run_ceo(org) -> str:
    """One scheduler run of ``ceo`` with the default runner (the stub kiro-cli); the text of its run log."""
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    first = sorted((org.dir("ceo") / "runs").glob("*.log"))[0]  # a failed run is retried: several logs, all alike
    return first.read_text(encoding="utf-8")


def pin_model(org, addr: str, model: str) -> None:
    """A charter written before the floor: ``model`` is put in its AGENT.md directly, behind ``hire`` and ``write``."""
    path = org.dir(addr) / "AGENT.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, "model": model}, body), encoding="utf-8")


def test_a_scheduler_run_passes_effort_high_and_its_run_log_shows_it(org, isolated_kiro):
    log = run_ceo(org)
    cmd = next(line for line in log.splitlines() if line.startswith("# cmd:"))
    assert "--model claude-sonnet-5.5 --effort high --v3" in cmd
    assert "--model claude-sonnet-5.5 --effort high --v3" in (isolated_kiro / "kiro-stub.log").read_text()


def test_an_effort_below_high_in_ORG_md_refuses_every_run(org, isolated_kiro):
    path = org.root / "ORG.md"
    path.write_text(path.read_text(encoding="utf-8").replace("effort: high", "effort: medium"), encoding="utf-8")
    log = run_ceo(org)
    assert '# failed to start: kiro: effort "medium" is not allowed for org agents; allowed: high, xhigh, max' in log
    stub = isolated_kiro / "kiro-stub.log"  # no kiro-cli ran at all, so there may be no log
    assert "chat --no-interactive" not in (stub.read_text() if stub.exists() else "")


def test_an_agent_that_existed_below_the_floor_keeps_its_model(org, isolated_kiro):
    pin_model(org, "ceo/eng", "claude-haiku-4.5")
    argv, _, _ = kiro_runner()(org, "ceo/eng", "P")  # no refusal and no substitution
    assert "--model claude-haiku-4.5 --effort high" in " ".join(argv)
