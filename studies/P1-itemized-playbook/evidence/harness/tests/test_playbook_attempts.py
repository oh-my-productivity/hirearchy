"""Tests of playbook_attempts.py (G0 harness, helper M): revise_playbook attempts, refusals, admissions, injection window."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))

import playbook_attempts as pa  # noqa: E402

P1 = ("refused: every line a revision adds or changes must rest on the evidence it cites, and 1 line(s) do not:\n"
      "- \"## Criteria added by confirmed amendments\"\nRule (c) admits only the cited confirmed criterion's own words.")


def ev(ts, kind="tool.call", **kw):
    d = {"v": 1, "ts": ts, "seq": 1, "proc": "mcp", "pid": 1, "kind": kind, "actor": "lead", "run": "lead@20261025T071720667277", "trace": None}
    d.update(kw)
    return json.dumps(d)


def tool(ts, name="revise_playbook", ok=True, error=None, error_type=None, run="lead@20261025T071720667277", actor="lead"):
    return ev(ts, tool=name, ok=ok, ms=5.0, error=error, error_type=error_type, run=run, actor=actor, args={"service": "weekly-meeting-memo"})


def make_stream(tmp_path, lines, window="2026-10-25T07:11:52 2026-10-25T07:14:42", name="s1"):
    s = tmp_path / name
    (s / "events" / "2026-10-25").mkdir(parents=True)
    (s / "events" / "2026-10-25" / "mcp-1-1.jsonl").write_text("\n".join(lines) + "\n")
    if window is not None:
        (s / "injection").mkdir()
        (s / "injection" / "window.txt").write_text(window + "\n")
    return s


def test_classify():
    assert pa.classify(True, None, None) == ("admitted", None)
    assert pa.classify(False, P1, "OrgError") == ("refused", "P1-REFUSED")
    assert pa.classify(False, "refused: the revision is empty", "OrgError") == ("refused", "other refusal")
    assert pa.classify(False, "unknown service 'x'", "OrgError") == ("error", "validation error")
    assert pa.classify(False, None, None) == ("error", "validation error")


def test_parse_window():
    a, b = pa.parse_window("2026-10-25T07:11:52 2026-10-25T07:14:42\n")
    assert a.isoformat() == "2026-10-25T07:11:52+00:00" and b.isoformat() == "2026-10-25T07:14:42+00:00"
    assert pa.parse_window("") is None and pa.parse_window("garbage") is None


def test_attempts_are_classified_and_counted(tmp_path):
    lines = [
        tool("2026-10-25T07:00:00+00:00", name="write", ok=True),  # another tool: ignored
        tool("2026-10-25T07:17:51.249968+00:00", ok=False, error=P1, error_type="OrgError"),
        tool("2026-10-25T07:17:58.508115+00:00", ok=True),
        ev("2026-10-25T07:17:58.507568+00:00", kind="service.revise", actor="lead", owner="lead", service="weekly-meeting-memo", version=2, by="lead", admitted="c"),
        tool("2026-10-25T07:20:00+00:00", ok=False, error="refused: the playbook is over its size", error_type="OrgError"),
        tool("2026-10-25T07:21:00+00:00", ok=False, error="unknown service", error_type="OrgError"),
        tool("2026-10-25T07:12:30+00:00", ok=False, error=P1, error_type="OrgError", run="lead@20261025T071200000000"),  # inside the window
        "not json at all",
    ]
    d = pa.analyse_stream(make_stream(tmp_path, lines))
    assert [a["time"] for a in d["attempts"]] == ["2026-10-25T07:12:30Z", "2026-10-25T07:17:51.249968Z", "2026-10-25T07:17:58.508115Z",
                                                 "2026-10-25T07:20:00Z", "2026-10-25T07:21:00Z"]
    assert [a["outcome"] for a in d["attempts"]] == ["refused", "refused", "admitted", "refused", "error"]
    assert [a["refusal_kind"] for a in d["attempts"]] == ["P1-REFUSED", "P1-REFUSED", None, "other refusal", "validation error"]
    assert d["counts"] == {"attempts": 5, "admitted": 1, "refused": 3, "p1_refused": 2, "other_refused": 1, "errors": 1, "in_window": 1}
    assert d["attempts"][0]["in_window"] is True and d["attempts"][1]["in_window"] is False
    assert d["attempts"][2]["admitted_version"] == 2 and d["attempts"][2]["admitted_letter"] == "c"
    assert d["attempts"][1]["error_first_line"].startswith("refused: every line a revision adds")
    assert d["owner_attempted"] is True
    assert d["window"] == {"start": "2026-10-25T07:11:52Z", "end": "2026-10-25T07:14:42Z"}
    assert d["bad_event_lines"] == 1
    assert d["script"]["name"] == "playbook_attempts.py" and d["source_files"] == ["events/2026-10-25/mcp-1-1.jsonl", "injection/window.txt"]


def test_no_attempt_no_window(tmp_path):
    d = pa.analyse_stream(make_stream(tmp_path, [tool("2026-10-25T07:00:00+00:00", name="write")], window=None))
    assert d["counts"] == {"attempts": 0, "admitted": 0, "refused": 0, "p1_refused": 0, "other_refused": 0, "errors": 0, "in_window": 0}
    assert d["owner_attempted"] is False and d["window"] is None and d["attempts"] == []


def test_without_a_window_file_nothing_is_in_a_window_and_it_is_said(tmp_path):
    d = pa.analyse_stream(make_stream(tmp_path, [tool("2026-10-25T07:12:30+00:00")], window=None))
    assert d["attempts"][0]["in_window"] is False and "no injection/window.txt" in d["notes"][0]


def test_the_admission_is_confirmed_by_a_service_revise_event_of_the_same_run(tmp_path):
    lines = [tool("2026-10-25T07:17:58.508115+00:00", ok=True),
             ev("2026-10-25T07:30:00+00:00", kind="service.revise", owner="lead", service="x", version=3, by="lead", admitted="c", run="lead@other")]
    d = pa.analyse_stream(make_stream(tmp_path, lines))
    assert d["attempts"][0]["admitted_version"] is None  # no revise event of that run within 5 s


def test_cross_check_with_revise_playbook_attempts_txt(tmp_path):
    s = make_stream(tmp_path, [tool("2026-10-25T07:17:51+00:00", ok=False, error=P1, error_type="OrgError"), tool("2026-10-25T07:17:58+00:00")])
    (s / "revise-playbook-attempts.txt").write_text("# revise_playbook attempts\n\ntool.call events with tool == revise_playbook: 2\n- x\n")
    assert pa.analyse_stream(s)["revise_playbook_attempts_txt"] == {"present": True, "events_listed": 2, "agrees": True}
    (s / "revise-playbook-attempts.txt").write_text("tool.call events with tool == revise_playbook: 3\n")
    assert pa.analyse_stream(s)["revise_playbook_attempts_txt"]["agrees"] is False
    (s / "revise-playbook-attempts.txt").unlink()
    assert pa.analyse_stream(s)["revise_playbook_attempts_txt"] == {"present": False, "events_listed": None, "agrees": None}


def test_cli_and_selfcheck(tmp_path):
    lines = [tool("2026-10-25T07:17:51+00:00", ok=False, error=P1, error_type="OrgError"), tool("2026-10-25T07:17:58+00:00")]
    s = make_stream(tmp_path, lines)
    out = tmp_path / "o"
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "playbook_attempts.py"), str(s), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = json.loads((out / "playbook_attempts.json").read_text())
    assert d["counts"]["attempts"] == 2 and "P1-REFUSED" in (out / "playbook_attempts.txt").read_text()
    assert (out / "playbook_attempts.json").read_text() == json.dumps(d, sort_keys=True, indent=2) + "\n"
    ev_dir = tmp_path / "E7EV"
    ev_dir.mkdir()
    for n in ("s1", "s2", "s3"):
        shutil.copytree(s, ev_dir / n)
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps([
        {"module": "playbook_attempts", "stream": "s1", "key": "counts.attempts", "expected": 2, "source": "t"},
        {"module": "playbook_attempts", "stream": "s3", "key": "counts.p1_refused", "expected": 0, "source": "t (wrong)"},
        {"module": "playbook_attempts", "stream": "s2", "key": "counts.in_window", "expected": 0, "source": "t"},
    ]))
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "playbook_attempts.py"), "--selfcheck", str(ev_dir), "--out", str(tmp_path / "sc"), "--expected", str(exp)],
                       capture_output=True, text=True)
    lines_out = r.stdout.strip().splitlines()
    assert lines_out[-1] == "selfcheck playbook_attempts: 2 of 3 OK" and r.returncode == 1, r.stdout
    assert (tmp_path / "sc" / "e7-s2" / "playbook_attempts.json").exists()
