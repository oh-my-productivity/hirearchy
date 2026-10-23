"""Tests against the REAL kiro-cli and a real LLM. Skipped unless ``pytest --run-integration`` (or HIREARCHY_RUN_INTEGRATION=1).

Each one is tiny (one agent run, a short task) and asserts on files and recorded events, never on the model's wording.
They are the repeatable form of three ad-hoc checks (the studies' NOTES point here) and of the V3 confinement check:

* ``studies/O-observability-check``: ``ORG_RUN_ID`` / the agent reach the MCP server kiro spawns;
* ``studies/F-read-experiment``: a built-in ``read`` reads the org by absolute path and nothing outside it;
* ``studies/F2-tool-names``: built-in ``write`` and hirearchy ``org_write`` work side by side;
* ``test_v3_agent_uses_hirearchy_tools_and_is_confined``: on kiro-cli's V3 engine an agent reaches the hirearchy tools, reads only what it
  may, cannot run a shell it was not granted, and leaves ``~/.kiro/agents`` alone;
* ``test_an_org_agent_runs_claude_sonnet_5_5_at_high_effort``: the model floor and the effort (docs/design/org-agent-model-floor.md): an org agent
  hired on claude-sonnet-5.5 runs to the end, and its run log's ``# cmd:`` line carries ``--model claude-sonnet-5.5 --effort high --v3``.

kiro's state (homes, logs, scratch directories) is kept in ``HIREARCHY_STATE_DIR`` inside the test's tmp dir.

Model: ``$HIREARCHY_IT_MODEL``, default ``hirearchy.core.DEFAULT_MODEL``. Safety (``~/.kiro`` fenced, leftovers killed): ``tests/testkit/kiro_sandbox.py``.
"""

import json
import re
import secrets
from pathlib import Path

import pytest
from testkit.e2e_world import observe

from hirearchy.core import ROOT
from hirearchy.progress import progress

pytestmark = pytest.mark.integration


def token(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4).upper()}"


def final_result(org, task):
    return next((m for m in org.received(ROOT) if m.type == "result" and m.reply_to == task.id), None)


def run_logs(org, addr: str) -> list[Path]:
    return sorted((org.dir(addr) / "runs").glob("*.log"))


def mcp_calls(kiro, org, actor: str) -> list[dict]:
    return [e for e in kiro.events(org, "mcp") if e.get("kind") == "tool.call" and e.get("actor") == actor]


def scheduler_runs(kiro, org, agent: str) -> list[str]:
    return [e["run"] for e in kiro.events(org, "scheduler") if e.get("kind") == "run.start" and e.get("agent") == agent]


def describe(org, addr: str) -> str:
    """Tail of the agent's run logs, for assertion messages only."""
    return "\n".join(p.read_text(errors="replace")[-1500:] for p in run_logs(org, addr))


