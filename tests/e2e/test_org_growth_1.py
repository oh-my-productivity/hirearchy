# mypy: ignore-errors
"""Phase 1, end to end: the itemized playbook and clause 2's two refusals (design 13, 20 e2e).

No scheduler, no LLM, no network: ``testkit.e7_replay.materialize`` rebuilds the organization an E7 stream had at one moment from the raw evidence
files, and the product's own services read it. A missing evidence file fails the test, never skips it. This module grows with the Phase 1 FEATs; an
expectation is never edited to match the product.
"""

import json
import os
import shutil
import subprocess

from pathlib import Path

import pytest
from testkit.e2e_world import build_server
from testkit.e7_replay import materialize
from testkit.services_world import call, confirmed_amendment, deliver, fails, playbook_meta, request, svc  # noqa: F401  (svc is a fixture)

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


STEPS = "## Steps\n1. Search.\n2. Write.\n3. Check every claim."
CRITERION = "Every claim names its source"


def test_every_reader_names_the_same_watch_states(svc):
    """Design 20, "one derivation path" (Mandatory check 3): for a service with a watched item, the settler's read (`ServiceEvidence.watch`), the
    owner's states line, root's `services` suffix and the `quality` record's `watch` all name the state of the item `CaseServiceEvidence.watch`
    derives, at each step of its life: `new` (the criterion's words, added on rule (c)), then `warning` (a related rejection of a later delivery,
    answered by the user's link)."""
    svc.revise_playbook("ceo", "weekly-brief", "first", "first draft", [], text=STEPS)
    c3 = confirmed_amendment(svc, CRITERION)
    svc.revise_playbook("ceo", "weekly-brief", "add", "the criterion's words", [c3], kind="step", text=CRITERION)
    rt = svc.runtime

    def readers():
        """The four readers: (the settler's read, the owner's states line, root's playbook line, the quality record's watch)."""
        derived = rt.service_evidence.watch("ceo", "weekly-brief")
        owner = next((x for x in rt.service_prompt_sections.prompt_sections("ceo", []).splitlines() if x.startswith("Item states:")), "")
        listed = next(x for x in rt.service_reports.services_text(ROOT).splitlines() if x.startswith("  playbook v"))
        (record,) = [r for r in rt.case_records.records("weekly-brief")]
        return derived, owner, listed, record.watch

    task = request(svc, "ai")  # the first delivery after P4: its case is a candidate, waiting for the user's verdict
    deliver(svc, "ceo", task)
    request(svc, "chips")  # a request still open, so that the owner's prompt carries the playbook section
    derived, owner, listed, recorded = readers()
    p4 = next(w for w in derived if w.id == "P4")
    assert (p4.state, p4.waiting) == ("new", 1) and recorded == derived
    assert "P4 step, new since v2 (waiting for the client's verdict on 1 case)" in owner
    assert listed.endswith("; 4 items (0 rules); watched: P4 new (0 of 3 clean cases, k 3; waiting for the client's verdict on 1 case)")

    no = svc.feedback(ROOT, task.id, "reject", f"Missing again: {CRITERION}", source="human")
    svc.feedback(ROOT, task.id, "reject", "Yes, it is about that.", source="human", criterion=[c3], confirms=no.id)
    derived, owner, listed, recorded = readers()
    p4 = next(w for w in derived if w.id == "P4")
    assert p4.state == "warning" and p4.related == ("R2",) and recorded == derived
    assert "P4 step, warning: rejection R2 (case " in owner and "is related; one more retires it" in owner
    assert listed.endswith("; watched: P4 warning (R2; the next related rejection retires it)")
    quality = rt.quality_report.quality_data("weekly-brief")["services"][0]["watch"]
    assert [(e["item"], e["state"], e["related"]) for e in quality if e["item"] == "P4"] == [("P4", "warning", ["R2"])]
    assert "playbook watch: P4 warning (R2; the next related rejection retires it)" in rt.quality_report.quality_text("weekly-brief")


