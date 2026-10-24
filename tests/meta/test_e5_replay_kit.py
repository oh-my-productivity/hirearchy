# mypy: ignore-errors
"""The kit of the E5 replays (``tests/testkit/e5_replay.py``): it rebuilds the organization a recorded stream had at one moment, from the raw evidence,
and a missing evidence file fails the test that asks for it, never skips it (a replay that quietly did not run proves nothing)."""

import shutil

import pytest
from testkit import e5_replay
from testkit.e5_replay import EV5, materialize

from hirearchy.core import ROOT, Org

Failed = pytest.fail.Exception

S1_CUT = "20261024T031704521000"  # s1: the moment of the case total after the relayed rework 963a (call #28)
S1_RELAYED = "20261024T031317713451-root-963a"
S2_6C4F = "20261024T034308207974"  # s2: the stamp of the user's rework 6c4f


def names(path):
    return sorted(p.name for p in path.iterdir())


def test_the_organization_holds_the_org_file_the_agents_and_the_contract_of_the_stream(tmp_path):
    root = materialize("s1", S1_CUT, tmp_path / "org")
    assert (root / "ORG.md").read_text(encoding="utf-8") == (EV5 / "s1" / "org-files" / "ORG.md").read_text(encoding="utf-8")
    assert [a for a in ("lead", "lead/writer", "lead/reviewer") if (root / a / "AGENT.md").is_file()] == ["lead", "lead/writer", "lead/reviewer"]
    contract = root / "lead" / "services" / "weekly-meeting-memo" / "SERVICE.md"
    assert contract.read_text(encoding="utf-8") == (EV5 / "s1" / "service" / "history--SERVICE.v1.md").read_text(encoding="utf-8")


def test_the_cut_is_inclusive_and_a_later_message_is_left_out(tmp_path):
    root = materialize("s2", S2_6C4F, tmp_path / "org")
    sent = names(root / "sent")
    assert sent == ["20261024T033732488726-root-ebe2.md", "20261024T034308207974-root-6c4f.md"]  # 6c4f is at the cut itself
    earlier = materialize("s2", "20261024T034308207973", tmp_path / "earlier")
    assert names(earlier / "sent") == ["20261024T033732488726-root-ebe2.md"]  # one microsecond before: 6c4f is out
    boxes = [b for base in (root, root / "lead") for b in (base / "inbox", base / "read", base / "sent") if b.is_dir()]
    assert boxes and all(p.name[:21] <= S2_6C4F for box in boxes for p in box.iterdir())


def test_each_agents_messages_and_logs_land_in_its_own_directory(tmp_path):
    root = materialize("s1", S1_CUT, tmp_path / "org")
    assert (root / "lead" / "sent").is_dir() and (root / "lead" / "read").is_dir() and (root / "lead" / "writer" / "sent").is_dir()
    logs = sorted((root / "lead" / "runs").glob("*.log"))
    assert logs and all(p.stat().st_size == 0 and p.name[:21] <= S1_CUT for p in logs)  # empty: the case counts read the names only
    assert sorted(p.name for p in logs) == sorted(
        p.name for p in (EV5 / "s1" / "run-logs" / "lead").glob("*.log") if p.name[:21] <= S1_CUT
    )
    assert all(p.name[:21] <= S1_CUT for agent in ("lead/writer", "lead/reviewer") for p in (root / agent / "runs").glob("*.log"))


def test_the_product_opens_it_and_counts_the_runs_of_the_chain(tmp_path):
    root = materialize("s1", S1_CUT, tmp_path / "org")
    org = Org(root)
    relayed = next(m for m in org.sent(ROOT) if m.id == S1_RELAYED)
    (case,) = [c for c in org.runtime.case_history.cases("lead", "weekly-meeting-memo") if relayed.id in {t.id for t in c.tasks}]
    assert (case.runs, case.relayed_runs) == (15, 5)


def test_a_missing_evidence_file_fails_the_test(tmp_path):
    with pytest.raises(Failed, match="no evidence directory"):
        materialize("s9", S1_CUT, tmp_path / "none")
    copy = tmp_path / "evidence"
    shutil.copytree(EV5 / "s1", copy / "s1")
    (copy / "s1" / "service" / "history--SERVICE.v1.md").unlink()
    saved = e5_replay.EV5
    try:
        e5_replay.EV5 = copy
        with pytest.raises(Failed, match="no evidence file .*history--SERVICE.v1.md"):
            materialize("s1", S1_CUT, tmp_path / "broken")
    finally:
        e5_replay.EV5 = saved


def test_a_cut_that_is_not_a_stamp_fails_the_test(tmp_path):
    with pytest.raises(Failed, match="21-character stamp"):
        materialize("s1", "20261024T0317", tmp_path / "short")


S3_CUT = "20261024T043138264197"  # s3: the lead's run that sent the rework delegation df89 (its batch was root's human rework 57b3)
S3_57B3 = "20261024T043106950333-root-57b3"


def test_the_inflight_messages_of_an_agent_are_in_its_inflight_box_and_nowhere_else(tmp_path):
    plain = materialize("s3", S3_CUT, tmp_path / "plain")
    assert (plain / "lead" / "read" / f"{S3_57B3}.md").is_file() and not (plain / "lead" / "inflight").exists()
    root = materialize("s3", S3_CUT, tmp_path / "org", inflight={"lead": [S3_57B3]})
    assert names(root / "lead" / "inflight") == [f"{S3_57B3}.md"]
    assert not (root / "lead" / "read" / f"{S3_57B3}.md").exists() and not (root / "lead" / "inbox" / f"{S3_57B3}.md").exists()
    assert (root / "lead" / "inflight" / f"{S3_57B3}.md").read_bytes() == (EV5 / "s3" / "msgs" / "lead-read" / f"{S3_57B3}.md").read_bytes()
    assert names(root / "lead" / "read") == [n for n in names(plain / "lead" / "read") if n != f"{S3_57B3}.md"]  # the rest stays where it was


def test_the_product_reads_the_inflight_box_as_the_batch(tmp_path):
    org = Org(materialize("s3", S3_CUT, tmp_path / "org", inflight={"lead": [S3_57B3]}))
    assert [m.id for m in org.messages("lead", "inflight")] == [S3_57B3]


def test_an_inflight_message_that_is_not_in_the_stream_at_the_cut_fails_the_test(tmp_path):
    with pytest.raises(Failed, match="inflight message .*57b3.* is not in the organization of lead at the cut"):
        materialize("s3", "20261024T043106950332", tmp_path / "early", inflight={"lead": [S3_57B3]})  # one microsecond before 57b3
    with pytest.raises(Failed, match="inflight message .*nope"):
        materialize("s3", S3_CUT, tmp_path / "unknown", inflight={"lead": ["20261024T043106950333-root-nope"]})