def test_agent_and_run_id_reach_the_mcp_server(real_kiro):
    """A worker with no built-in tools calls whoami, writes MEMORY.md and reports; the events name the agent and the run."""
    org = real_kiro.new_org()
    real_kiro.hire(org, "worker", "Worker", "You do small tasks exactly as asked, with hirearchy tools only.")
    note = token("MEM")
    task = real_kiro.task(
        org, "worker", "Tool check",
        "The hirearchy tools are loaded with tool_load (tool_ids [\"hirearchy::*\"]) and called with tool_call. "
        f"1) Call the whoami tool. 2) Write the single line `{note}` to your own MEMORY.md with the write tool "
        "(path worker/MEMORY.md). 3) Report the task done with the report tool.",
        "whoami called; worker/MEMORY.md contains the given line; task reported done.", budget=2)
    real_kiro.run_scheduler(org, max_runs=2)

    result = final_result(org, task)
    assert result is not None and result.status == "done", describe(org, "worker")
    assert note in org.memory("worker")

    runs = scheduler_runs(real_kiro, org, "worker")
    assert len(runs) >= 1
    calls = mcp_calls(real_kiro, org, "worker")
    tools = {c.get("tool") for c in calls}
    assert {"whoami", "write", "report"} <= tools, f"tools called: {sorted(map(str, tools))}\n{describe(org, 'worker')}"
    assert all(c.get("run") in runs for c in calls), (sorted({str(c.get("run")) for c in calls}), runs)
    assert set(runs) <= {f"worker@{p.stem}" for p in run_logs(org, "worker")}  # the run id is <agent>@<run log stem>
    assert not [e for e in real_kiro.events(org, "mcp") if e.get("kind") == "tool.call" and e.get("actor") in (None, "", ROOT)]

    print(f"evidence: model={real_kiro.model} run={runs[0]} tool.call(actor=worker)={[c['tool'] for c in calls]}")
    tr = observe.trace(org, task.id)
    m = re.search(r"runs (\d+) of (\d+)", progress(org, task.id).splitlines()[0])
    assert m, progress(org, task.id)
    assert tr["totals"]["runs"] == int(m.group(1)) == len(runs)
    assert tr["totals"]["budget_given"] == int(m.group(2)) == 2
    assert tr["totals"]["tool_calls"] >= len(calls)
    print(f"evidence: trace totals runs={tr['totals']['runs']} budget_given={tr['totals']['budget_given']} == progress {m.group(0)!r}")


def test_builtin_read_reads_the_org_but_not_outside(real_kiro):
    """An agent with kiro's built-in ``read`` opens a teammate's work file by absolute path; a file outside stays closed."""
    org = real_kiro.new_org()
    inputs = real_kiro.base / "inputs"
    outside = real_kiro.base / "outside"
    inputs.mkdir()
    outside.mkdir()
    real_kiro.hire(org, "writer", "Writer", "Holds a file; does nothing.")
    real_kiro.hire(org, "reader", "Reader", "You read files with kiro's built-in read tool and copy what you read.",
                   tools=["read"], inputs=[str(inputs)])
    org_secret, outside_secret = token("ORGFILE"), token("OUTSIDE")
    memo = org.dir("writer") / "work" / "memo.md"
    memo.parent.mkdir(parents=True, exist_ok=True)
    memo.write_text(f"{org_secret}\n", encoding="utf-8")
    (outside / "secret.txt").write_text(f"{outside_secret}\n", encoding="utf-8")
    task = real_kiro.task(
        org, "reader", "Read two files",
        f"Use kiro's BUILT-IN read tool (read_file; not the hirearchy tool org_read, not any shell) on these absolute paths. File A: {memo}. "
        f"File B: {outside / 'secret.txt'}. Then, with the hirearchy write tool, save to reader/work/copy.md the "
        "first line of file A, and the first line of file B if you could read it, else the single word DENIED. "
        "Then report the task done.",
        "reader/work/copy.md exists; the task is reported done.", budget=2)
    real_kiro.run_scheduler(org, max_runs=2)

    result = final_result(org, task)
    assert result is not None and result.status == "done", describe(org, "reader")
    copy = (org.dir("reader") / "work" / "copy.md").read_text(encoding="utf-8")
    assert org_secret in copy, copy
    reader_files = [p for p in org.dir("reader").rglob("*") if p.is_file()]
    assert reader_files
    assert not [p for p in reader_files if outside_secret in p.read_text(errors="replace")], "the file outside the org was read"
    # the task tells the agent to use kiro's built-in read; hirearchy's `org_read` stays loadable under V3, so this checks that the agent followed the instruction
    assert not [c for c in mcp_calls(real_kiro, org, "reader") if c.get("tool") in ("read", "org_read")]
    print(f"evidence: copy.md={copy.strip()!r}; reader mcp calls={[c['tool'] for c in mcp_calls(real_kiro, org, 'reader')]}")