# ============================================================================================ the exit criterion end to end (design 18.4, 20 e2e (3), 21.1)
WEEK = "weekly-brief"
INITIALS = "Owners as initials only"  # the planted wrong rule's words: the client confirms them as C3, then changes her mind (18.4, memos 2 and 4)
FULL_NAMES = "Full names"  # what her answer to the next rejection adds (C4)
WARNED = "Rejection R2 is related to playbook item P4 of weekly-brief: P4 is in warning now (ceo was told); one more related rejection retires it."
RETIRED = "The watch retired P4 of weekly-brief (playbook v3) because rejections R2 and R3 are related to it; ceo was told."


def planted(org):
    """ceo's v1 and the planted wrong rule B (P4): the own words of C3, which the client confirmed (rule (c)); its watch starts ``new``. Returns C3."""
    org.revise_playbook("ceo", WEEK, "first", "first draft", [], text=STEPS)
    c3 = confirmed_amendment(org, INITIALS)
    added = org.revise_playbook("ceo", WEEK, "add", "the client's rule", [c3], kind="rule", then=INITIALS)
    assert (added.version, added.item, added.admission.rule) == (2, "P4", "c")
    return c3


def delivered(org, topic):
    """A new request of the service, delivered by its owner; returns the task."""
    task = request(org, topic)
    deliver(org, "ceo", task)
    return task


def related(org, server, task, c3, note="No."):
    """The client rejects ``task`` and answers the one question: it is about ``c3``. Returns the reply of the answering call."""
    no = org.feedback(ROOT, task.id, "reject", note, source="human")
    return call(server, "feedback", task_id=task.id, verdict="reject", note="Yes, it is about that.", source="human", criterion=[c3], confirms=no.id)


def retired_by_the_chain(org, server, c3):
    """The planted rule's two related rejections: R2 warns it (the answering call's reply says so), R3's answer is ``define_service(answers=...)`` that adds
    C4 and the runtime retires P4 in that call. Returns the two replies."""
    warned = related(org, server, delivered(org, "again"), c3)
    third = delivered(org, "again and again")
    no = org.feedback(ROOT, third.id, "reject", "Full names again.", source="human")
    retired = call(server, "define_service", owner="ceo", name=WEEK, add_acceptance=[FULL_NAMES], answers=no.id, about=c3, words="Yes, add it.")
    return warned, retired


def events_of(org, kind):
    """The events of ``kind`` the organization recorded, oldest first, as the files hold them (the fields flat, with ``actor``)."""
    found = [json.loads(line) for f in (org.root / ".runtime" / "events").glob("*/*.jsonl") for line in f.read_text(encoding="utf-8").splitlines()]
    return [{**e, **e.get("fields", {})} for e in sorted(found, key=lambda e: (e["ts"], e["seq"])) if e["kind"] == kind]


def playbook_of(org):
    return org.runtime.service_catalog.read_playbook("ceo", WEEK)


def notes_titled(org, addr, title):
    return [m for m in org.received(addr) if m.title == title]


