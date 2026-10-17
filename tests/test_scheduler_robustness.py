"""Robustness of the scheduler, health and review code paths (QA_REPORT.md, workstream F2)."""

import os
import pwd
import time
from datetime import timedelta
from pathlib import Path

from orgmcp import scheduler as sched_mod
from orgmcp.core import ROOT, OrgError, utcnow
from orgmcp.scheduler import Scheduler, ensure_kiro_profile


def real_agent_profiles() -> dict[str, int]:
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)  # the account's home, whatever $HOME says
    return {p.name: p.stat().st_mtime_ns for p in (home / ".kiro" / "agents").glob("orgmcp*.json")}


def run_to_idle(sched, limit=5.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.01)


# ------------------------------------------------------------- test isolation


def test_default_kiro_runner_in_tests_writes_nothing_under_the_real_home(org, isolated_kiro):
    before = real_agent_profiles()
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, echo=lambda _: None)  # the default runner: kiro_runner("kiro-cli")
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    assert (isolated_kiro / ".kiro" / "agents" / "orgmcp.json").is_file()  # the profile went to the sandbox
    assert "--agent orgmcp" in (isolated_kiro / "kiro-stub.log").read_text()  # and the stub, not kiro, ran
    assert real_agent_profiles() == before


def test_ensure_kiro_profile_resolves_the_directory_at_call_time(isolated_kiro, tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setattr(sched_mod, "KIRO_AGENTS_DIR", elsewhere)
    ensure_kiro_profile(["read"])
    assert (elsewhere / "orgmcp-read.json").is_file()
    assert not (isolated_kiro / ".kiro" / "agents" / "orgmcp-read.json").exists()


def test_ensure_kiro_profile_is_atomic_and_idempotent(tmp_path):
    d = tmp_path / "agents"
    ensure_kiro_profile([], d)
    path = d / "orgmcp.json"
    path.write_text("{ not json")  # a corrupt profile is repaired, not fatal
    ensure_kiro_profile([], d)
    assert path.read_text().startswith("{") and '"orgmcp"' in path.read_text()
    mtime = path.stat().st_mtime_ns
    ensure_kiro_profile([], d)
    assert path.stat().st_mtime_ns == mtime  # unchanged profile is not rewritten
    assert [p.name for p in d.iterdir()] == ["orgmcp.json"]  # no temp files left behind


# ------------------------------------------------------------ QA-5: fault isolation

import json  # noqa: E402

import pytest  # noqa: E402

from orgmcp.core import join_frontmatter, split_frontmatter  # noqa: E402
from orgmcp.health import agent_health, org_health, thresholds  # noqa: E402


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def write_ledger(org, name, text):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / f"{name}.json").write_text(text)


@pytest.mark.parametrize("name", ["nudges", "reviews", "failures"])
@pytest.mark.parametrize("junk", ["[]", "42", '"x"', "null", "{ broken", '{"a": []}', '{"a": {"step": "x"}}'])
def test_malformed_ledgers_never_kill_tick(org, name, junk):
    configure(org, review_every_seconds=0)
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    write_ledger(org, name, junk)
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    for _ in range(3):
        sched.tick()
        time.sleep(0.05)
    sched._reap()


def test_malformed_reviews_ledger_restarts_the_review_clock(org):
    write_ledger(org, "reviews", '{"at": 5, "runs": "x", "notified": [1]}')
    sched = Scheduler(org, echo=lambda _: None)
    sched.tick()
    assert json.loads((org.root / ".runtime" / "reviews.json").read_text())["at"]  # a real timestamp again


def test_a_crashing_phase_is_logged_once_and_the_loop_continues(org, monkeypatch):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    messages = []
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=messages.append)

    def boom():
        raise RuntimeError("kaput")

    monkeypatch.setattr(sched, "_check_stalls", boom)
    monkeypatch.setattr(sched, "_check_review", boom)
    sched.tick()
    sched.tick()
    assert "ceo" in sched.runs or org.runs_used("ceo") == 1  # launching still happened
    assert len([m for m in messages if "kaput" in m]) == 2  # once per phase, not once per tick
    sched.release()


