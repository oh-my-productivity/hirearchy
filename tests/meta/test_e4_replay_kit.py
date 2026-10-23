# mypy: ignore-errors
"""The kit of the deterministic replays (``tests/testkit/e4_replay.py``): it reads E4's and E3's recorded evidence, and a missing file or an unbound
id fails the test that asks for it, never skips it (a replay that quietly did not run proves nothing)."""

import subprocess

import pytest
from testkit import e4_replay
from testkit.e4_replay import EV, EV3, ReplayIds, evidence, lena_line, scripted_report, tool_call

from hirearchy.kernel import ROOT

Failed = pytest.fail.Exception


def test_evidence_reads_a_file_under_ev_and_ev3():
    meta, body = evidence("s1r/service/history--SERVICE.v1.md")  # E4: the first contract of the s1r stream
    assert meta["name"] == "weekly-memo" and "acceptance" in meta and body.strip() == ""
    meta3, _ = evidence("service/SERVICE.v1.md")  # E3: found under its own tree
    assert meta3["name"] == "weekly-meeting-memo"
    assert evidence(EV / "s1r" / "turn-05.prompt.txt")[1].startswith("No, not right yet.")  # an absolute path reads the same way
    assert evidence("s1r/msgs/read/20261022T192346320735-lead-fa63.md")[0]["status"] == "done"
    assert EV.is_dir() and EV3.is_dir()


def test_a_missing_evidence_file_fails_the_test():
    with pytest.raises(Failed, match="no evidence file"):
        evidence("s1r/no-such-file.md")
    with pytest.raises(Failed, match="no evidence file"):
        evidence(EV / "s9r" / "service" / "SERVICE.v1.md")


def test_tool_call_reads_the_e4_contract_loop_format():
    args = tool_call(EV / "s1r", 22)  # call #22 of s1r: the rejection root recorded before the amendment
    assert args["task_id"] == "20261022T182945409755-root-ed94" and args["verdict"] == "reject" and args["criterion"] == ["C5"]
    assert args["note"].startswith("Sam's CI item says 'before Friday'")
    assert tool_call(EV / "s1r", 21)["name"] == "weekly-memo"  # #21: the define_service made before it


def test_tool_call_reads_the_e3_one_line_format():
    args = tool_call(EV3, 24)  # CALL #24 of E3: Lena's first rejection
    assert args["verdict"] == "reject" and args["criterion"] == ["C6", "C3"] and args["note"].startswith("No, not right yet.")
    assert tool_call(EV3, 25)["name"] == "weekly-meeting-memo"


def test_an_absent_or_duplicated_call_number_fails(tmp_path):
    with pytest.raises(Failed, match="call #99999"):
        tool_call(EV / "s1r", 99999)  # absent
    twice = tmp_path / "stream"
    twice.mkdir()
    (twice / "contract-loop.txt").write_text(
        '[2026-10-22T18:59:00.000Z] call #7 turn 1 hirearchy::feedback status=completed\nARGS: {"tool_id": "x", "arguments": {"a": 1}}\n\n'
        '[2026-10-22T18:59:01.000Z] call #7 turn 1 hirearchy::feedback status=completed\nARGS: {"tool_id": "x", "arguments": {"a": 2}}\n',
        encoding="utf-8",
    )
    with pytest.raises(Failed, match="call #7 .*twice|more than once"):
        tool_call(twice, 7)
    with pytest.raises(Failed, match="no tool-call record"):
        tool_call(tmp_path, 1)  # a stream with neither file


def test_lena_line_reads_e4_prompt_files_and_e3_lena_lines():
    t5 = lena_line(EV / "s1r", 5)  # E4: turn-05.prompt.txt, as it was sent
    assert t5.startswith("No, not right yet. Sam's CI item says 'before Friday'")
    e3 = lena_line(EV3, 5)  # E3: the line after the marker in turn-05.txt
    assert e3.startswith("No, not right yet. Sam's CI item says 'before Friday', so that has a date, 2026-10-09.") and "\n" not in e3
    with pytest.raises(Failed, match="no turn"):
        lena_line(EV / "s1r", 99)


def test_replay_ids_map_e4_ids_and_pass_c_and_r_ids_through():
    ids = ReplayIds()
    ids.bind("20261022T182945409755-root-ed94", "20261018T100000000002-root-0000")
    assert ids.of("20261022T182945409755-root-ed94") == "20261018T100000000002-root-0000"
    assert ids.of("C5") == "C5" and ids.of("R12") == "R12"  # criteria and assertions are numbered the same in the replay
    assert ids.map(["C9", "20261022T182945409755-root-ed94", "R1"]) == ["C9", "20261018T100000000002-root-0000", "R1"]
    assert ids.map([]) == []
    with pytest.raises(Failed, match="already bound"):
        ids.bind("20261022T182945409755-root-ed94", "other")  # one id, one meaning


def test_an_unbound_e4_id_fails():
    ids = ReplayIds()
    with pytest.raises(Failed, match="20261022T185900393028-root-cdb5"):
        ids.of("20261022T185900393028-root-cdb5")
    with pytest.raises(Failed, match="not bound"):
        ids.map(["C1", "20261022T185900393028-root-cdb5"])


def test_scripted_report_writes_the_artifacts_reports_and_commits(org):
    org.hire(ROOT, "lead", "Lead", "Run the memo service.", can_hire=True, max_children=2)
    task = org.delegate(ROOT, "lead", "Memo", "Write the memo.", "It exists.", budget=4)
    result = "s1r/msgs/read/20261022T192346320735-lead-fa63.md"  # E4's delivery of the 2026-10-12 memo (status done, questions, lessons, artifacts)
    texts = {
        "lead/writer/work/memo-2026-10-12.md": "Summary: a platform weekly.\n",
        "lead/checker/work/review-memo-2026-10-12.md": "criteria met: 7 of 7\n",
    }
    sent = scripted_report(org, task.id, result, texts)
    assert (org.root / "lead/writer/work/memo-2026-10-12.md").read_text() == "Summary: a platform weekly.\n"
    got = [m for m in org.messages(ROOT, "inbox") if m.type == "result" and m.reply_to == task.id]
    assert [m.id for m in got] == [sent.id] and sent.status == "done"
    meta, body = evidence(result)
    assert "Questions for the client:" in sent.body and "Memo for the 2026-10-12 Platform weekly delivered." in sent.body
    assert "## Lessons\nNo rework needed" in sent.body and "lead/writer/work/memo-2026-10-12.md" in sent.body
    log = subprocess.run(["git", "log", "--format=%s"], cwd=org.root, capture_output=True, text=True).stdout.splitlines()
    assert log[0].startswith("lead: run ok") and body  # committed the way a settled run is
    assert e4_replay.REPO.name  # the kit finds the repository
