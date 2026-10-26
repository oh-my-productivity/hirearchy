"""Tests of prompt_sizes.py (G0 harness, helper M): the owner's prompt bytes per run and the words of the Reflect sections."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))

import prompt_sizes as ps  # noqa: E402


def log_text(prompt_body, output="# kiro: run started\nhello\n# exit 0 after 5s\n", agent="lead"):
    return f"# run of {agent}, 1 message(s)\n# senders: root\n# cmd: kiro-cli chat\n# ---- prompt ----\n{prompt_body}# ---- output ----\n{output}"


REFLECT = "# Reflect before you start: weekly-meeting-memo\nOne two three four five.\nSix seven.\n\n"


def prompt(reflect=False, extra=""):
    return "# hirearchy run: you are `lead`\n\n# Your state\nstate line\n\n" + (REFLECT if reflect else "") + "# New messages for this run (1)\n" + extra


def test_prompt_stats_counts_bytes_between_the_markers_and_reflect_words():
    body = prompt(reflect=True)
    st = ps.prompt_stats(log_text(body))
    assert st["bytes"] == len(body.encode())
    # E7's rule: the whole section from its heading line to the next '# ' line that is not a Reflect line, split on whitespace
    assert st["reflect"] is True and st["reflect_words"] == len(REFLECT.split()) == 13


def test_prompt_stats_without_a_reflect_section():
    st = ps.prompt_stats(log_text(prompt()))
    assert st["reflect"] is False and st["reflect_words"] == 0


def test_bytes_are_utf8_bytes_not_characters():
    body = prompt(extra="caf\u00e9 \u2192 ok\n")
    assert ps.prompt_stats(log_text(body))["bytes"] == len(body.encode("utf-8")) > len(body)


def test_a_log_without_the_prompt_marker_has_no_size():
    st = ps.prompt_stats("# run of lead\n# cmd: x\n# exit 1 after 0s\n")
    assert st["bytes"] is None and st["reflect"] is False


def test_reflect_section_runs_to_the_end_of_the_prompt_when_nothing_follows():
    body = "# hirearchy run: you are `lead`\n\n" + REFLECT
    assert ps.prompt_stats(log_text(body))["reflect_words"] == len(REFLECT.split())


def make_stream(tmp_path, owner="lead", sizes=(("20261025T070000000001", False), ("20261025T070100000002", True), ("20261025T070200000003", False))):
    s = tmp_path / "s1"
    d = s / "run-logs" / owner
    d.mkdir(parents=True)
    (s / "run-logs" / f"{owner}-writer").mkdir()
    (s / "run-logs" / f"{owner}-writer" / "20261025T070050000000.log").write_text(log_text(prompt(extra="writer " * 500), agent=f"{owner}/writer"))
    for i, (stamp, refl) in enumerate(sizes):
        (d / f"{stamp}.log").write_text(log_text(prompt(reflect=refl, extra="pad " * [200, 500, 300][i % 3] + "\n"), agent=owner))
    (s / "msgs" / "sent").mkdir(parents=True)
    (s / "msgs" / "sent" / "20261025T065900000000-root-aaaa.md").write_text(
        f"---\nid: 20261025T065900000000-root-aaaa\nfrom: root\nto: {owner}\ntype: task\nservice: weekly-meeting-memo\n---\nbody\n")
    return s


def test_analyse_stream_first_max_last_and_difference(tmp_path):
    s = make_stream(tmp_path)
    d = ps.analyse_stream(s)
    sizes = [r["bytes"] for r in d["lead_runs"]]
    assert [r["stamp"] for r in d["lead_runs"]] == ["20261025T070000000001", "20261025T070100000002", "20261025T070200000003"]
    assert d["bytes"] == {"first": sizes[0], "max": max(sizes), "last": sizes[2], "last_minus_first": sizes[2] - sizes[0], "runs": 3}
    assert d["reflect_words"] == {"min": 13, "max": 13, "sections": 1}
    assert d["owner"] == "lead" and d["owner_detected_by"] == "root tasks"
    assert d["reference_E3"] == {"first_kb": 20.2, "peak_kb": 29.9, "reflect_words_min": 452, "reflect_words_max": 679}
    assert d["script"]["name"] == "prompt_sizes.py" and "run-logs/lead/20261025T070100000002.log" in d["source_files"]
    assert not any("writer" in f for f in d["source_files"])  # only the owner's runs are read


def test_the_writers_runs_are_not_counted(tmp_path):
    d = ps.analyse_stream(make_stream(tmp_path))
    assert d["bytes"]["runs"] == 3


def test_order_is_by_run_stamp_not_by_modification_time(tmp_path):
    s = make_stream(tmp_path)
    import os
    p = s / "run-logs" / "lead" / "20261025T070000000001.log"
    os.utime(p, (4102444800, 4102444800))  # year 2100
    d = ps.analyse_stream(s)
    assert d["lead_runs"][0]["stamp"] == "20261025T070000000001"


def test_owner_other_than_lead_is_detected_from_the_root_tasks(tmp_path):
    d = ps.analyse_stream(make_stream(tmp_path, owner="chief"))
    assert d["owner"] == "chief" and d["bytes"]["runs"] == 3


def test_owner_detected_from_the_contract_path_when_there_are_no_root_tasks(tmp_path):
    s = make_stream(tmp_path, owner="chief")
    for f in (s / "msgs" / "sent").glob("*.md"):
        f.unlink()
    p = s / "run-logs" / "chief" / "20261025T070000000001.log"
    p.write_text(log_text(prompt(extra="- weekly-meeting-memo: contract v1; contract: chief/services/weekly-meeting-memo/SERVICE.md; playbook: x\n"), agent="chief"))
    d = ps.analyse_stream(s)
    assert d["owner"] == "chief" and d["owner_detected_by"] == "contract path"


def test_no_reflect_section_anywhere_gives_none(tmp_path):
    d = ps.analyse_stream(make_stream(tmp_path, sizes=(("20261025T070000000001", False), ("20261025T070100000002", False))))
    assert d["reflect_words"] == {"min": None, "max": None, "sections": 0}


def test_a_run_log_without_a_prompt_is_listed_not_counted(tmp_path):
    s = make_stream(tmp_path)
    (s / "run-logs" / "lead" / "20261025T070300000004.log").write_text("# run of lead\n# exit 1 after 0s\n")
    d = ps.analyse_stream(s)
    assert d["bytes"]["runs"] == 3 and d["could_not_parse"] == ["run-logs/lead/20261025T070300000004.log"]
    assert d["bytes"]["last"] == d["lead_runs"][2]["bytes"]


def test_cross_check_against_the_extract_mechanical_file(tmp_path):
    s = make_stream(tmp_path)
    d0 = ps.analyse_stream(s)
    lines = ["# lead prompt sizes (protocol 7.2): bytes between '# ---- prompt ----' and '# ---- output ----'", ""]
    for r in d0["lead_runs"]:
        lines.append(f"lead@{r['stamp']}     bytes={r['bytes']} reflect_section={'yes' if r['reflect'] else 'no'} reflect_words={r['reflect_words']} regression_list=no")
    (s / "lead-prompt-sizes.txt").write_text("\n".join(lines) + "\n")
    assert ps.analyse_stream(s)["lead_prompt_sizes_txt"] == {"present": True, "compared": 3, "differences": []}
    lines[2] = lines[2].replace("bytes=", "bytes=1")
    (s / "lead-prompt-sizes.txt").write_text("\n".join(lines) + "\n")
    diff = ps.analyse_stream(s)["lead_prompt_sizes_txt"]["differences"]
    assert len(diff) == 1 and diff[0]["stamp"] == "20261025T070000000001"
    (s / "lead-prompt-sizes.txt").unlink()
    assert ps.analyse_stream(s)["lead_prompt_sizes_txt"] == {"present": False, "compared": 0, "differences": []}


def test_cli_and_selfcheck(tmp_path):
    s = make_stream(tmp_path)
    out = tmp_path / "o"
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "prompt_sizes.py"), str(s), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = json.loads((out / "prompt_sizes.json").read_text())
    assert d["bytes"]["runs"] == 3 and "first" in (out / "prompt_sizes.txt").read_text()
    assert (out / "prompt_sizes.json").read_text() == json.dumps(d, sort_keys=True, indent=2) + "\n"
    ev = tmp_path / "E7EV"
    ev.mkdir()
    import shutil
    src = make_stream(tmp_path / "src")
    for n in ("s1", "s2", "s3"):
        shutil.copytree(src, ev / n)  # E7EV/<sN> is the stream directory itself
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps([
        {"module": "prompt_sizes", "stream": "s1", "key": "bytes.runs", "expected": 3, "source": "t"},
        {"module": "prompt_sizes", "stream": "s2", "key": "reflect_words.max", "expected": 14, "source": "t (wrong)"},
        {"module": "playbook_attempts", "stream": "s2", "key": "zz", "expected": 1, "source": "other module"},
    ]))
    r = subprocess.run([sys.executable, "-B", str(HARNESS / "prompt_sizes.py"), "--selfcheck", str(ev), "--out", str(tmp_path / "sc"), "--expected", str(exp)],
                       capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    assert lines[-1] == "selfcheck prompt_sizes: 1 of 2 OK" and r.returncode == 1, r.stdout
    assert (tmp_path / "sc" / "e7-s3" / "prompt_sizes.json").exists()
