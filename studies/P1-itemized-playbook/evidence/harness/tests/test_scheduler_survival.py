"""Tests of scheduler_survival.py (D-SURVIVE, D-SIGNAL, M-C-8; E7 Interpretation 18's starter rule, Correction 9's header).

Synthetic event streams live in tmp_path; the E7 tests read E7's committed evidence read-only."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
sys.dont_write_bytecode = True

E7EV = Path("/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence")
SCRIPT = HARNESS / "scheduler_survival.py"
PY = sys.executable
e7 = pytest.mark.skipif(not (E7EV / "s1" / "events").exists(), reason="E7 evidence not available")


def run(*args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([PY, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=env)


# ------------------------------------------------------------------ synthetic stream
def T(sec):
    """UTC timestamp `sec` seconds after 10:00:00 on 2026-11-01."""
    s = int(sec)
    ms = int(round((sec - s) * 1000))
    return f"2026-11-01T10:{s // 60:02d}:{s % 60:02d}.{ms:03d}000+00:00"


def mk(tmp_path, events, turn_ends, turn_starts=None, turn_times=None, inj_log=None):
    d = tmp_path / "s"
    (d / "events" / "2026-11-01").mkdir(parents=True)
    byfile = {}
    for fname, e in events:
        byfile.setdefault(fname, []).append(e)
    for fname, es in byfile.items():
        (d / "events" / "2026-11-01" / fname).write_text("\n".join(json.dumps(e) for e in es) + "\n")
    lines = []
    for n, te in enumerate(turn_ends, 1):
        ts = (turn_starts or {}).get(n, 0.0)
        lines.append(f"turn {n}: user_ts x turn_start {T(ts).replace('+00:00', 'Z')} turn_end {T(te).replace('+00:00', 'Z')} stop end_turn status success elapsed_ms 1 credits 1.0")
    (d / "session-turn-times-utc.txt").write_text("\n".join(lines) + "\n")
    if turn_times is not None:
        (d / "turn-times.txt").write_text(turn_times)
    if inj_log is not None:
        (d / "injection").mkdir()
        (d / "injection" / "injection-log.txt").write_text(inj_log)
    return d


def ev(sec, kind, pid, **kw):
    return dict({"ts": T(sec), "kind": kind, "pid": pid}, **kw)


def start_call(sec, mcp_pid, ms=100.0):
    return (f"mcp-{mcp_pid}-1.jsonl", ev(sec, "tool.call", mcp_pid, tool="start", ms=ms, ok=True))


def analyse(d):
    import scheduler_survival as ss
    return ss.analyse(Path(d))


def test_the_starter_is_the_start_call_whose_interval_holds_the_scheduler_start(tmp_path):
    # start call A: interval [4.9, 5.0]; scheduler start at 4.95 -> A. Call B (interval [5.9,6.0]) is the NEXT call: a "last start before" rule would pick A for a scheduler
    # started at 5.5 and B's own scheduler (5.95) would be credited to A too; the interval rule keeps them apart.
    events = [start_call(5.0, 11, ms=100), start_call(6.0, 12, ms=100),
              ("scheduler-21-1.jsonl", ev(4.95, "scheduler.start", 21)), ("scheduler-22-1.jsonl", ev(5.95, "scheduler.start", 22))]
    a = analyse(mk(tmp_path, events, [20]))
    by = {s["pid"]: s for s in a["schedulers"]}
    assert by[21]["starter"]["mcp_pid"] == 11 and by[22]["starter"]["mcp_pid"] == 12
    assert by[21]["starter"]["kind"] == "assistant"


def test_a_scheduler_whose_start_lies_in_no_start_call_interval_has_an_unknown_starter(tmp_path):
    events = [start_call(5.0, 11, ms=100), ("scheduler-21-1.jsonl", ev(8.0, "scheduler.start", 21))]
    a = analyse(mk(tmp_path, events, [20]))
    assert a["schedulers"][0]["starter"]["kind"] == "unknown"


def test_the_injection_scripts_server_is_named_in_the_injection_log(tmp_path):
    events = [start_call(5.0, 11), ("scheduler-21-1.jsonl", ev(4.95, "scheduler.start", 21))]
    a = analyse(mk(tmp_path, events, [20], inj_log="scheduler started (pid 21; x)\n"))
    assert a["schedulers"][0]["starter"]["kind"] == "script"
    assert a["counts"]["script_started"] == 1 and a["counts"]["assistant_started"] == 0


def sched(pid, start, exit_at=None, reason="finished: no open tasks", mcp=11, call_at=None):
    es = [start_call(call_at if call_at is not None else start + 0.05, mcp), (f"scheduler-{pid}-1.jsonl", ev(start, "scheduler.start", pid))]
    if exit_at is not None:
        es.append((f"scheduler-{pid}-1.jsonl", ev(exit_at, "scheduler.exit", pid, reason=reason)))
    return es


def test_a_scheduler_that_exits_on_its_own_before_the_turn_end_is_not_running_at_the_end(tmp_path):
    a = analyse(mk(tmp_path, sched(21, 1.0, exit_at=10.0), [20]))
    s = a["schedulers"][0]
    assert s["running_at_turn_ends"] == []
    assert a["m_c_1"] == {"k": 0, "n": 1} and a["m_c_2_pairs"] == {"k": 0, "n": 0}


def test_a_scheduler_that_ends_itself_within_5_seconds_of_the_turn_end_is_not_running_at_the_end(tmp_path):
    a = analyse(mk(tmp_path, sched(21, 1.0, exit_at=17.0), [20]))  # own exit, 3 s before: E7 Interpretation 18
    assert a["schedulers"][0]["running_at_turn_ends"] == []


def test_a_scheduler_still_running_at_the_turn_end_that_finishes_later_survives(tmp_path):
    events = sched(21, 1.0, exit_at=60.0) + [("scheduler-21-1.jsonl", ev(5.0, "run.start", 21, run="lead@A")),
                                             ("scheduler-21-1.jsonl", ev(50.0, "run.end", 21, run="lead@A", ok=True, killed=False))]
    a = analyse(mk(tmp_path, events, [20]))
    pair = a["schedulers"][0]["running_at_turn_ends"][0]
    assert pair["turn"] == 1 and pair["in_flight"] == ["lead@A"] and pair["survived"] is True and pair["class"] == "survived"
    assert a["m_c_2_pairs"] == {"k": 1, "n": 1} and a["m_c_2_runs"] == {"k": 1, "n": 1} and a["m_c_1"] == {"k": 1, "n": 1}


def test_no_scheduler_exit_means_died_with_the_call(tmp_path):
    a = analyse(mk(tmp_path, sched(21, 1.0), [20]))
    pair = a["schedulers"][0]["running_at_turn_ends"][0]
    assert pair["survived"] is False and pair["class"] == "died with the call"
    assert a["m_c_2_pairs"] == {"k": 0, "n": 1}


def test_stopped_by_sigterm_after_the_turn_end_with_no_recorded_stop_is_died_later_beyond_5_s(tmp_path):
    a = analyse(mk(tmp_path, sched(21, 1.0, exit_at=40.0, reason="stopped by SIGTERM"), [20]))
    assert a["schedulers"][0]["running_at_turn_ends"][0]["class"] == "died later"
    a = analyse(mk(tmp_path / "b", sched(21, 1.0, exit_at=22.0, reason="stopped by SIGTERM"), [20]))
    assert a["schedulers"][0]["running_at_turn_ends"][0]["class"] == "died with the call"


def test_a_sigterm_exit_within_5_s_before_the_turn_end_counts_as_running_and_died_with_the_call(tmp_path):
    # the signal extension of D-SURVIVE (E7 item 5): C1's DENn2 wrote the handled stop 727 ms before the chat returned
    a = analyse(mk(tmp_path, sched(21, 1.0, exit_at=19.3, reason="stopped by SIGTERM"), [20]))
    pair = a["schedulers"][0]["running_at_turn_ends"][0]
    assert pair["class"] == "died with the call"


def test_a_sigterm_after_an_assistant_stop_call_is_a_recorded_stop_and_the_scheduler_survived(tmp_path):
    events = sched(21, 1.0, exit_at=25.0, reason="stopped by SIGTERM") + [
        ("mcp-11-1.jsonl", ev(24.0, "tool.call", 11, tool="stop", ms=5.0, ok=True))]
    a = analyse(mk(tmp_path, events, [20]))
    assert a["schedulers"][0]["running_at_turn_ends"][0]["class"] == "survived"


def test_error_exits_are_classed_error(tmp_path):
    a = analyse(mk(tmp_path, sched(21, 1.0, exit_at=30.0, reason="error: boom"), [20]))
    assert a["schedulers"][0]["running_at_turn_ends"][0]["class"] == "error"


def test_a_run_in_flight_killed_without_a_stop_means_the_scheduler_did_not_survive(tmp_path):
    events = sched(21, 1.0, exit_at=40.0) + [("scheduler-21-1.jsonl", ev(5.0, "run.start", 21, run="lead@A")),
                                             ("scheduler-21-1.jsonl", ev(30.0, "run.end", 21, run="lead@A", ok=False, killed=True))]
    a = analyse(mk(tmp_path, events, [20]))
    pair = a["schedulers"][0]["running_at_turn_ends"][0]
    assert pair["survived"] is False and pair["class"] == "died with the call"
    assert a["m_c_2_runs"] == {"k": 0, "n": 1}


def test_signals_are_listed_with_what_followed_and_explained_only_by_a_stop_within_30_s(tmp_path):
    sig = lambda sec: ("scheduler-21-1.jsonl", ev(sec, "scheduler.signal", 21, signal="SIGTERM", action="stop", ppid=1, running=["lead@A"]))  # noqa: E731
    base = sched(21, 1.0, exit_at=35.0, reason="stopped by SIGTERM") + [sig(34.9),
        ("scheduler-21-1.jsonl", ev(5.0, "run.start", 21, run="lead@A")), ("scheduler-21-1.jsonl", ev(35.0, "run.end", 21, run="lead@A", ok=False, killed=True))]
    a = analyse(mk(tmp_path, base, [40]))
    g = a["signals"][0]
    assert g["explained"] is False and g["exit_after"]["reason"] == "stopped by SIGTERM" and g["runs"][0]["killed"] is True
    assert a["m_c_6"] == {"k": 1, "n": 1} and a["m_c_7"] == {"k": 1, "n": 1}
    stop_at = lambda sec: [("mcp-11-1.jsonl", ev(sec, "tool.call", 11, tool="stop", ms=1, ok=True))]  # noqa: E731
    b = analyse(mk(tmp_path / "b", base + stop_at(10.0), [40]))  # 24.9 s before the signal: explained
    assert b["signals"][0]["explained"] is True and b["m_c_7"] == {"k": 0, "n": 1}
    c = analyse(mk(tmp_path / "c", base + stop_at(1.0), [40]))  # 33.9 s before: not explained
    assert c["signals"][0]["explained"] is False


def test_a_zero_denominator_renders_n_a_and_never_a_pass(tmp_path):
    import scheduler_survival as ss
    assert ss.rate({"k": 0, "n": 0}) == "n/a (0 of 0)"
    assert ss.rate({"k": 3, "n": 20}) == "3 of 20"
    a = analyse(mk(tmp_path, sched(21, 1.0, exit_at=10.0), [20]))
    text = "\n".join(ss.render(a, "lbl"))
    assert "(turn end, scheduler) pairs with the scheduler running: 0 -> n/a (0 of 0) for survival" in text


def test_the_boundary_m_c_8_counts_turns_whose_sleep_ended_at_least_20_s_after_the_chat(tmp_path):
    tt = ("turn 1: 10:00:00 - 10:00:30  x  utc 2026-11-01T10:00:00Z - 2026-11-01T10:00:30Z  exit 0  sleep 20 ended utc 2026-11-01T10:00:50Z\n"
          "turn 2: 10:01:00 - 10:01:30  x  utc 2026-11-01T10:01:00Z - 2026-11-01T10:01:30Z  exit 0  sleep 20 ended utc 2026-11-01T10:01:49Z\n"
          "turn 3: 10:02:00 - 10:02:30  x  utc 2026-11-01T10:02:00Z - 2026-11-01T10:02:30Z  exit 0\n")
    d = mk(tmp_path, sched(21, 1.0, exit_at=10.0), [20], turn_times=tt)
    (d / "harness-failures").mkdir()
    (d / "harness-failures" / "boundary-turn-02.txt").write_text("x")
    a = analyse(d)
    assert a["m_c_8"]["k"] == 1 and a["m_c_8"]["n"] == 3
    assert [t["ok"] for t in a["m_c_8"]["turns"]] == [True, False, False]
    assert a["m_c_8"]["boundary_failure_files"] == ["boundary-turn-02.txt"]
    assert a["sleep_entries"] == 2


def test_the_header_states_the_interval_rule_not_the_last_start_before_rule():
    src = SCRIPT.read_text()
    assert "interval" in src and "E7 s1" not in src and "E7 s2" not in src
    assert "the last `start` tool.call before its scheduler.start" not in src  # Correction 9: E7's header worded the starter rule wrongly


def test_cli_writes_the_text_and_the_json_with_source_files_and_script_md5(tmp_path):
    d = mk(tmp_path, sched(21, 1.0, exit_at=10.0), [20])
    out = tmp_path / "out"
    r = run(d, "--out", out)
    assert r.returncode == 0, r.stderr
    j = json.loads((out / "scheduler_survival.json").read_text())
    assert j["script"]["name"] == "scheduler_survival.py" and re.fullmatch(r"[0-9a-f]{32}", j["script"]["md5"])
    assert any(f.endswith("session-turn-times-utc.txt") for f in j["source_files"])
    assert (out / "scheduler-survival.txt").read_text().startswith("# s scheduler survival")


# ------------------------------------------------------------------ E7: the published numbers
def e7_analysis(stream):
    import scheduler_survival as ss
    return ss.analyse(E7EV / stream)


@e7
@pytest.mark.parametrize("stream,total,assistant,script", [("s1", 9, 8, 1), ("s2", 6, 5, 1), ("s3", 8, 7, 1)])
def test_e7_scheduler_counts(stream, total, assistant, script):
    a = e7_analysis(stream)
    c = a["counts"]
    assert (c["schedulers"], c["assistant_started"], c["script_started"]) == (total, assistant, script)
    assert a["m_c_1"] == {"k": 0, "n": assistant}
    assert a["m_c_2_pairs"] == {"k": 0, "n": 0}
    assert a["m_c_4"] == {"k": total, "n": total}
    assert c["reasons"] == ["finished: no open tasks"]
    assert c["run_orphan"] == 0 and a["signals"] == [] and c["run_end_killed"] == 0
    assert a["m_c_8"]["k"] == a["m_c_8"]["n"]


def segment(lines, first_prefix, last_prefix):
    i = next(n for n, l in enumerate(lines) if l.startswith(first_prefix))
    j = next(n for n, l in enumerate(lines) if n > i and l.startswith(last_prefix))
    return lines[i:j]


@e7
@pytest.mark.parametrize("stream", ["s1", "s2", "s3"])
def test_e7_facts_equal_the_committed_extracts_facts_and_only_the_header_differs(stream):
    import scheduler_survival as ss
    mine = ss.render(ss.analyse(E7EV / stream), stream)
    theirs = (E7EV / stream / "scheduler-survival.txt").read_text().splitlines()
    # the interval starter rule gives the same starter as the committed extract for every scheduler (E7 STUDY Interpretation 18)
    assert segment(mine, "scheduler pid", "Per-turn ps records") == segment(theirs, "scheduler pid", "Per-turn ps records")
    assert segment(mine, "# D-SIGNAL", "# Schedulers alive") == segment(theirs, "# D-SIGNAL", "# Schedulers alive")
    # the header: E7's states the starter rule wrongly and says "E7 s1" in every stream (Correction 9); ours states the interval rule
    assert mine[0] == f"# {stream} scheduler survival (D-SURVIVE and D-SIGNAL; facts only, from events/, session-turn-times-utc.txt, injection-log.txt)"
    assert "interval" in mine[1]
    assert theirs[0].startswith("# E7 s1" if stream == "s1" else "# E7 s")
