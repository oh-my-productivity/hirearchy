# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import dataclasses
import os
import sys
import time

from testkit.legacy.orgmcp.core import ROOT

from testkit.scheduler_loop import loop_over
from orgmcp.strays import StrayProbe


# ----------------------------------------------------------------------- tool names in the prompts
def hire_writer(org, tmp_path, tools):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    org.hire(ROOT, "dev", "Developer", "Build.", tools=tools, workspace=str(ws))
    return ws


# ------------------------------------------------------------------------------ stray org files in a workspace
def script_runner(code: str):
    def build(org, addr, prompt):
        return [sys.executable, "-c", code], org.workspace_of(addr), dict(os.environ)

    return build


def run_to_end(sched, addr):
    sched.tick()
    deadline = time.time() + 20
    while sched.state.runs and time.time() < deadline:
        sched.reap()
        time.sleep(0.02)
    assert not sched.state.runs


STRAY = "import pathlib; p = pathlib.Path('dev/MEMORY.md'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('my notes')"


def test_stray_memory_in_the_workspace_is_logged_and_noticed_once(org, tmp_path):
    ws = hire_writer(org, tmp_path, ["write"])
    org.send(ROOT, "dev", "go", budget=5)
    lines = []
    sched = loop_over(org, script_runner(STRAY), echo=lines.append)
    run_to_end(sched, "dev")
    assert (ws / "dev" / "MEMORY.md").is_file() and org.memory("dev") == ""  # nothing was moved
    log = next((org.root / "dev" / "runs").glob("*.log")).read_text()
    assert f"# warning: dev created org files in its workspace with the built-in `write`" in log and str(ws / "dev") in log
    assert any("dev: warning: org files in its workspace" in x for x in lines)
    assert org.ledger("strays")["dev"] == {"paths": [str(ws / "dev")], "told": False}

    prompt = org.run_prompt("dev", [])
    assert "# Notice from the runtime (shown once)" in prompt and str(ws / "dev") in prompt
    assert '`@orgmcp/org_write` (e.g. path="dev/MEMORY.md"' in prompt and "does not move or delete" in prompt
    assert "# Notice from the runtime" not in org.run_prompt("dev", [])  # once
    assert org.ledger("strays")["dev"]["told"] is True

    org.send(ROOT, "dev", "again", budget=0)
    (ws / "dev" / "MEMORY.md").write_text("more")  # a later stray is only logged, not announced again
    os.utime(ws / "dev" / "MEMORY.md", (time.time() + 5, time.time() + 5))
    run_to_end(sched, "dev")
    assert org.ledger("strays")["dev"]["told"] is True
    assert "# Notice from the runtime" not in org.run_prompt("dev", [])


def test_stray_nested_address_tree_is_detected(org, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    org.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["write"], workspace=str(ws))
    org.hire("lead", "an", "Analyst", "Analyse.", tools=["write"], workspace=str(ws))
    org.send(ROOT, "lead", "budget for the team", budget=5)
    org.send("lead", "lead/an", "go", budget=2)
    code = "import pathlib; p = pathlib.Path('lead/an/work/x.md'); p.parent.mkdir(parents=True); p.write_text('x')"
    sched = loop_over(org, script_runner(code), echo=lambda _: None)
    sched.start("lead/an")
    deadline = time.time() + 20
    while sched.state.runs and time.time() < deadline:
        sched.reap()
        time.sleep(0.02)
    assert org.ledger("strays")["lead/an"]["paths"] == [str(ws / "lead" / "an")]


def test_no_warning_for_clean_runs_pre_existing_folders_or_agents_without_write(org, tmp_path):
    ws = hire_writer(org, tmp_path, ["write"])
    (ws / "dev").mkdir()  # already there before the run: not ours to flag
    org.send(ROOT, "dev", "go", budget=5)
    clean = "import pathlib; pathlib.Path('report.md').write_text('fine')"
    sched = loop_over(org, script_runner(clean), echo=lambda _: None)
    run_to_end(sched, "dev")
    assert org.ledger("strays") == {}
    log = next((org.root / "dev" / "runs").glob("*.log")).read_text()
    assert "# warning:" not in log
    # an agent with a workspace but no built-in write cannot have written there: no probe at all
    org.hire(ROOT, "rd", "Reader", "Read.", tools=["read"], workspace=str(ws))
    assert org.runtime.stray_probe.probe("rd") == {}


class BrokenProbe(StrayProbe):
    """A probe of the workspace that cannot read it."""

    def probe(self, addr):
        raise OSError("boom")

    def found_since(self, before, after):
        return []


def test_a_failing_stray_probe_never_stops_a_run(org, tmp_path):
    hire_writer(org, tmp_path, ["write"])
    org.send(ROOT, "dev", "go", budget=5)
    lines = []
    org.runtime = dataclasses.replace(org.runtime, stray_probe=BrokenProbe())
    sched = loop_over(org, script_runner("pass"), echo=lines.append)
    run_to_end(sched, "dev")
    assert any("stray check failed" in x for x in lines) and org.ledger("failures") == {}
