# mypy: ignore-errors
"""The kit of the E7 replays (``tests/testkit/e7_replay.py``, 0a.5 plan item 2): the E5 kit pointed at E7's evidence and its service, so a replay of an
E7 stream rebuilds the organization the stream had at one moment from the raw evidence. A missing evidence file fails the test that asks for it, never
skips it (a replay that quietly did not run proves nothing)."""

import shutil

import pytest
from testkit import e7_replay
from testkit.e7_replay import EV7, SERVICE_NAME, materialize

from hirearchy.core import Org

Failed = pytest.fail.Exception

S2_C671_CUT = "20261025T075038845671"  # s2: the stamp of c671, the user's rework of 3ca4 (call #20)
S2_3CA4 = "20261025T074451197103-root-3ca4"
S2_C671 = "20261025T075038845671-root-c671"
S2_D5C7 = "20261025T074917047599-lead-d5c7"


def names(path):
    return sorted(p.name for p in path.iterdir())


def test_the_service_is_the_weekly_meeting_memo_of_the_e7_streams():
    assert SERVICE_NAME == "weekly-meeting-memo"
    assert EV7.name == "evidence" and EV7.parent.name == "E7-org-growth-0a4-recheck"


def test_s2_at_the_cut_of_c671_holds_the_two_requests_the_reply_and_the_contract(tmp_path):
    root = materialize("s2", S2_C671_CUT, tmp_path / "org")
    assert names(root / "sent") == [f"{S2_3CA4}.md", f"{S2_C671}.md"]  # c671 is at the cut itself (inclusive)
    assert f"{S2_D5C7}.md" in names(root / "read")  # the lead's blocked result d5c7 is in root's read/
    contract = root / "lead" / "services" / SERVICE_NAME / "SERVICE.md"
    assert contract.read_text(encoding="utf-8") == (EV7 / "s2" / "service" / "history--SERVICE.v1.md").read_text(encoding="utf-8")
    assert "budget: 12" in contract.read_text(encoding="utf-8")


def test_the_runs_before_c671_are_nine_empty_logs(tmp_path):
    root = materialize("s2", S2_C671_CUT, tmp_path / "org")
    logs = {a: names(root / a / "runs") for a in ("lead", "lead/writer", "lead/reviewer")}
    assert [len(logs[a]) for a in ("lead", "lead/writer", "lead/reviewer")] == [5, 2, 2]
    assert sum(len(v) for v in logs.values()) == 9
    assert all(p.stat().st_size == 0 for a in logs for p in (root / a / "runs").iterdir())


def test_the_product_opens_it_and_reads_the_case_of_3ca4(tmp_path):
    org = Org(materialize("s2", S2_C671_CUT, tmp_path / "org"))
    cases = org.runtime.case_history.cases("lead", SERVICE_NAME)
    assert any(S2_3CA4 in {t.id for t in c.tasks} for c in cases)


def test_a_missing_evidence_file_fails_the_test(tmp_path):
    with pytest.raises(Failed, match="no evidence directory"):
        materialize("s9", S2_C671_CUT, tmp_path / "none")
    copy = tmp_path / "evidence"
    for part in ("service", "org-files", "msgs", "run-logs"):
        shutil.copytree(EV7 / "s2" / part, copy / "s2" / part)
    (copy / "s2" / "service" / "history--SERVICE.v1.md").unlink()
    saved = e7_replay.EV7
    try:
        e7_replay.EV7 = copy
        with pytest.raises(Failed, match="no evidence file .*history--SERVICE.v1.md"):
            materialize("s2", S2_C671_CUT, tmp_path / "broken")
    finally:
        e7_replay.EV7 = saved