def test_the_planted_rule_is_warned_at_the_first_related_answer_and_retired_in_the_second_answering_call(svc):
    """G1(a)+(b), design 20 e2e (3), 18.4: the planted rule B is `new`; the first related answer warns it (the reply says so, the owner is told quietly);
    the second answering call retires it before it returns (the reply says so, the owner and the parent are told), with nothing left to restore."""
    server = build_server(svc, ROOT)
    c3 = planted(svc)
    rt = svc.runtime
    (new,) = [w for w in rt.service_evidence.watch("ceo", WEEK) if w.id == "P4"]
    assert (new.state, new.related, new.retire_due) == ("new", (), False)
    warned = related(svc, server, delivered(svc, "again"), c3)
    assert warned.endswith("\n" + WARNED)
    (warning,) = [w for w in rt.service_evidence.watch("ceo", WEEK) if w.id == "P4"]
    assert (warning.state, warning.related, warning.retire_due) == ("warning", ("R2",), False)
    assert playbook_of(svc).version == 2  # a warning writes no version
    (to_owner,) = notes_titled(svc, "ceo", "playbook item P4 of weekly-brief: warning")
    assert not notes_titled(svc, ROOT, "playbook item P4 of weekly-brief: warning")  # the warning is the owner's alone
    assert to_owner.wake is False and "One more related rejection retires P4." in to_owner.body and "R2 (case " in to_owner.body
    third = delivered(svc, "again and again")
    no = svc.feedback(ROOT, third.id, "reject", "Full names again.", source="human")
    reply = call(server, "define_service", owner="ceo", name=WEEK, add_acceptance=[FULL_NAMES], answers=no.id, about=c3, words="Yes, add it.")
    assert reply.endswith("\n" + RETIRED)
    after = playbook_of(svc)
    assert after.version == 3 and INITIALS not in after.body and [i.id for i in after.items] == ["P1", "P2", "P3"]  # written in the answering call
    meta, _ = playbook_meta(svc)
    assert (meta["op"], meta["admitted"], meta["by"], meta["item"], meta["related"]) == ("watch", "watch", "runtime (watch)", "P4", ["R2", "R3"])
    assert "restores" not in meta  # the rule had no text before its watch: it is removed
    (event,) = [e for e in events_of(svc, "service.revise") if e["version"] == 3]
    assert (event["actor"], event["admitted"], event["by"]) == ("runtime", "watch", "runtime (watch)")
    title = "playbook of weekly-brief: the watch retired P4"
    for addr in ("ceo", ROOT):  # the owner and the parent (root is the client and the owner's parent)
        (told,) = notes_titled(svc, addr, title)
        assert told.wake is False and INITIALS not in told.body  # ids only, never the item's words
        assert told.body == (
            "Rejections R2 and R3 are about R1, C3, which P4 cited, so the runtime retired it (playbook v3). "
            "The client's verdicts decide this; no acknowledgement is needed."
        )
    (gone,) = [w for w in rt.service_evidence.watch("ceo", WEEK) if w.id == "P4"]
    assert (gone.state, gone.related, gone.retire_due) == ("retired", ("R2", "R3"), False)


def accepted(org, topic):
    """A new request delivered and accepted by the client herself (a human verdict): a judged case, clean for every item."""
    task = delivered(org, topic)
    org.feedback(ROOT, task.id, "accept", "That is right.", source="human")
    return task


def watched(org, item="P4"):
    (found,) = [w for w in org.runtime.service_evidence.watch("ceo", WEEK) if w.id == item]
    return found


def test_a_second_related_rejection_of_a_later_delivery_recorded_after_the_kth_verdict_retires_it(svc):
    """B1, design 8.1 (row xx), 20 e2e (3): k = 3. The rule is warned by a related rejection of its second case; the third case's verdict (the k-th) is
    recorded; then a rejection of a delivery made AFTER it, and recorded after it, is answered as related. That rejection is outside the rule's first window
    (its result is after E, its note after D) and the rule never reaches `kept`, yet it is the second related rejection of a warned rule (the warned
    window), so the runtime retires it in the answering call."""
    server = build_server(svc, ROOT)
    c3 = planted(svc)
    accepted(svc, "one")
    assert "P4 is in warning now" in related(svc, server, delivered(svc, "two"), c3)
    accepted(svc, "three")  # the k-th judged case: E and D are defined, and the rule is not clean
    held = watched(svc)
    assert (held.state, held.related, held.waiting, held.retire_due) == ("warning", ("R2",), 0, False)
    fourth = delivered(svc, "four")  # delivered after the k-th verdict
    no = svc.feedback(ROOT, fourth.id, "reject", "Full names again.", source="human")
    assert (watched(svc).state, watched(svc).related) == ("warning", ("R2",))  # a rejection nobody has answered yet relates to nothing
    answer = call(server, "feedback", task_id=fourth.id, verdict="reject", note="Yes, about that.", source="human", criterion=[c3], confirms=no.id)
    assert answer.endswith("\nThe watch retired P4 of weekly-brief (playbook v3) because rejections R2 and R3 are related to it; ceo was told.")
    assert playbook_of(svc).version == 3 and INITIALS not in playbook_of(svc).body
    assert (watched(svc).state, watched(svc).related) == ("retired", ("R2", "R3"))
    assert not [w for w in svc.runtime.service_evidence.watch("ceo", WEEK) if w.state == "kept" and w.id == "P4"]


