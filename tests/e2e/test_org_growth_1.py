# mypy: ignore-errors
"""Phase 1, end to end: the itemized playbook and clause 2's two refusals (design 13, 20 e2e).

No scheduler, no LLM, no network: ``testkit.e7_replay.materialize`` rebuilds the organization an E7 stream had at one moment from the raw evidence
files, and the product's own services read it. A missing evidence file fails the test, never skips it. This module grows with the Phase 1 FEATs; an
expectation is never edited to match the product.
"""

import os
import shutil
import subprocess

import pytest
from testkit.e7_replay import materialize

from hirearchy.core import ROOT, Org
from hirearchy.kernel import OrgError

SERVICE = "weekly-meeting-memo"
S1_MEMO_1 = "20261025T070423629042-root-5efc"  # E7 s1: the first memo's case
S1_REWORK = "20261025T070822368798-root-5e3e"  # the user's rework of it, which Lena rejected
S1_REJECTION = "20261025T071537817238-root-905b"  # her human rejection of that rework (R1), about C2
S1_ANSWER = "20261025T071714388062-root-6096"  # the human link that answers it (C9), written 3 minutes later; the next memo came after it


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


def test_e7_flow_the_next_memo_requested_before_the_answer_is_request_unanswered(tmp_path):
    """Scenario 7 (design 20 e2e (7); Q1): E7 s1 at Lena's rejection 905b of the rework of memo 1. Asking for the next memo now is refused, naming the
    rejection, its case's task and the one question; at the human link 6096 (what E7 did) the same request is sent. Nothing is sent by the refusal."""
    waiting = Org(materialize("s1", S1_REJECTION[:21], tmp_path / "waiting"))
    sent = len(waiting.sent(ROOT))
    with pytest.raises(OrgError) as refusal:
        waiting.request(ROOT, SERVICE, {"notes_file": "2026-10-12.md"})
    assert str(refusal.value).startswith(
        f"refused: rejection R1 (message {S1_REJECTION}) on task {S1_REWORK} of `{SERVICE}` has no recorded answer yet, so the next request of "
        f"`{SERVICE}` waits: every rejection gets the user's answer within one request. Ask the user the one question first: "
        'About C2: add "<the rule, in their words>" as a lasting rule? Yes or no. On yes: '
    )
    assert len(waiting.sent(ROOT)) == sent
    answered = Org(materialize("s1", S1_ANSWER[:21], tmp_path / "answered"))
    memo = answered.request(ROOT, SERVICE, {"notes_file": "2026-10-12.md"})
    assert (memo.type, memo.service, memo.revises) == ("task", SERVICE, None)


def test_an_l_asis_accept_recorded_before_its_answer_is_feedback_unanswered(tmp_path):
    """Scenario 7 (design 20 e2e (7); Q1, L-ASIS): E7 s1 at Lena's rejection 905b. Her accept of the rejected delivery "as it is" is refused while
    the rejection has no answer, and recorded once the human link 6096 (what E7 did) is there. A relayed accept is never held."""
    waiting = Org(materialize("s1", S1_REJECTION[:21], tmp_path / "waiting"))
    sent = len(waiting.sent(ROOT))
    with pytest.raises(OrgError) as refusal:
        waiting.feedback(ROOT, S1_REWORK, "accept", "It is right as it is.", source="human")
    assert str(refusal.value).startswith(
        f"refused: rejection R1 (message {S1_REJECTION}) on task {S1_REWORK} of this case of `{SERVICE}` has no recorded answer yet, so the user's "
        "accept waits: a case is closed only after its rejections have the user's answers. "
    )
    assert len(waiting.sent(ROOT)) == sent
    assert waiting.feedback(ROOT, S1_REWORK, "accept", "The assistant's reading.", source="relayed").source == "relayed"
    answered = Org(materialize("s1", S1_ANSWER[:21], tmp_path / "answered"))
    assert answered.feedback(ROOT, S1_REWORK, "accept", "It is right as it is.", source="human").feedback == "accept"


def test_the_playbook_lock_file_is_never_committed(tmp_path):
    """Design 4.3, 19.3: a playbook write takes its lock on `services/<name>/.tmp-playbook.lock`. The `.tmp-` prefix is one `Org.init`'s `.gitignore`
    has ignored since the atomic writer's temp files, so `git add -A` does not commit it, and no reader lists it."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    org = Org.init(tmp_path / "org", "Mission.", {"poll_seconds": 0.05})
    org.hire(ROOT, "lead", "Lead", "Run the memos.", can_hire=True, max_children=2)
    org.define_service(
        ROOT, "lead", SERVICE, description="A memo.", inputs=[{"name": "topic", "description": "what it is about", "required": True}],
        acceptance=["A Summary line first"], deliverable={"description": "one markdown file"}, budget=10, playbook="# Memo\n\n1. Write it.\n",
    )
    lock = org.root / "lead" / "services" / SERVICE / ".tmp-playbook.lock"
    assert lock.is_file() and lock.stat().st_size == 0
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "add", "-A"], cwd=org.root, check=True, capture_output=True, env=env)
    tracked = subprocess.run(["git", "ls-files"], cwd=org.root, check=True, capture_output=True, text=True, env=env).stdout.splitlines()
    assert f"lead/services/{SERVICE}/PLAYBOOK.md" in tracked
    assert not [path for path in tracked if path.endswith(".tmp-playbook.lock")]
