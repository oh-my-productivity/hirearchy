"""Tests of extract_mechanical.py (the generalized E7 extract) and injection_files.py.

Synthetic streams live in pytest's tmp_path. The E7 integration tests read E7's committed evidence read-only (E7EV) and write only to
tmp_path. extract_mechanical.py imports the product's client-question parser read-only (sys.dont_write_bytecode set first); that import is
the one product import the build allows (see the script's docstring)."""
import hashlib
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
SCRIPT = HARNESS / "extract_mechanical.py"
INJ = HARNESS / "injection_files.py"
PY = sys.executable
HAVE_E7 = (E7EV / "s1" / "assistant-session-messages.jsonl").exists()
e7 = pytest.mark.skipif(not HAVE_E7, reason="E7 evidence not available")


def run(script, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([PY, "-B", str(script), *map(str, args)], capture_output=True, text=True, env=env)


# ------------------------------------------------------------------ synthetic stream
def msg(path: Path, hdr: dict, body: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    head = "\n".join(f"{k}: {v}" for k, v in hdr.items())
    path.write_text(f"---\n{head}\n---\n{body}")


def make_stream(tmp_path: Path, owner="boss", service="daily-brief", writer="scribe", seat="inspector", sandbox="/tmp/hirearchy-g0-m0-s1-1793000000"):
    d = tmp_path / "stream"
    d.mkdir()
    (d / "sandbox-path.txt").write_text(sandbox + "\n")
    ts = "2026-11-01T10:00:00.000Z"
    lines = [
        {"timestamp": ts, "payload": {"type": "user", "content": "hi"}},
        {"timestamp": ts, "payload": {"type": "turn_start"}},
        {"timestamp": "2026-11-01T10:00:05.000Z", "payload": {"type": "turn_end"}},
    ]
    (d / "assistant-session-messages.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    (d / "turn-times.txt").write_text("turn 1: 10:00:00 - 10:00:05  1-0=5s  utc 2026-11-01T10:00:00Z - 2026-11-01T10:00:05Z  exit 0  sleep 20 ended utc 2026-11-01T10:00:25Z\n")
    (d / "session-turn-times-utc.txt").write_text("turn 1: user_ts x turn_start 2026-11-01T10:00:00.000Z turn_end 2026-11-01T10:00:05.000Z stop end_turn status success elapsed_ms 5000 credits 1.0000\n")
    (d / "lena-lines.txt").write_text("turn 1 | rule H1 | x\n")
    (d / "turn-01.prompt.txt").write_text("Hi\n")
    (d / "events" / "2026-11-01").mkdir(parents=True)
    # root's task to the owner for the service
    msg(d / "msgs" / "sent" / "20261101T100001000000-root-aaaa.md",
        {"id": "20261101T100001000000-root-aaaa", "from": "root", "to": owner, "type": "task", "created": "'2026-11-01T10:00:01+00:00'", "service": service})
    # run logs for owner, writer and the final-check seat
    for agent, stamp in ((owner, "20261101T100002000000"), (f"{owner}-{writer}", "20261101T100003000000"), (f"{owner}-{seat}", "20261101T100004000000")):
        (d / "run-logs" / agent).mkdir(parents=True, exist_ok=True)
        (d / "run-logs" / agent / f"{stamp}.log").write_text(
            f"# run of {agent}\n# cwd: /state/kiro-cwd/orgid/{agent}-1\n# cmd: x --agent prof --model claude-sonnet-5.5 --effort high\n# ---- prompt ----\nPROMPT\n# ---- output ----\nok\n# exit 0 after 5s\n")
    (d / "org-files").mkdir()
    (d / "org-files" / f"{owner}-{seat}-AGENT.md").write_text("You review and check the work.\n")
    return d


# ------------------------------------------------------------------ detection
def test_the_script_names_no_study_service_or_seat():
    src = SCRIPT.read_text()
    for banned in ("weekly-memo", "weekly-meeting-memo", "checker", "hirearchy-e7-s", "studies/E7"):
        assert banned not in src, banned


def test_detects_owner_service_and_the_final_check_seat(tmp_path):
    import extract_mechanical as em
    d = make_stream(tmp_path)
    info = em.detect(d)
    assert info["owner"] == "boss"
    assert info["service"] == "daily-brief"
    assert info["seat_dir"] == "boss-inspector"
    assert info["seat_short"] == "inspector"


def test_seat_falls_back_to_the_agent_whose_charter_says_review(tmp_path):
    import extract_mechanical as em
    d = make_stream(tmp_path, seat="zed", writer="amy")
    info = em.detect(d)
    assert info["seat_dir"] == "boss-zed"  # its AGENT.md says review/check


def test_seat_falls_back_to_the_agent_whose_results_carry_criteria_met(tmp_path):
    import extract_mechanical as em
    d = make_stream(tmp_path, seat="zed", writer="amy")
    (d / "org-files" / "boss-zed-AGENT.md").write_text("You do things.\n")
    msg(d / "msgs" / "boss-zed-sent" / "x.md", {"id": "x", "from": "boss/zed", "to": "boss", "type": "result"}, "criteria met: 7 of 7\n")
    assert em.detect(d)["seat_dir"] == "boss-zed"


# ------------------------------------------------------------------ pure helpers
def test_read_msg_parses_quoted_headers_and_body(tmp_path):
    import extract_mechanical as em
    p = tmp_path / "m.md"
    msg(p, {"id": "a-1", "created": "'2026-11-01T10:00:01+00:00'", "to": "root"}, "## Summary\nhello\n")
    hdr, body, raw = em.read_msg(p)
    assert hdr["id"] == "a-1" and hdr["created"] == "2026-11-01T10:00:01+00:00" and hdr["to"] == "root"
    assert body.startswith("## Summary")


def test_the_shell_flags_follow_the_stream_sandbox_not_a_study_name():
    import extract_mechanical as em
    S = "/tmp/hirearchy-g0-m1-s2-1793000001"
    # a command that only names the stream's own sandbox does not "mention hirearchy"
    assert em.shell_flags(f"cp {S}/org/lead/work/memo-2026-10-05.md {S}/deliverables/memo-2026-10-05.md", S)[0] == [
        "writes into the deliverable folder", "touches S/org"]
    flags = em.shell_flags("uv run hirearchy --root x status", S)[0]
    assert "mentions hirearchy" in flags and "runs hirearchy CLI" in flags
    # the g0 profile and sandbox names are not "hirearchy" mentions, as e7's names were not
    assert "mentions hirearchy" not in em.shell_flags("ls /tmp/hirearchy-g0-m0-s1-1793000000/notes", S)[0]


def test_source_files_of_a_copy_command_are_found_for_any_sandbox_name():
    import extract_mechanical as em
    cmd = "cp /private/tmp/hirearchy-g0-m0-s3-1793000009/org/lead/writer/work/memo-2026-10-12.md /tmp/x/deliverables/memo-2026-10-12.md"
    assert em.source_paths(cmd) == ["/private/tmp/hirearchy-g0-m0-s3-1793000009/org/lead/writer/work/memo-2026-10-12.md"]
    assert em.source_paths("cp org/a/b.md deliverables/") == ["org/a/b.md"]


# ------------------------------------------------------------------ no-sandbox mode on a synthetic stream
def test_no_sandbox_mode_writes_the_extract_files_into_out_and_leaves_the_stream_dir_alone(tmp_path):
    d = make_stream(tmp_path)
    (d / "memos").mkdir()
    (d / "memos" / "memo-2026-10-05.md").write_text("# Memo\n")
    msg(d / "msgs" / "read" / "20261101T100100000000-boss-bbbb.md",
        {"id": "20261101T100100000000-boss-bbbb", "from": "boss", "to": "root", "type": "result", "created": "'2026-11-01T10:01:00+00:00'",
         "reply_to": "20261101T100001000000-root-aaaa", "status": "blocked"},
        "## Summary\nQuestions for the client:\n- Sam's row (C6): which date?\n- a remark with no id\n\n## Artifacts\n- boss/scribe/work/memo-2026-10-05.md\n")
    before = sorted(str(p.relative_to(d)) for p in d.rglob("*"))
    out = tmp_path / "out"
    r = run(SCRIPT, d, "-", "--out", out)
    assert r.returncode == 0, r.stderr
    assert sorted(str(p.relative_to(d)) for p in d.rglob("*")) == before  # read-only on the stream dir
    for name in ("client-questions.txt", "contract-loop.txt", "deliverables-log.txt", "shell-writes.txt", "revise-playbook-attempts.txt",
                 "cost.txt", "lead-prompt-sizes.txt", "run-session-map.txt"):
        assert (out / name).exists(), name
    assert (out / "reflect-sections").is_dir() and (out / "regression-list").is_dir()
    cq = (out / "client-questions.txt").read_text()
    assert "parsed items (2): [\"Sam's row (C6): which date?\", 'a remark with no id']" in cq
    sizes = (out / "lead-prompt-sizes.txt").read_text()
    assert "@20261101T100002000000" in sizes and "bytes=" in sizes
    assert "@20261101T100003000000" not in sizes and "@20261101T100004000000" not in sizes  # only the owner's runs
    # the deliverable listing comes from memos/ when there is no sandbox
    dl = (out / "deliverables-log.txt").read_text()
    assert "memo-2026-10-05.md size 7" in dl


def test_regression_list_of_the_final_check_seat_uses_the_seat_name(tmp_path):
    d = make_stream(tmp_path)
    (d / "memos").mkdir()
    msg(d / "msgs" / "boss-inspector-read" / "t1.md", {"id": "t1", "from": "boss", "to": "boss/inspector", "type": "task"},
        "## Goal\nCheck.\n\nRegression list\n- R1: x\n")
    out = tmp_path / "out"
    assert run(SCRIPT, d, "-", "--out", out).returncode == 0
    assert (out / "regression-list" / "inspector-task-t1.md").exists()


def test_the_product_parser_import_does_not_write_bytecode_into_the_product(tmp_path):
    d = make_stream(tmp_path)
    (d / "memos").mkdir()
    out = tmp_path / "out"
    src = Path("/Volumes/workspace/hirearchy/src/hirearchy")
    snap = lambda: {str(p): p.stat().st_mtime_ns for p in src.rglob("*.pyc")} | {str(p): 0 for p in src.rglob("__pycache__")}  # noqa: E731
    before = snap()
    r = subprocess.run([PY, str(SCRIPT), str(d), "-", "--out", str(out)], capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"})
    assert r.returncode == 0, r.stderr
    assert snap() == before  # no new .pyc, no touched .pyc, no new __pycache__ under the product


# ------------------------------------------------------------------ E7 integration: the extracts equal E7's committed ones
FILES = ("client-questions.txt", "contract-loop.txt", "deliverables-log.txt", "shell-writes.txt", "revise-playbook-attempts.txt", "cost.txt",
         "lead-prompt-sizes.txt", "run-session-map.txt")


def tree_files(root: Path):
    return {str(p.relative_to(root)): p for p in sorted(root.rglob("*")) if p.is_file()}


@e7
@pytest.mark.parametrize("stream", ["s1", "s2", "s3"])
def test_e7_no_sandbox_mode_reproduces_e7s_committed_extracts(tmp_path, stream):
    out = tmp_path / "out"
    r = run(SCRIPT, E7EV / stream, "-", "--out", out)
    assert r.returncode == 0, r.stderr
    same = {"client-questions.txt", "contract-loop.txt", "shell-writes.txt", "lead-prompt-sizes.txt", "revise-playbook-attempts.txt", "cost.txt"}
    for name in sorted(same):
        assert (out / name).read_text() == (E7EV / stream / name).read_text(), name
    for sub in ("reflect-sections", "regression-list"):
        mine, theirs = tree_files(out / sub), tree_files(E7EV / stream / sub)
        assert sorted(mine) == sorted(theirs), sub
        for k in theirs:
            assert mine[k].read_text() == theirs[k].read_text(), (sub, k)


@e7
@pytest.mark.parametrize("stream", ["s1", "s2", "s3"])
def test_e7_no_sandbox_deliverables_log_differs_only_in_the_folder_listing_tail(tmp_path, stream):
    out = tmp_path / "out"
    assert run(SCRIPT, E7EV / stream, "-", "--out", out).returncode == 0
    mine = (out / "deliverables-log.txt").read_text()
    theirs = (E7EV / stream / "deliverables-log.txt").read_text()
    marker = "\nfinal ls -la:"
    assert mine.split(marker)[0] == theirs.split(marker)[0]
    assert "no sandbox" in mine.split(marker)[1]


@e7
@pytest.mark.parametrize("stream", ["s1", "s2", "s3"])
def test_e7_run_session_map_differs_only_in_the_copied_sessions_line(tmp_path, stream):
    out = tmp_path / "out"
    assert run(SCRIPT, E7EV / stream, "-", "--out", out).returncode == 0
    a = (out / "run-session-map.txt").read_text().splitlines()
    b = (E7EV / stream / "run-session-map.txt").read_text().splitlines()
    assert len(a) == len(b)
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    assert len(diff) == 1 and diff[0][1].startswith("org kiro sessions copied:") and diff[0][0].startswith("org kiro sessions read from the stream dir")


@e7
@pytest.mark.parametrize("stream", ["s1", "s2", "s3"])
def test_e7_with_the_sandbox_present_reproduces_every_extract_byte_for_byte(tmp_path, stream):
    sandbox = Path((E7EV / stream / "sandbox-path.txt").read_text().strip())
    if not (sandbox / "org" / ".git").exists():
        pytest.skip("E7's sandbox is gone")
    out = tmp_path / "out"
    r = run(SCRIPT, E7EV / stream, sandbox, "--out", out)
    assert r.returncode == 0, r.stderr
    for name in FILES:
        mine, theirs = (out / name).read_text(), (E7EV / stream / name).read_text()
        if name == "run-session-map.txt":
            # the org's kiro home (outside the sandbox) is gone: the sessions come from the stream dir copy, and only that line says so
            mine = mine.replace("org kiro sessions read from the stream dir copy:", "org kiro sessions copied:").replace(
                " (org-kiro-sessions/<hash>/<session id>/)", " (to org-kiro-sessions/<hash>/<session id>/)")
        assert mine == theirs, name
    for sub in ("reflect-sections", "regression-list"):
        mine, theirs = tree_files(out / sub), tree_files(E7EV / stream / sub)
        assert sorted(mine) == sorted(theirs)
        for k in theirs:
            assert mine[k].read_text() == theirs[k].read_text(), (sub, k)
    # with the sandbox the memos/versions are regenerated from the org's git: INDEX.txt equals E7's
    assert (out / "memos" / "versions" / "INDEX.txt").read_text() == (E7EV / stream / "memos" / "versions" / "INDEX.txt").read_text()


# ------------------------------------------------------------------ injection_files.py
def test_injection_files_reads_the_evidence_copy_and_writes_only_to_out(tmp_path):
    d = make_stream(tmp_path)
    (d / "injection").mkdir()
    (d / "injection" / "window.txt").write_text("2026-11-01T10:00:02 2026-11-01T10:00:09\n")
    note = "x" * 3
    msg(d / "msgs" / "sent" / "20261101T100002000000-root-iiii.md",
        {"id": "20261101T100002000000-root-iiii", "from": "root", "to": "boss", "type": "task", "title": "T", "created": "'2026-11-01T10:00:02+00:00'", "source": "relayed"},
        f"## Note from the requester\n{note}\n")
    ev = d / "events" / "2026-11-01" / "scheduler-1-1.jsonl"
    ev.write_text(json.dumps({"ts": "2026-11-01T10:00:03.000000+00:00", "kind": "run.start", "run": "boss@20261101T100002000000", "pid": 1}) + "\n"
                  + json.dumps({"ts": "2026-11-01T10:00:08.000000+00:00", "kind": "run.end", "run": "boss@20261101T100002000000", "pid": 1, "ok": True, "killed": False}) + "\n")
    before = sorted(str(p.relative_to(d)) for p in d.rglob("*"))
    out = tmp_path / "out"
    r = run(INJ, d, "-", "--injected", "20261101T100002000000-root-iiii", "--out", out)
    assert r.returncode == 0, r.stderr
    assert sorted(str(p.relative_to(d)) for p in d.rglob("*")) == before
    ti = (out / "text-identity.txt").read_text()
    assert "title as stored: 'T'" in ti and "match=False" in ti  # not E7's title: reported, never asserted
    wr = (out / "window-runs.txt").read_text()
    assert wr.startswith("# window runs (protocol 5.4)")
    assert "## run boss@20261101T100002000000 agent=boss" in wr
    assert "org-git: not available" in wr  # an owner run, no sandbox


def test_injection_files_needs_a_window(tmp_path):
    d = make_stream(tmp_path)
    r = run(INJ, d, "-", "--out", tmp_path / "o")
    assert r.returncode == 2 and "injection/window.txt" in r.stderr


def e7_sandbox(stream):
    sandbox = Path((E7EV / stream / "sandbox-path.txt").read_text().strip())
    return sandbox if (sandbox / "org" / ".git").exists() else None


@e7
@pytest.mark.parametrize("stream", ["s1", "s2", "s3"])
def test_e7_injection_files_reproduce_the_committed_files(tmp_path, stream):
    ex = tmp_path / "ex"
    assert run(SCRIPT, E7EV / stream, "-", "--out", ex).returncode == 0
    out = tmp_path / "inj"
    sandbox = e7_sandbox(stream)
    r = run(INJ, E7EV / stream, sandbox or "-", "--session-map", ex / "run-session-map.txt", "--out", out)
    assert r.returncode == 0, r.stderr
    assert (out / "text-identity.txt").read_text() == (E7EV / stream / "injection" / "text-identity.txt").read_text()
    mine = (out / "window-runs.txt").read_text()
    theirs = (E7EV / stream / "injection" / "window-runs.txt").read_text()
    if sandbox:
        assert mine == theirs
    else:  # the lead run's MEMORY.md patch is in the org git, which the stream dir does not hold: only the commit's log entry (org-git-log.txt) is shown
        keep = lambda t: [l for l in t.splitlines() if not l.startswith("  org-git") and not l.startswith("    ")]  # noqa: E731
        assert keep(mine) == keep(theirs)
        assert "from org-git-log.txt" in mine


@e7
@pytest.mark.parametrize("stream", ["s1", "s2", "s3"])
def test_e7_injection_files_without_the_sandbox_show_the_commit_entry_but_not_the_patch(tmp_path, stream):
    ex = tmp_path / "ex"
    assert run(SCRIPT, E7EV / stream, "-", "--out", ex).returncode == 0
    out = tmp_path / "inj"
    r = run(INJ, E7EV / stream, "-", "--session-map", ex / "run-session-map.txt", "--out", out)
    assert r.returncode == 0, r.stderr
    mine = (out / "window-runs.txt").read_text()
    theirs = (E7EV / stream / "injection" / "window-runs.txt").read_text()
    keep = lambda t: [l for l in t.splitlines() if not l.startswith("  org-git") and not l.startswith("    ")]  # noqa: E731
    assert keep(mine) == keep(theirs)
    assert "from org-git-log.txt" in mine and "diff --git" not in mine