def test_re_adding_it_or_editing_another_item_into_it_is_pb_watched_out(svc):
    """B2, design 8.6, 20 e2e (3): once the watch retired the planted rule, its text cannot come back as a rule, as a step with the same words, or as another
    live item edited into them, while the client's two rejections stand: PB-WATCHED-OUT names the item, the version, the rejections and the one question for
    the client; nothing is written. A circuit that is open is the owner's to use only with a criterion the client confirms afterwards (rule (c))."""
    server = build_server(svc, ROOT)
    c3 = planted(svc)
    retired_by_the_chain(svc, server, c3)
    assert playbook_of(svc).version == 3
    start = (
        "refused: this text is P4's text that the watch retired in v3, because the client rejected R2 and R3 on what it cited (R1, C3). It comes back only as "
        "the own words of a criterion the client confirms after that (rule (c)). Nothing was written. If you think the client wants it, send root (`send`) "
        'this question once: "Your rejections R2 and R3 retired this from how we deliver weekly-brief: Owners as initials only. Do you want it back from '
        'now on? If yes, please add it to the contract as a criterion."'
    )
    owner = build_server(svc, "ceo")
    attempts = (
        dict(op="add", kind="rule", then=INITIALS, evidence=[c3]),  # the same rule again
        dict(op="add", kind="step", text=INITIALS, evidence=[c3]),  # as a step (the rule's key is that of its `then`)
        dict(op="add", kind="rule", when="always", then=INITIALS, evidence=["R1", "R2"]),  # as a rule with a WHEN, on other evidence
        dict(op="edit", item="P3", text=INITIALS, evidence=[c3]),  # another live item edited into its words (B2)
    )
    for given in attempts:
        assert start in fails(owner, "revise_playbook", service=WEEK, reason="the client wants it", **given), given
        assert playbook_of(svc).version == 3 and "Check every claim." in playbook_of(svc).body  # a refusal writes nothing
    gone = watched(svc)
    assert (gone.state, gone.related) == ("retired", ("R2", "R3"))
    assert not [w for w in svc.runtime.service_evidence.watch("ceo", WEEK) if w.id == "P3" and w.state == "warning"]  # the refused edit carried nothing


