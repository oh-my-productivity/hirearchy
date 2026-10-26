# mypy: ignore-errors
"""The kit of the G0 replays (``tests/testkit/g0_replay.py``, 0b.1 design 6 and A4): the E5 kit pointed at G0's evidence and its service, with the
three options the 0b.1 replays need (root's ``inflight``, pinned deliverables, the team's files, a one-commit git history). A missing evidence file, a
bad pin, an unfaithful history or a failing git call fails the test that asks for it, never skips it (a replay that quietly did not run proves nothing)."""

import shutil
import subprocess

import pytest
from testkit import g0_replay
from testkit.org_replay import md5_of
from testkit.g0_replay import EVG0, SERVICE_NAME, materialize

from hirearchy.kernel import ROOT

Failed = pytest.fail.Exception
git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")

S2_FIRST_CUT = "20261026T061639840350"  # m0-s2: the stamp of root's first request, 6f1d (inclusive)
S2_6F1D = "20261026T061639840350-root-6f1d"
S2_T4_CUT = "20261026T062340000000"  # m0-s2 turn 4: after f5df (06:23:07), before the user's 9279 (06:24:13) and v3 (06:25:26)
S2_AFTER_V3 = "20261026T062600000000"  # after v3 b389f15 (06:25:26), while e876 lists the memo
S2_E876 = "20261026T062305224870-lead-e876"
S2_PIN = ("memo-2026-10-05.md", "memo-2026-10-05.v2.0d07ec4.md", "2026-10-26T06:23:13.513Z", 3)
S2_V2_MD5 = "47d12bc382b8200461240047cb3a935c"
S2_V2_NS = 1_792_995_793_513_000_000  # 2026-10-26T06:23:13.513Z, ns since the epoch (the pin's mtime)


def names(path):
    return sorted(p.name for p in path.iterdir())


def copied_evidence(tmp_path):
    """The parts of m0-s2 the kit reads, copied, to break one of them."""
    copy = tmp_path / "evidence"
    for part in ("org-files", "msgs", "run-logs", "service"):
        shutil.copytree(EVG0 / "m0-s2" / part, copy / "m0-s2" / part)
    shutil.copytree(EVG0 / "m0-s2" / "memos" / "versions", copy / "m0-s2" / "memos" / "versions")
    shutil.copyfile(EVG0 / "m0-s2" / "deliverables-log.txt", copy / "m0-s2" / "deliverables-log.txt")
    return copy


def use(monkeypatch, evidence):
    monkeypatch.setattr(g0_replay, "EVG0", evidence)


def test_the_service_is_the_weekly_meeting_memo_of_the_g0_streams():
    assert SERVICE_NAME == "weekly-meeting-memo"
    assert EVG0.name == "evidence" and EVG0.parent.name == "G0-noise-baseline"


def test_the_cut_is_inclusive_and_the_organization_is_root_org(tmp_path):
    org = materialize("m0-s2", S2_FIRST_CUT, tmp_path)
    assert org == tmp_path / "org"
    assert names(org / "sent") == [f"{S2_6F1D}.md"]  # 6f1d is at the cut itself
    before = materialize("m0-s2", "20261026T061639840349", tmp_path / "before")
    assert not (before / "sent").exists() or names(before / "sent") == []


def test_inflight_of_root_puts_the_message_in_the_organization_s_own_inflight_box(tmp_path):
    org = materialize("m0-s2", S2_T4_CUT, tmp_path, inflight={ROOT: [S2_E876]})
    assert names(org / "inflight") == [f"{S2_E876}.md"]
    assert f"{S2_E876}.md" not in names(org / "read")
    assert (org / "inflight" / f"{S2_E876}.md").read_bytes() == (EVG0 / "m0-s2" / "msgs" / "read" / f"{S2_E876}.md").read_bytes()


def test_the_contract_is_the_kept_one_except_its_path_line_which_names_no_deliverables(tmp_path):
    org = materialize("m0-s2", S2_T4_CUT, tmp_path)
    kept = (EVG0 / "m0-s2" / "service" / "history--SERVICE.v1.md").read_text(encoding="utf-8").split("\n")
    made = (org / "lead" / "services" / SERVICE_NAME / "SERVICE.md").read_text(encoding="utf-8").split("\n")
    assert len(made) == len(kept)
    changed = [(a, b) for a, b in zip(kept, made) if a != b]
    assert len(changed) == 1 and changed[0][0].startswith("  path: /tmp/hirearchy-g0-")
    assert changed[0][1] == f"  path: {tmp_path / 'no-deliverables'}"
    assert "/tmp/hirearchy-g0-" not in "\n".join(made)
    assert not (tmp_path / "no-deliverables").exists() and not (tmp_path / "deliverables").exists()


