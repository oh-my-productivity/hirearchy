"""The org-agent floor, end to end (docs/design/org-agent-model-floor.md, owner decision D-E4-9): every org-agent run passes ``--effort`` (``high``
unless ORG.md says ``xhigh`` or ``max``), the allowed models are claude-sonnet-5.5 and claude-opus-5.5 (only the user widens the set), and an agent
that already runs below the floor keeps running and is named to root. The scheduler runs against the stub kiro-cli of the ``isolated_kiro`` fixture;
the calls under test go through the in-process MCP servers. Every test builds its own organization in its own ``tmp_path``.
"""

import asyncio
import re
import time

import pytest
from testkit.e2e_world import build_server
from testkit.health_world import Scheduler
from testkit.kiro_world import kiro_runner
from testkit.mcp_server_world import OrgBinding
from testkit.mcp_server_world import build_server as build_setup_server

from hirearchy.core import ROOT
from hirearchy.kernel import join_frontmatter, split_frontmatter

ALLOWED = "allowed: claude-sonnet-5.5, claude-opus-5.5"
MODELS = [("claude-haiku-4.5", False), ("claude-sonnet-4.6", False), ("claude-sonnet-5.5", True), ("claude-opus-5.5", True)]


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


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


# ------------------------------------------------------------------------------------------------ the refusal points


def point_hire(org, model: str) -> str | None:
    """Root hires an agent on ``model`` through its MCP server: the refusal, or None when the agent exists with that model."""
    name = f"x-{slug(model)}"  # one agent per model, so a test may hire on several
    try:
        call(build_server(org, ROOT), "hire", name=name, role="X", charter="x", model=model)
    except Exception as error:
        return str(error)
    meta, _ = split_frontmatter((org.dir(name) / "AGENT.md").read_text(encoding="utf-8"))
    assert meta["model"] == model
    return None


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", model)


def point_create_org(org, model: str) -> str | None:
    """A setup-mode root creates an organization with ``default_model=model``: the refusal, or None when ORG.md says so."""
    target = org.root.parent / f"created-{slug(model)}"
    server = build_setup_server(OrgBinding(target, None, pinned=True), ROOT)
    try:
        call(server, "create_org", mission="m", default_model=model)
    except Exception as error:
        assert not (target / "ORG.md").exists()
        return str(error)
    meta, _ = split_frontmatter((target / "ORG.md").read_text(encoding="utf-8"))
    assert meta["default_model"] == model
    return None


POINTS = {"hire": point_hire, "create_org default_model": point_create_org}


@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("model, admitted", MODELS)
def test_each_refusal_point_refuses_or_admits(org, point, model, admitted):
    refusal = POINTS[point](org, model)
    if admitted:
        assert refusal is None
    else:
        assert refusal is not None and f'model "{model}" is not allowed' in refusal and ALLOWED in refusal


def widen(org, *ids: str) -> None:
    """The user widens the set by editing ORG.md by hand."""
    path = org.root / "ORG.md"
    path.write_text(path.read_text(encoding="utf-8").replace("effort: high", f"effort: high\nextra_allowed_models: [{', '.join(ids)}]"), encoding="utf-8")


def test_a_widened_set_admits_another_model(org):
    assert point_hire(org, "claude-sonnet-4.6") is not None
    widen(org, "claude-sonnet-4.6")
    assert point_hire(org, "claude-sonnet-4.6") is None
    assert point_hire(org, "claude-haiku-4.5") is not None  # still outside the widened set