def test_the_same_chain_on_an_edited_rule_restores_its_previous_text(svc):
    """G1(b), design 8.5, 20 e2e (3): a client-written step (v1's P3) is edited into the planted rule's words (a gated change, rule (c)); two related
    rejections retire that text, and the runtime puts the text P3 had before its watch back in its place (`restores`: 1), in the answering call."""
    server = build_server(svc, ROOT)
    svc.revise_playbook("ceo", WEEK, "first", "first draft", [], text=STEPS)
    c3 = confirmed_amendment(svc, INITIALS)
    edited = svc.revise_playbook("ceo", WEEK, "edit", "the client's rule", [c3], item="P3", text=INITIALS)
    assert (edited.version, edited.item, edited.admission.rule) == (2, "P3", "c")
    assert INITIALS in playbook_of(svc).body and "Check every claim." not in playbook_of(svc).body
    assert watched(svc, "P3").state == "new"
    warned = related(svc, server, delivered(svc, "again"), c3)
    assert warned.endswith("P3 is in warning now (ceo was told); one more related rejection retires it.")
    note = notes_titled(svc, "ceo", "playbook item P3 of weekly-brief: warning")[0].body
    assert "One more related rejection retires P3 and restores the text of v1." in note
    third = delivered(svc, "again and again")
    no = svc.feedback(ROOT, third.id, "reject", "Full names again.", source="human")
    reply = call(server, "define_service", owner="ceo", name=WEEK, add_acceptance=[FULL_NAMES], answers=no.id, about=c3, words="Yes, add it.")
    assert reply.endswith(
        "\nThe watch retired P3 of weekly-brief (playbook v3) because rejections R2 and R3 are related to it, and restored the text of v1; ceo was told."
    )
    after = playbook_of(svc)
    assert after.version == 3 and after.body == f"## Steps\n1. [P1] Search.\n2. [P2] Write.\n3. [P3] Check every claim."
    meta, _ = playbook_meta(svc)
    assert (meta["op"], meta["item"], meta["restores"], meta["related"]) == ("watch", "P3", 1, ["R2", "R3"])
    back = watched(svc, "P3")
    assert (back.state, back.related) == ("restored", ("R2", "R3"))  # live with a text the watch brought back


def test_a_failed_retire_write_reads_retire_due_and_is_retried_at_the_owners_next_op(svc):
    """Design 8.5 (Failure), 8.1, 20 e2e (3): the answer is the client's record and stays written when the runtime cannot write the retire. The reply says the
    watch could not retire the rule yet; every reader says `retire due`; nothing was written to the playbook. The owner's next op retries the due retire first
    (step 3 of 5.1), then does its own change, so the rule is gone before the move is."""
    server = build_server(svc, ROOT)
    c3 = planted(svc)
    related(svc, server, delivered(svc, "again"), c3)
    history = svc.dir("ceo") / "services" / WEEK / "history"
    (history / "PLAYBOOK.v2.md").mkdir(parents=True)  # the archive name of v2 is taken by a directory: the retire's write fails with an OSError
    third = delivered(svc, "again and again")
    no = svc.feedback(ROOT, third.id, "reject", "Full names again.", source="human")
    reply = call(server, "define_service", owner="ceo", name=WEEK, add_acceptance=[FULL_NAMES], answers=no.id, about=c3, words="Yes, add it.")
    assert reply.endswith(
        "\nThe watch could not retire P4 of weekly-brief yet (retire due: R2 and R3 are related); it retries at the owner's next change of the playbook or "
        "the next recorded answer."
    )
    assert playbook_of(svc).version == 2 and INITIALS in playbook_of(svc).body  # nothing written
    due = watched(svc)
    assert (due.state, due.related, due.retire_due) == ("warning", ("R2", "R3"), True)
    assert not notes_titled(svc, "ceo", "playbook of weekly-brief: the watch retired P4") and not notes_titled(svc, ROOT, "playbook of weekly-brief: the watch retired P4")
    assert "contract v2 -> v3" in reply and svc.runtime.service_catalog.criteria("ceo", WEEK)[-1].text == FULL_NAMES  # the answering version stays
    listed = next(x for x in svc.runtime.service_reports.services_text(ROOT).splitlines() if x.startswith("  playbook v"))
    assert "P4 warning (R2, R3; retire due)" in listed
    (history / "PLAYBOOK.v2.md").rmdir()  # the cause is gone
    moved = svc.revise_playbook("ceo", WEEK, "move", "read the sources first", [], item="P3", after="start")
    assert moved.version == 4  # v3 is the runtime's retire, v4 the owner's move
    meta3 = [m for _, m in svc.runtime.service_store.playbook_history("ceo", WEEK)][2]
    assert (meta3["version"], meta3["op"], meta3["by"], meta3["item"], meta3["related"]) == (3, "watch", "runtime (watch)", "P4", ["R2", "R3"])
    after = playbook_of(svc)
    assert after.version == 4 and INITIALS not in after.body and [i.id for i in after.items] == ["P3", "P1", "P2"]
    for addr in ("ceo", ROOT):  # the notes follow the retire that was written
        assert len(notes_titled(svc, addr, "playbook of weekly-brief: the watch retired P4")) == 1
    assert watched(svc).retire_due is False and watched(svc).state == "retired"