@pytest.mark.parametrize("bad", ["1h", None, [], {}, True, float("nan"), "nan", float("inf")])
def test_bad_health_thresholds_fall_back_to_defaults(org, bad):
    configure(org, health={"idle_after_seconds": bad, "max_runs_per_task": bad, "min_runs_for_waste": 7})
    limits = thresholds(org)
    assert limits["idle_after_seconds"] == 86400 and limits["max_runs_per_task"] == 5
    assert limits["min_runs_for_waste"] == 7
    org_health(org)  # no TypeError
    agent_health(org, "ceo")


def test_numeric_string_thresholds_are_accepted(org):
    configure(org, health={"idle_after_seconds": "120", "max_problem_ratio": "0.25"})
    assert thresholds(org)["idle_after_seconds"] == 120 and thresholds(org)["max_problem_ratio"] == 0.25


def test_bad_scheduler_settings_fall_back_to_defaults(org):
    configure(org, run_timeout="soon", max_parallel=None, stall_after="10m", max_failures=[])
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    run_to_idle(sched)
    assert org.runs_used("ceo") == 1


# ------------------------------------------------- QA-3: retire during a run


def test_end_run_is_a_noop_for_a_vanished_agent(org):
    org.retire(ROOT, "ceo", "gone")
    org.end_run("ceo", ok=False)
    org.end_run("ceo/eng", ok=True)
    assert not (org.root / "ceo").exists()