def test_the_pinned_deliverable_has_the_checked_bytes_and_the_pinned_time(tmp_path):
    org = materialize("m0-s2", S2_T4_CUT, tmp_path, deliverables=[S2_PIN])
    memo = tmp_path / "deliverables" / "memo-2026-10-05.md"
    assert names(tmp_path / "deliverables") == ["memo-2026-10-05.md"]
    assert md5_of(memo) == S2_V2_MD5
    assert memo.stat().st_mtime_ns == S2_V2_NS
    contract = (org / "lead" / "services" / SERVICE_NAME / "SERVICE.md").read_text(encoding="utf-8")
    assert f"  path: {tmp_path / 'deliverables'}\n" in contract and "/tmp/hirearchy-g0-" not in contract


def test_a_pin_whose_log_line_is_not_a_header_or_whose_time_differs_fails(tmp_path):
    with pytest.raises(Failed, match="not the start of a logged command"):
        materialize("m0-s2", S2_T4_CUT, tmp_path / "a", deliverables=[(*S2_PIN[:3], 2)])
    with pytest.raises(Failed, match="2026-10-26T06:23:13.514Z"):
        materialize("m0-s2", S2_T4_CUT, tmp_path / "b", deliverables=[(S2_PIN[0], S2_PIN[1], "2026-10-26T06:23:13.514Z", 3)])


def test_a_version_file_that_is_missing_or_has_another_md5_fails(tmp_path, monkeypatch):
    copy = copied_evidence(tmp_path)
    use(monkeypatch, copy)
    version = copy / "m0-s2" / "memos" / "versions" / S2_PIN[1]
    version.write_bytes(b"not the version INDEX lists\n")
    with pytest.raises(Failed, match=f"md5 .* {S2_V2_MD5}"):
        materialize("m0-s2", S2_T4_CUT, tmp_path / "wrong", deliverables=[S2_PIN])
    with pytest.raises(Failed, match=f"md5 .* {S2_V2_MD5}"):
        materialize("m0-s2", S2_T4_CUT, tmp_path / "wrong-team", team_files=True)
    version.unlink()
    with pytest.raises(Failed, match=r"no evidence file .*memo-2026-10-05\.v2\.0d07ec4\.md"):
        materialize("m0-s2", S2_T4_CUT, tmp_path / "missing", deliverables=[S2_PIN])
    with pytest.raises(Failed, match=r"no evidence file .*memo-2026-10-05\.v2\.0d07ec4\.md"):
        materialize("m0-s2", S2_T4_CUT, tmp_path / "missing-team", team_files=True)


def test_a_pin_that_INDEX_does_not_list_fails(tmp_path):
    with pytest.raises(Failed, match="lists no version file"):
        materialize("m0-s2", S2_T4_CUT, tmp_path, deliverables=[(S2_PIN[0], "memo-2026-10-05.v9.abcdef0.md", S2_PIN[2], 3)])


def test_the_team_files_are_the_newest_versions_at_the_cut_and_a_path_with_none_is_not_written(tmp_path):
    org = materialize("m0-s2", S2_T4_CUT, tmp_path, team_files=True)
    work = org / "lead" / "writer" / "work"
    assert md5_of(work / "memo-2026-10-05.md") == S2_V2_MD5  # v2 (06:21:48); v3 came at 06:25:26, after the cut
    assert names(work) == ["memo-2026-10-05.md"]  # A4: memo-2026-10-12.md (06:39:20) and memo-2026-10-19.md (06:44:10) have no version yet: no failure
    later = materialize("m0-s2", S2_AFTER_V3, tmp_path / "later", team_files=True)
    assert md5_of(later / "lead" / "writer" / "work" / "memo-2026-10-05.md") == "f642f38ce079521c68d106e7b9b4c4f8"  # v3


@git
def test_the_history_is_one_commit_that_holds_the_sent_copy_of_the_result(tmp_path):
    org = materialize("m0-s2", S2_T4_CUT, tmp_path, team_files=True, history=True)
    count = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=org, check=True, capture_output=True, text=True).stdout.strip()
    held = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=org, check=True, capture_output=True, text=True).stdout.split()
    assert count == "1"
    assert f"lead/sent/{S2_E876}.md" in held and "lead/writer/work/memo-2026-10-05.md" in held


@git
def test_a_history_after_a_listed_file_changed_is_not_faithful_and_fails(tmp_path):
    with pytest.raises(Failed, match="not faithful"):
        materialize("m0-s2", S2_AFTER_V3, tmp_path, team_files=True, history=True)  # v3 (06:25:26) came after e876 (06:23:05), which lists the memo


def test_a_history_asks_for_the_team_files(tmp_path):
    with pytest.raises(Failed, match="history needs team_files"):
        materialize("m0-s2", S2_T4_CUT, tmp_path, history=True)


def test_a_missing_stream_or_a_bad_cut_fails(tmp_path):
    with pytest.raises(Failed, match="no evidence directory"):
        materialize("m9-s9", S2_T4_CUT, tmp_path / "none")
    with pytest.raises(Failed, match="21-character"):
        materialize("m0-s2", "2026", tmp_path / "cut")
