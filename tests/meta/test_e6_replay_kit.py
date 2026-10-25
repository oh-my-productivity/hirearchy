# mypy: ignore-errors
"""The kit of the E6 replays (``tests/testkit/e6_replay.py``, 0a.4 design 17.1): the E5 kit pointed at E6's evidence and its service, so a replay of an
E6 stream rebuilds the organization the stream had at one moment from the raw evidence. A missing evidence file fails the test that asks for it, never
skips it (a replay that quietly did not run proves nothing)."""

import shutil

import pytest
from testkit import e5_replay, e6_replay
from testkit.e6_replay import EV6, SERVICE_NAME, materialize

from hirearchy.core import Org

Failed = pytest.fail.Exception

S3_BC02_CUT = "20261024T171425096624"  # s3: the stamp of bc02, the user's rework of 4a3e (call #19)
S3_4A3E = "20261024T170957358424-root-4a3e"
S3_BC02 = "20261024T171425096624-root-bc02"
S3_11CC = "20261024T171306190749-lead-11cc"


def names(path):
    return sorted(p.name for p in path.iterdir())


def test_the_service_is_the_weekly_memo_of_the_e6_streams():
    assert SERVICE_NAME == "weekly-memo"
    assert EV6.name == "evidence" and EV6.parent.name == "E6-org-growth-0a3-recheck"


def test_s3_at_the_cut_of_bc02_holds_the_two_requests_the_reply_and_the_contract(tmp_path):
    root = materialize("s3", S3_BC02_CUT, tmp_path / "org")
    assert names(root / "sent") == [f"{S3_4A3E}.md", f"{S3_BC02}.md"]  # bc02 is at the cut itself (inclusive)
    assert f"{S3_11CC}.md" in names(root / "read")  # the lead's result 11cc is in root's read/
    contract = root / "lead" / "services" / SERVICE_NAME / "SERVICE.md"
    assert contract.read_text(encoding="utf-8") == (EV6 / "s3" / "service" / "history--SERVICE.v1.md").read_text(encoding="utf-8")
    assert "budget: 16" in contract.read_text(encoding="utf-8")


def test_the_runs_of_the_interval_of_4a3e_are_five_empty_logs(tmp_path):
    root = materialize("s3", S3_BC02_CUT, tmp_path / "org")
    logs = {a: names(root / a / "runs") for a in ("lead", "lead/writer", "lead/reviewer")}
    assert logs["lead"] == ["20261024T171012998633.log", "20261024T171115450136.log", "20261024T171236209901.log"]
    assert sum(len(v) for v in logs.values()) == 5  # all of 4a3e's interval: nothing ran before it
    assert all(p.stat().st_size == 0 for a in logs for p in (root / a / "runs").iterdir())


def test_the_product_opens_it_and_counts_the_runs_of_the_request(tmp_path):
    org = Org(materialize("s3", S3_BC02_CUT, tmp_path / "org"))
    cases = org.runtime.case_history.cases("lead", SERVICE_NAME)
    assert any(S3_4A3E in {t.id for t in c.tasks} for c in cases)


def test_the_e5_kit_keeps_its_defaults(tmp_path):
    root = e5_replay.materialize("s1", "20261024T031704521000", tmp_path / "org")
    assert (root / "lead" / "services" / e5_replay.SERVICE_NAME / "SERVICE.md").is_file()
    assert e5_replay.SERVICE_NAME == "weekly-meeting-memo" and "E5-org-growth-0a2-recheck" in str(e5_replay.EV5)


def test_a_missing_evidence_file_fails_the_test(tmp_path):
    with pytest.raises(Failed, match="no evidence directory"):
        materialize("s9", S3_BC02_CUT, tmp_path / "none")
    copy = tmp_path / "evidence"
    shutil.copytree(EV6 / "s3" / "service", copy / "s3" / "service")
    shutil.copytree(EV6 / "s3" / "org-files", copy / "s3" / "org-files")
    shutil.copytree(EV6 / "s3" / "msgs", copy / "s3" / "msgs")
    shutil.copytree(EV6 / "s3" / "run-logs", copy / "s3" / "run-logs")
    (copy / "s3" / "service" / "history--SERVICE.v1.md").unlink()
    saved = e6_replay.EV6
    try:
        e6_replay.EV6 = copy
        with pytest.raises(Failed, match="no evidence file .*history--SERVICE.v1.md"):
            materialize("s3", S3_BC02_CUT, tmp_path / "broken")
    finally:
        e6_replay.EV6 = saved