def test_failed_run_of_a_retired_agent_leaves_no_trace(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    messages = []
    sched = Scheduler(org, lambda o, a, p: (["sh", "-c", "exit 3"], o.dir(a), dict(os.environ)), echo=messages.append)
    sched.acquire()
    try:
        sched.tick()
        sched.runs["ceo"].proc.wait()
        org.retire(ROOT, "ceo", "no longer needed")
        sched._reap()
    finally:
        sched.release()
    assert not (org.root / "ceo").exists() and sched.runs == {}
    assert org.ledger("failures") == {} and org.paused("ceo") is None
    assert not [m for m in org.messages(ROOT, "inbox") if "keeps failing" in m.title]
    retired_logs = list((org.root / ".retired").glob("ceo-*/runs/*.log"))
    assert retired_logs and "# exit 3" in retired_logs[0].read_text()  # the log handle was closed and flushed


# ------------------------------------------------------- QA-4: long prompts


def test_prompt_is_delivered_on_stdin_not_in_argv(org, tmp_path):
    out = tmp_path / "stdin.txt"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    argv = ["sh", "-c", f"cat > {out}"]
    sched = Scheduler(org, lambda o, a, p: (argv, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    text = out.read_text()
    assert text.startswith("# orgmcp run: you are `ceo`") and "### task " in text


def test_kiro_command_has_no_prompt_argument(org):
    cmd, _, _ = sched_mod.kiro_runner()(org, "ceo", "THE PROMPT")
    assert "THE PROMPT" not in cmd


def test_oversized_message_from_an_agent_is_refused_with_advice(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    cap = org.config["max_message_chars"]
    assert cap == 20000
    org.send("ceo", "root", "x" * cap)  # exactly at the cap is fine
    with pytest.raises(OrgError, match="write the detail to a file"):
        org.send("ceo", "root", "x" * (cap + 1))
    task = org.delegate("ceo", "ceo/eng", "t", "g", "a", budget=2)
    with pytest.raises(OrgError, match="max_message_chars"):
        org.report("ceo/eng", task.id, "done", "y" * (cap + 1))
    with pytest.raises(OrgError, match="max_message_chars"):
        org.delegate("ceo", "ceo/eng", "t2", "g" * (cap + 1), "a", budget=1)


def test_the_cap_is_configurable_and_a_bad_value_means_the_default(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    configure(org, max_message_chars=50)
    with pytest.raises(OrgError):
        org.send("ceo", "root", "x" * 51)
    configure(org, max_message_chars="lots")
    org.send("ceo", "root", "x" * 5000)


def test_a_huge_message_in_an_inbox_is_cut_in_the_prompt_with_the_path_to_read_it(org):
    org.send(ROOT, "ceo", "BEGIN " + "x" * 3_000_000 + " END")  # root (the human) is not capped
    batch = org.messages("ceo", "inbox")
    prompt = org.run_prompt("ceo", batch)
    assert len(prompt) < 40_000 and "BEGIN" in prompt and "END" not in prompt
    assert f'read(path="ceo/inbox/{batch[0].id}.md")' in prompt
    org.begin_run("ceo")  # the pointer stays right while the message is being handled
    assert f"ceo/inflight/{batch[0].id}.md" in org.run_prompt("ceo", org.messages("ceo", "inflight"))
    assert "cut" not in batch[0].render(limit=0) and batch[0].render(limit=0).endswith(" END\n")


def test_short_messages_render_unchanged(org):
    msg = org.send(ROOT, "ceo", "hello")
    assert msg.render().endswith("\n\nhello\n") and "cut" not in msg.render()


# --------------------------------------------------- QA-7: monotonic run counter

from orgmcp.review import review_if_due, total_runs  # noqa: E402


def add_runs(org, addr, n, prefix="2026"):
    d = org.dir(addr) / "runs"
    start = len(list(d.glob("*.log")))
    for i in range(n):
        (d / f"{prefix}0101T{start + i:012d}.log").touch()


def test_total_runs_never_goes_down_when_agents_are_retired(org):
    org.hire("ceo", "sub", "S", "s")  # a sub-team: ceo/sub
    add_runs(org, "ceo", 2)
    add_runs(org, "ceo/eng", 3)
    add_runs(org, "ceo/sub", 4)
    assert total_runs(org) == 9
    org.retire("ceo", "eng", "done")
    assert total_runs(org) == 9
    org.retire(ROOT, "ceo", "restructure")  # takes the whole team (ceo, ceo/sub) along
    assert total_runs(org) == 9
    # unrelated files inside a retired directory are not run logs
    for d in (org.root / ".retired").glob("ceo-*"):
        (d / "work" / "runs").mkdir(parents=True, exist_ok=True)
        (d / "work" / "runs" / "x.log").touch()
        (d / "inbox" / "y.log").touch()
    assert total_runs(org) == 9


def test_review_baseline_is_rebased_if_the_counter_ever_shrinks(org):
    configure(org, review_every_runs=2, review_every_seconds=10**9)
    add_runs(org, "ceo", 5)
    review_if_due(org, utcnow())  # starts the clock at 5
    for f in (org.dir("ceo") / "runs").glob("*.log"):
        f.unlink()
    assert review_if_due(org, utcnow()) is None  # no spurious review, and no permanent stall:
    add_runs(org, "ceo", 2, prefix="2027")
    assert review_if_due(org, utcnow()) is not None


# ------------------------------------------------ QA-8: reviews and the reserve


def test_manager_with_spare_budget_beyond_its_reserve_still_gets_the_note(org):
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=4)
    org.delegate("ceo", "ceo/eng", "work", "g", "a", budget=1)  # budget 2 left, one outstanding
    configure(org, health={"idle_after_seconds": -1})
    from orgmcp.review import review

    result = review(org, utcnow() + timedelta(hours=1))
    assert [n.to for n in result.notes if n.to == "ceo"] == ["ceo"] and "ceo" not in result.skipped


def test_skipped_manager_is_listed_in_roots_summary_and_told_later(org):
    from orgmcp.review import review

    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.delegate("ceo", "ceo/eng", "work", "g", "a", budget=2)
    configure(org, health={"idle_after_seconds": -1})
    later = utcnow() + timedelta(hours=1)
    result = review(org, later)
    assert "reserved for 1 outstanding" in result.skipped["ceo"]
    root_note = next(n for n in result.notes if n.to == ROOT)
    assert "Managers not notified: `ceo` (budget 1 is reserved for 1 outstanding delegation(s))" in root_note.body
    org.send(ROOT, "ceo", "more budget", budget=3)  # the reserve is covered again
    again = review(org, later + timedelta(hours=1))
    assert [n.to for n in again.notes if n.to == "ceo"] == ["ceo"]  # its pending news is delivered now


# ------------------------------------------------ QA-14: health vs failed runs

from orgmcp.health import agent_health  # noqa: E402,F811


def write_run(org, addr, i, text):
    (org.dir(addr) / "runs" / f"20260101T{i:012d}.log").write_text(text)


HEADER = "# run of ceo, 1 message(s)\n# senders: {senders}\n# cwd: /x\n# cmd: kiro-cli chat <prompt on stdin>\n"
PROMPT = "# ---- prompt ----\nplease do things\n# ---- output ----\n"


def test_failed_runs_do_not_make_an_agent_wasteful(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i, tail in enumerate(["\n# exit 1 after 2s\n", "\n# failed to start: boom\n", "\n# killed after 5s timeout\n\n# exit -9 after 5s\n",
                              "\n# interrupted by scheduler shutdown\n", "\n# exit 2 after 1s\n"]):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + tail)
    h = agent_health(org, "ceo", utcnow())
    assert "wasteful" not in h.flags and h.empty_runs == 0 and h.failed_runs == 5 and h.runs_used == 5


def test_successful_empty_runs_are_still_wasteful(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i in range(5):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + "\n# exit 0 after 2s\n")
    h = agent_health(org, "ceo", utcnow())
    assert "wasteful" in h.flags and h.empty_runs == 5 and "5 of 5" in h.flags["wasteful"]


def test_runs_that_only_handled_runtime_notes_are_not_empty(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i in range(6):
        write_run(org, "ceo", i, HEADER.format(senders="runtime") + PROMPT + "\n# exit 0 after 2s\n")
    write_run(org, "ceo", 6, HEADER.format(senders="root, runtime") + PROMPT + "\n# exit 0 after 2s\n")  # mixed: counts
    h = agent_health(org, "ceo", utcnow())
    assert h.runtime_runs == 6 and h.empty_runs == 1 and "wasteful" not in h.flags  # 1 judged run < min_runs_for_waste


def test_failures_mixed_with_real_empty_runs_judge_only_the_real_ones(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i in range(10):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + "\n# exit 1 after 1s\n")
    for i in range(10, 14):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + "\n# exit 0 after 1s\n")
    h = agent_health(org, "ceo", utcnow())
    assert h.empty_runs == 4 and "4 of 4" in h.flags["wasteful"]


def test_the_scheduler_records_senders_and_exit_in_the_log(org):
    org.notify("ceo", "fyi", "a runtime note")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, lambda o, a, p: (["sh", "-c", "exit 3"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    log = next((org.dir("ceo") / "runs").glob("*.log")).read_text()
    assert "# senders: root, runtime\n" in log and "# exit 3 after" in log
    assert agent_health(org, "ceo", utcnow()).failed_runs >= 1


def test_runtime_only_batch_is_recorded_as_such(org):
    org.send(ROOT, "ceo", "budget", budget=5)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.notify("ceo", "fyi", "a runtime note")
    sched = Scheduler(org, lambda o, a, p: (["true"], o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    assert agent_health(org, "ceo", utcnow()).runtime_runs == 1


# --------------------------------------------------------- QA-13: parse caching

from orgmcp import core  # noqa: E402


def test_message_load_is_cached_by_path_mtime_and_size(org, monkeypatch):
    msg = org.send(ROOT, "ceo", "hello")
    path = org.dir("ceo") / "inbox" / f"{msg.id}.md"
    parses = []
    real = core.split_frontmatter
    monkeypatch.setattr(core, "split_frontmatter", lambda t: (parses.append(1), real(t))[1])
    first = core.Message.load(path)
    second = core.Message.load(path)
    assert len(parses) == 1 and first == second and first is not second and second.path == path
    first.body = "mutated"  # the cache hands out fresh objects
    assert core.Message.load(path).body == "hello"
    path.write_text(path.read_text().replace("hello", "HELLO!"))  # same path, new content: reparsed
    assert core.Message.load(path).body == "HELLO!" and len(parses) == 2


def test_cached_load_equals_uncached_parse(org):
    msg = org.delegate(ROOT, "ceo", "Title: with colon", "goal\nline2", "acc", budget=3)
    path = org.dir("ceo") / "inbox" / f"{msg.id}.md"
    core._PARSED.clear()
    cold = core.Message.load(path)
    assert core.Message.load(path) == cold and cold.title == "Title: with colon" and cold.budget == 3
    meta, body = core.split_frontmatter(path.read_text(encoding="utf-8"))
    assert cold.body == body.strip() and meta["id"] == cold.id


def test_crlf_files_parse_like_read_text(tmp_path):
    p = tmp_path / "20260101T000000000000-root-aaaa.md"
    p.write_bytes(b"---\r\nfrom: root\r\nto: ceo\r\ntype: note\r\n---\r\nline1\r\nline2\r\n")
    assert core.Message.load(p).body == "line1\nline2" and core.Message.load(p).sender == "root"


def test_cache_is_bounded(org, monkeypatch):
    monkeypatch.setattr(core, "_PARSED_MAX", 5)
    core._PARSED.clear()
    for i in range(12):
        org.send(ROOT, "ceo", f"n{i}")
    org.messages("ceo", "inbox")
    assert len(core._PARSED) == 5


def test_yaml_uses_the_c_loader_when_present():
    import yaml

    assert core._YAML_LOADER is getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    assert core.split_frontmatter("---\na: 1\nb: [x, y]\n---\nbody\n") == ({"a": 1, "b": ["x", "y"]}, "body\n")


def test_stall_view_reparses_only_when_the_mailbox_files_change(org, monkeypatch):
    org.send(ROOT, "ceo", "budget", budget=10)
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    sched = Scheduler(org, echo=lambda _: None)
    assert [t.id for t in sched._task_view("ceo", "open_tasks")] == [task.id]
    loads = []
    real = core.Message.load.__func__
    monkeypatch.setattr(core.Message, "load", classmethod(lambda cls, p: (loads.append(p), real(cls, p))[1]))
    for _ in range(3):
        sched._task_view("ceo", "open_tasks")
    assert loads == []  # unchanged mailbox: nothing is parsed
    org.begin_run("ceo")  # inbox -> inflight is the same set of messages
    loads.clear()  # (begin_run itself parses the batch)
    assert [t.id for t in sched._task_view("ceo", "open_tasks")] == [task.id] and loads == []
    org.end_run("ceo", ok=True)
    org.report("ceo", task.id, "done", "ok")  # a new sent message: recomputed, and the task is closed
    assert sched._task_view("ceo", "open_tasks") == [] and loads


# ------------------------------------------------- QA-16: process groups


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_for_pid(pidfile, limit=5.0):
    deadline = time.time() + limit
    while time.time() < deadline:
        if pidfile.exists() and pidfile.read_text().strip():
            return int(pidfile.read_text())
        time.sleep(0.02)
    raise AssertionError("child never started")


def spawn_tree(org, tmp_path, marker):
    pidfile = tmp_path / f"{marker}.pid"
    cmd = ["sh", "-c", f"sleep {marker} & echo $! > {pidfile}; wait"]
    sched = Scheduler(org, lambda o, a, p: (cmd, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    sched.tick()
    return sched, wait_for_pid(pidfile)


def test_shutdown_kills_the_whole_process_group(org, tmp_path):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched, child = spawn_tree(org, tmp_path, "46")
    try:
        sched.release()
        time.sleep(0.2)
        assert not alive(child), "tool subprocess outlived the scheduler"
    finally:
        if alive(child):
            os.kill(child, 9)


def test_retiring_an_agent_mid_run_kills_its_process_group(org, tmp_path):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched, child = spawn_tree(org, tmp_path, "45")
    try:
        org.retire(ROOT, "ceo", "gone")
        sched._reap()
        time.sleep(0.2)
        assert sched.runs == {} and not alive(child) and not (org.root / "ceo").exists()
    finally:
        sched.release()
        if alive(child):
            os.kill(child, 9)


def test_runs_are_started_in_their_own_session(org, tmp_path):
    out = tmp_path / "ids.txt"
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    cmd = ["sh", "-c", f"ps -o pid=,pgid= -p $$ > {out}"]
    sched = Scheduler(org, lambda o, a, p: (cmd, o.dir(a), dict(os.environ)), echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    pid, pgid = map(int, out.read_text().split())
    assert pid == pgid != os.getpgid(0)


def test_signalling_a_finished_run_is_harmless():
    import subprocess

    proc = subprocess.Popen(["true"], start_new_session=True)
    proc.wait()
    sched_mod._signal_group(proc, 9)