def test_builtin_write_and_org_write_side_by_side(real_kiro):
    """read+write+shell agent with a workspace: built-in write in the workspace, hirearchy ``org_write`` for MEMORY.md and work/."""
    org = real_kiro.new_org()
    ws = real_kiro.base / "ws"
    ws.mkdir()
    real_kiro.hire(org, "dev", "Developer", "You write small files exactly as asked.",
                   tools=["read", "write", "shell"], workspace=str(ws))
    hello, note, mem = token("HELLO"), token("NOTE"), token("MEM")
    task = real_kiro.task(
        org, "dev", "Write three files",
        f"1) With kiro's built-in write tool (fs_write) create {ws / 'hello.txt'} containing exactly `{hello}`. "
        f"2) With the hirearchy tool `org_write` (loaded with tool_load, called with tool_call) write dev/work/note.md containing exactly `{note}`. "
        f"3) With `org_write` write dev/MEMORY.md containing exactly `{mem}`. 4) Report the task done.",
        "hello.txt in the workspace, dev/work/note.md and dev/MEMORY.md written as specified; reported done.", budget=2)
    real_kiro.run_scheduler(org, max_runs=2)

    result = final_result(org, task)
    assert result is not None and result.status == "done", describe(org, "dev")
    assert (ws / "hello.txt").read_text(encoding="utf-8").strip() == hello
    assert (org.dir("dev") / "work" / "note.md").read_text(encoding="utf-8").strip() == note
    assert mem in org.memory("dev")
    tools = [c.get("tool") for c in mcp_calls(real_kiro, org, "dev")]
    assert tools.count("org_write") >= 2, f"tools called: {tools}\n{describe(org, 'dev')}"
    assert "write" not in tools  # the hirearchy write tool of this agent is called org_write
    assert not (org.dir("dev") / "hello.txt").exists()
    print(f"evidence: hello.txt={(ws / 'hello.txt').read_text().strip()!r}; dev mcp calls={tools}")


def log_lines(text: str) -> list[dict]:
    """The JSON lines of kiro's debug logs (anything else is skipped)."""
    found = []
    for line in text.splitlines():
        try:
            found.append(json.loads(line))
        except ValueError:
            pass
    return found