def test_g2b_end_of_stream_check_lists_no_unanswered_human_rejection(svc):
    """G2(b), design 13, 21.1: every human rejection has its `R<k>` and, within one request, the user's answer. While one waits, `amendment_basis` lists it
    (the study's end-of-stream check) and the next request of the service is refused (REQUEST-UNANSWERED, nothing sent); once it is answered, by a link or by
    an answering contract version alike, the check lists nothing and the request goes through."""
    server = build_server(svc, ROOT)
    c3 = planted(svc)

    def unanswered():
        return [r.assertion for r in svc.runtime.service_evidence.amendment_basis("ceo", WEEK).rejections if not r.answered]

    assert unanswered() == []  # R1 (the amendment's own) is answered by the version that added C3 and its link
    first = delivered(svc, "two")
    no = svc.feedback(ROOT, first.id, "reject", "Owners again.", source="human")
    assert unanswered() == ["R2"]  # the end-of-stream check lists it
    sent = len(svc.sent(ROOT))
    assert "refused: rejection R2 " in fails(server, "request", service=WEEK, inputs={"topic": "three"}) and len(svc.sent(ROOT)) == sent
    call(server, "feedback", task_id=first.id, verdict="reject", note="No lasting rule.", source="human", criterion=["none"], confirms=no.id)  # a link answers it
    assert unanswered() == []
    second = delivered(svc, "three")
    no = svc.feedback(ROOT, second.id, "reject", "Full names.", source="human")
    assert unanswered() == ["R3"]
    call(server, "define_service", owner="ceo", name=WEEK, add_acceptance=[FULL_NAMES], answers=no.id, about=c3, words="Yes, add it.")  # a version answers it
    assert unanswered() == []
    assert [r.assertion for r in svc.runtime.service_evidence.amendment_basis("ceo", WEEK).rejections] == ["R1", "R2", "R3"]  # each has its R<k>
    assert request(svc, "four").type == "task"  # nothing is due: the request is sent


WEEKS = "Names the week it covers"  # a correct rule: the own words of a criterion the client confirmed and never reverses


def correct_rule(org):
    """ceo's v1 and a correct (c) rule (P4: the words of a confirmed criterion, WEEKS); its watch starts ``new``. Returns the criterion's id."""
    org.revise_playbook("ceo", WEEK, "first", "first draft", [], text=STEPS)
    cid = confirmed_amendment(org, WEEKS)
    org.revise_playbook("ceo", WEEK, "add", "the client's rule", [cid], kind="rule", then=WEEKS)
    return cid


def answered_none(org, server, task, note="Too long."):
    """The client rejects ``task`` and answers the one question: no lasting rule. Returns the rejection's id."""
    no = org.feedback(ROOT, task.id, "reject", note, source="human")
    call(server, "feedback", task_id=task.id, verdict="reject", note="No, a one-off.", source="human", criterion=["none"], confirms=no.id)
    return no.id


def test_a_correct_c_rule_reaches_kept_at_k(svc):
    """G1(a), design 8.1, 20 e2e (4): a correct rule is `new` with 0 of 3 clean cases; each judged case without a related rejection counts (a rejection the
    client answers 'no lasting rule' leaves the case clean); a delivery with no verdict yet, or a rejection with no answer, holds it `new` and says what it
    waits for; at the third clean case it is `kept`, and no reader lists it as watched any more."""
    server = build_server(svc, ROOT)
    correct_rule(svc)
    rt = svc.runtime
    start = watched(svc)
    assert (start.state, start.k, start.clean, start.waiting) == ("new", 3, 0, 0)
    accepted(svc, "one")
    one = watched(svc)
    assert (one.state, one.clean, one.waiting) == ("new", 1, 0)
    second = delivered(svc, "two")  # delivered, not yet judged
    assert (watched(svc).state, watched(svc).clean, watched(svc).waiting) == ("new", 1, 1)
    no = svc.feedback(ROOT, second.id, "reject", "Too long.", source="human")  # judged, but the rejection has no answer
    held = watched(svc)
    assert (held.state, held.clean, held.pending) == ("new", 1, ("R2",))
    listed = next(x for x in rt.service_reports.services_text(ROOT).splitlines() if x.startswith("  playbook v"))
    assert listed.endswith("; 4 items (1 rule); watched: P4 new (1 of 3 clean cases, k 3; waiting for the user's answer to R2)")
    call(server, "feedback", task_id=second.id, verdict="reject", note="No, a one-off.", source="human", criterion=["none"], confirms=no.id)
    answered = watched(svc)
    assert (answered.state, answered.clean, answered.pending, answered.related) == ("new", 2, (), ())
    accepted(svc, "three")
    kept = watched(svc)
    assert (kept.state, kept.clean, kept.related, kept.retire_due) == ("kept", 3, (), False)
    assert playbook_of(svc).version == 2 and WEEKS in playbook_of(svc).body  # a kept rule is untouched
    listed = next(x for x in rt.service_reports.services_text(ROOT).splitlines() if x.startswith("  playbook v"))
    assert listed.endswith("; 4 items (1 rule), none watched")  # nothing left to watch
    record = [(w["item"], w["state"], w["clean"], w["related"]) for w in rt.quality_report.quality_data(WEEK)["services"][0]["watch"] if w["item"] == "P4"]
    assert record == [("P4", "kept", 3, [])]
    accepted(svc, "four")
    assert watched(svc).state == "kept"  # later cases change nothing


def test_a_corrected_link_after_k_warns_it_and_a_second_retires_it(svc):
    """Design 8.1 (the one exception to monotonicity; row xix), 8.2, 20 e2e (4): the rule reached `kept` over two rejections the client answered 'no lasting
    rule'. Her corrected link (a second link on the same rejection, which 0a.2 lets decide) makes R2 about the rule's criterion: the rule is `warning` again
    (kept -> warning, the exception); a second corrected link, on R3, retires it in that call."""
    server = build_server(svc, ROOT)
    cid = correct_rule(svc)
    accepted(svc, "one")
    first = delivered(svc, "two")
    r2 = answered_none(svc, server, first)
    second = delivered(svc, "three")
    r3 = answered_none(svc, server, second, "Still too long.")
    kept = watched(svc)
    assert (kept.state, kept.clean, kept.related) == ("kept", 3, ())
    corrected = call(server, "feedback", task_id=first.id, verdict="reject", note="I meant the week, yes.", source="human", criterion=[cid], confirms=r2)
    assert corrected.endswith("\n" + WARNED)  # kept -> warning
    again = watched(svc)
    assert (again.state, again.related, again.retire_due) == ("warning", ("R2",), False)
    (told,) = notes_titled(svc, "ceo", "playbook item P4 of weekly-brief: warning")
    assert "Rejection R2 (case " in told.body and playbook_of(svc).version == 2
    retired = call(server, "feedback", task_id=second.id, verdict="reject", note="The week too.", source="human", criterion=[cid], confirms=r3)
    assert retired.endswith("\n" + RETIRED)  # the runtime retires it in the call that records the second corrected link
    assert playbook_of(svc).version == 3 and WEEKS not in playbook_of(svc).body
    gone = watched(svc)
    assert (gone.state, gone.related, gone.retire_due) == ("retired", ("R2", "R3"), False)