def test_v3_agent_uses_hirearchy_tools_and_is_confined(real_kiro):
    """On the V3 engine an agent with only ``read`` and one input folder reaches the hirearchy tools, reads the input, is refused a file
    outside, has no shell, and everything is visible in the run log and kiro's own debug log (ground truth, not the model's words)."""
    org = real_kiro.new_org()
    inputs = real_kiro.base / "inputs"
    outside = real_kiro.base / "outside"
    inputs.mkdir()
    outside.mkdir()
    in_token, out_token = token("IN"), token("OUT")
    (inputs / "brief.txt").write_text(f"{in_token}\n", encoding="utf-8")
    (outside / "secret.txt").write_text(f"{out_token}\n", encoding="utf-8")
    canary = real_kiro.base / "shell-canary"
    real_kiro.hire(org, "probe", "Probe", "You do small checks exactly as asked.", tools=["read"], inputs=[str(inputs)])
    task = real_kiro.task(
        org, "probe", "Confinement probe",
        "The hirearchy tools are loaded with tool_load (tool_ids [\"hirearchy::*\"]) and called with tool_call. "
        "1) Call the whoami tool. "
        f"2) With kiro's read tool read {inputs / 'brief.txt'} and {outside / 'secret.txt'} (absolute paths). "
        f"3) If you have a shell tool, run `touch {canary}`; if you have none, note NO-SHELL. "
        "4) With the hirearchy write tool write what you read from each file (or the single word DENIED where the read was refused) "
        "to probe/work/out.md. 5) Report the task done.",
        "probe/work/out.md exists; the task is reported done.", budget=2)
    real_kiro.run_scheduler(org, max_runs=2)

    result = final_result(org, task)
    assert result is not None and result.status == "done", describe(org, "probe")
    runs = scheduler_runs(real_kiro, org, "probe")
    calls = mcp_calls(real_kiro, org, "probe")
    tools = {c.get("tool") for c in calls}
    assert runs and {"whoami", "report"} <= tools, f"tools called: {sorted(map(str, tools))}\n{describe(org, 'probe')}"
    assert all(c.get("run") in runs for c in calls), (sorted({str(c.get("run")) for c in calls}), runs)

    out = (org.dir("probe") / "work" / "out.md").read_text(encoding="utf-8")
    assert in_token in out, out
    everything = [p for p in org.root.rglob("*") if p.is_file() and ".runtime" not in p.parts[len(org.root.parts):]]
    assert not [p for p in everything if out_token in p.read_text(errors="replace")], "the file outside the allowed folders was read"
    transcript = real_kiro.transcript(org, "probe")
    assert out_token not in transcript, "the forbidden file's content reached the run log"
    kiro_log = real_kiro.kiro_logs(org)
    assert out_token not in kiro_log

    denied_in_transcript = "[tool failed]" in transcript and "Tool call denied" in transcript and "Source: agent-profile" in transcript
    messages = [str(entry.get("message", "")) for entry in log_lines(kiro_log)]
    denied_in_log = any(m.startswith("acp.policy-eval.complete") and '"effect":"deny"' in m and '"capability":"fs_read"' in m for m in messages)
    assert denied_in_transcript or denied_in_log, "no fs_read denial in the run log or kiro.log\n" + transcript[-1500:]
    assert not canary.exists(), "the shell the agent was not granted ran"

    surfaces = [m for m in messages if m.startswith("custom_agent.tool_selection.tools")]
    assert surfaces, "kiro.log has no tool surface (KIRO_LOG_LEVEL=debug)"
    assert all("read_file" in m and "execute_bash" not in m for m in surfaces), surfaces
    logs = [p.read_text(errors="replace") for p in sorted((org.dir("probe") / "runs").glob("*.log"))]
    assert logs and all("# kiro: run started (engine v3)" in text for text in logs), logs
    print(f"evidence: model={real_kiro.model} runs={runs} tool.call(actor=probe)={sorted(map(str, tools))} "
          f"denied(transcript={denied_in_transcript}, kiro.log={denied_in_log}) tool surfaces={len(surfaces)} canary={canary.exists()}")


def test_an_org_agent_runs_claude_sonnet_5_5_at_high_effort(real_kiro):
    """The floor of the org agents (D-E4-9): a run on claude-sonnet-5.5 passes ``--effort high`` to the real kiro-cli, succeeds, and says so in its run log."""
    org = real_kiro.new_org()
    org.hire(ROOT, "worker", "Worker", "You do small tasks exactly as asked, with hirearchy tools only.", model="claude-sonnet-5.5")
    task = real_kiro.task(
        org, "worker", "Effort check",
        "The hirearchy tools are loaded with tool_load (tool_ids [\"hirearchy::*\"]) and called with tool_call. "
        "1) Call the whoami tool. 2) Report the task done with the report tool.",
        "whoami called; task reported done.", budget=2)
    real_kiro.run_scheduler(org, max_runs=2)

    result = final_result(org, task)
    assert result is not None and result.status == "done", describe(org, "worker")
    runs = scheduler_runs(real_kiro, org, "worker")
    logs = run_logs(org, "worker")
    assert runs and logs, describe(org, "worker")
    first = logs[0].read_text(encoding="utf-8", errors="replace")
    cmd = next(line for line in first.splitlines() if line.startswith("# cmd:"))
    assert "--model claude-sonnet-5.5 --effort high --v3" in cmd, cmd
    assert "# kiro: run started (engine v3)" in first, first[-1500:]
    print(f"evidence: model=claude-sonnet-5.5 effort=high runs={runs} result={result.status}")
    print(f"evidence: {cmd}")
