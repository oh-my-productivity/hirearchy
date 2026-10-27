"""The marks of the timeline that the stored files give: contract versions, playbook versions, top-ups, and the words of every mark (design 7).

The tests build the stored contract versions (``(version, frontmatter, body)``, as ``ServiceStore.versions`` lists them), the playbook versions, the
verdicts with their link notes and the cases by hand; the criteria are numbered by ``services.number_criteria`` from the same versions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import JsonObject, Message, link_ids, msg_time, verdict_tier
from hirearchy.reflection import Case, CharterMark, ModelMark, TopUp, TopUps, Verdict
from hirearchy.reflection._marks import contract_marks, playbook_marks, top_up_marks
from hirearchy.services import Criterion, Playbook, number_criteria

OWNER = "lead"
T0 = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def ident(n: int, sender: str = "root") -> str:
    """The id of the message sent ``n`` seconds after the origin (so ids order like ``n``)."""
    return f"20261021T15{n // 60:02d}{n % 60:02d}000000-{sender.replace('/', '-')}-{n:04d}"


def contract(version: int, acceptance: list[str], *, by: str = "root", answers: str = "", initiated: str = "", at: int | None = None) -> tuple[int, JsonObject, str]:
    meta: JsonObject = {
        "name": "weekly", "version": version, "defined_by": by, "defined": (T0 + timedelta(minutes=at if at is not None else version)).isoformat(),
        "acceptance": acceptance, "budget": 15,
    }
    if answers:
        meta["answers"] = answers
    if initiated:
        meta["initiated"] = initiated
    return version, meta, ""


def task(n: int) -> Message:
    return Message(sender="root", to=OWNER, type="task", body="b", title=f"t{n}", id=ident(n), service="weekly")


def verdict(n: int, *, links: tuple[str, ...] = (), link_source: str | None = "human", on: Message | None = None, kind: str = "reject") -> Verdict:
    """The verdict ``kind`` sent at second ``n`` with one link note naming ``links`` (source ``link_source``) sent a second later."""
    on = on or task(1)
    note = Message(sender="root", to=OWNER, type="note", body="no", id=ident(n), reply_to=on.id, feedback=kind, source="human")
    link_notes: list[Message] = []
    confirmed: tuple[str, ...] = ()
    tier = ""
    if links:
        link = Message(sender="root", to=OWNER, type="note", body="link", id=ident(n + 1), reply_to=note.id, criterion=", ".join(links), source=link_source)
        link_notes.append(link)
        tier = verdict_tier(link)
        confirmed = tuple(x for x in link_ids(link) if x.startswith("C")) if tier == "human" else ()
    return Verdict(kind, "no", msg_time(note), on.id, 0, note, tier="human", links=links, links_tier=tier, confirmed=confirmed, link_notes=tuple(link_notes))


def case(*verdicts: Verdict, top_ups: tuple[TopUp, ...] = (), name: str = "") -> Case:
    t = task(1)
    return Case(
        id=name or t.id, service="weekly", owner=OWNER, tasks=[t], result=None, state="open", playbook=0, used=0, reworks=0, budget=15, runs=0, lessons=[],
        verdicts=list(verdicts), started=None, finished=None, top_ups=TopUps(top_ups),
    )


def marks(versions: list[tuple[int, JsonObject, str]], *cases: Case):  # type: ignore[no-untyped-def]
    return contract_marks(OWNER, "weekly", versions, list(cases))


# ------------------------------------------------------------------------------------------------------------------------ contract marks


def test_v1_lists_its_ids() -> None:
    (mark,) = marks([contract(1, ["A", "B", "C"])])
    assert (mark.version, mark.by, mark.adds, mark.removes, mark.basis, mark.parts) == (1, "root", ("C1", "C2", "C3"), (), "first", ())
    assert mark.when == T0 + timedelta(minutes=1)
    assert mark.text == "contract v1 (C1, C2, C3)"


def test_a_later_version_adds_then_removes_in_amendment_ids_order() -> None:
    # v2 lists its new texts E, D (C4, C5) and drops A and C; v3 brings A back (it keeps its first id, C1) and drops D
    versions = [contract(1, ["A", "B", "C"]), contract(2, ["E", "B", "D"]), contract(3, ["A", "B", "E"])]
    _, v2, v3 = marks(versions)
    assert (v2.adds, v2.removes) == (("C4", "C5"), ("C1", "C3"))  # the added ids in the order of the version's list, the removed in the version before's
    assert (v3.adds, v3.removes) == (("C1",), ("C5",))
    assert v2.text.startswith("contract v2 (root): adds C4, C5; removes C1, C3")


def test_criteria_unchanged_when_nothing_is_added_or_removed() -> None:
    _, v2 = marks([contract(1, ["A", "B"]), contract(2, ["A", "B"])])
    assert (v2.adds, v2.removes) == ((), ())
    assert v2.text.startswith("contract v2 (root): criteria unchanged")


def test_an_answers_version_marks_each_part_confirmed_with_its_link() -> None:
    rejection = verdict(70, links=("C3",))
    link = rejection.link_notes[0].id
    _, v2 = marks([contract(1, ["A", "B"]), contract(2, ["A", "B", "C"], answers=rejection.message.id)], case(rejection))
    assert (v2.basis, v2.answers, v2.parts) == ("answers", "R1", (("C3", link),))
    assert v2.text == f"contract v2 (root): adds C3: the user's answer to R1: C3 confirmed (link {link})"


def test_a_removal_only_answering_version_marks_its_removed_id_confirmed_with_the_link() -> None:
    rejection = verdict(70, links=("C3",))
    link = rejection.link_notes[0].id
    _, v2 = marks([contract(1, ["A", "B", "C"]), contract(2, ["A", "B"], answers=rejection.message.id)], case(rejection))
    assert (v2.adds, v2.removes, v2.parts) == ((), ("C3",), (("C3", link),))
    assert v2.text == f"contract v2 (root): removes C3: the user's answer to R1: C3 confirmed (link {link})"


def test_a_removal_only_answering_version_without_its_link_reads_not_confirmed() -> None:
    rejection = verdict(70)  # the product's link write failed after the contract (0a.2 DR-30)
    _, v2 = marks([contract(1, ["A", "B", "C"]), contract(2, ["A", "B"], answers=rejection.message.id)], case(rejection))
    assert v2.parts == (("C3", ""),)
    assert v2.text == "contract v2 (root): removes C3: the user's answer to R1: C3 not confirmed (the link was not recorded)"


def test_the_answers_basis_joins_its_parts_with_a_colon_then_commas() -> None:
    rejection = verdict(70, links=("C4",))
    link = rejection.link_notes[0].id
    versions = [contract(1, ["A", "B"]), contract(2, ["A", "B", "C", "D"], answers=rejection.message.id)]
    _, v2 = marks(versions, case(rejection))
    assert v2.parts == (("C3", ""), ("C4", link))  # one part per id, in the order of the added ids
    assert v2.text == f"contract v2 (root): adds C3, C4: the user's answer to R1: C3 not confirmed (the link was not recorded), C4 confirmed (link {link})"


def test_confirmed_and_not_confirmed_cover_the_ids_the_parts_name() -> None:
    rejection = verdict(70, links=("C4",))
    link = rejection.link_notes[0].id
    added = [contract(1, ["A", "B"]), contract(2, ["A", "B", "C", "D"], answers=rejection.message.id)]
    removed = [contract(1, ["A", "B", "C"]), contract(2, ["A"], answers=rejection.message.id)]
    _, with_adds = marks(added, case(rejection))
    _, with_removes = marks(removed, case(rejection))
    assert (with_adds.confirmed, with_adds.not_confirmed) == ((("C4", link),), ("C3",))
    assert [i for i, _ in with_adds.parts] == ["C3", "C4"] == list(with_adds.adds)  # the added ids when it adds any
    assert [i for i, _ in with_removes.parts] == list(with_removes.removes) == ["C2", "C3"]  # else the removed ones, in the order of the version before


def test_only_the_human_link_on_the_answered_rejection_confirms_an_answered_version() -> None:
    answered, other = verdict(70, links=("C3",)), verdict(90, links=("C3",), on=task(2))
    relayed = verdict(110, links=("C3",), link_source="relayed", on=task(3))
    versions = [contract(1, ["A", "B"]), contract(2, ["A", "B", "C"], answers=answered.message.id)]
    _, none_of_them = marks(versions, case(other, relayed))
    assert none_of_them.parts == (("C3", ""),)  # a human link on another rejection, and a relayed one, are not the user's yes to this answer
    _, found = marks(versions, case(other, answered, relayed))
    assert found.parts == (("C3", answered.link_notes[0].id),)


def test_a_user_initiated_version_says_never_admit() -> None:
    link = verdict(70, links=("C3",))
    _, v2 = marks([contract(1, ["A", "B"]), contract(2, ["A", "B", "C"], initiated="user")], case(link))
    assert (v2.basis, v2.parts) == ("user", ())
    assert v2.text == "contract v2 (root): adds C3: asked for by the user on their own: C3 user-initiated (never admit a playbook revision)"


def test_a_legacy_root_version_marks_confirmed_by_any_human_link_else_not_confirmed() -> None:
    first, second = verdict(70, links=("C4",)), verdict(90, links=("C5",), link_source="relayed", on=task(2))
    versions = [contract(1, ["A", "B"]), contract(2, ["A", "B", "C"]), contract(3, ["A", "B", "C", "D", "E"])]
    _, v2, v3 = marks(versions, case(first, second))
    assert (v2.basis, v2.parts) == ("legacy", (("C3", ""),))
    assert v2.text == "contract v2 (root): adds C3: not confirmed"  # none of its ids is confirmed: the mark ends so
    assert v3.parts == (("C4", first.link_notes[0].id), ("C5", ""))  # the relayed link confirms nothing
    assert v3.text == f"contract v3 (root): adds C4, C5: C4 confirmed (link {first.link_notes[0].id}), C5 not confirmed"


def test_an_agent_version_says_hypotheses() -> None:
    _, v2 = marks([contract(1, ["A"], by="ceo"), contract(2, ["A", "B"], by="ceo")])
    assert (v2.basis, v2.by, v2.parts) == ("agent", "ceo", ())
    assert v2.text == "contract v2 (ceo): adds C2: by ceo, an agent client (its verdicts are hypotheses)"


def test_a_version_without_a_time_has_none_and_the_marks_follow_the_stored_order() -> None:
    meta: JsonObject = {"version": 1, "acceptance": ["A"]}
    (mark,) = marks([(1, meta, "")])
    assert mark.when is None and mark.by == "" and mark.adds == ("C1",)


# ------------------------------------------------------------------------------------------------------------------------ playbook marks


def criteria(*texts: str) -> list[Criterion]:
    """The criteria of a root contract that has had these texts (C1 for the first)."""
    return number_criteria([(1, "root", list(texts))])


def playbook(version: int, body: str, *, by: str = "lead", admitted: str = "", evidence: tuple[str, ...] = (), at: int | None = None) -> Playbook:
    return Playbook(
        version=version, revised=T0 + timedelta(minutes=at if at is not None else 10 + version), by=by, reason="because", body=body, evidence=list(evidence),
        admitted=admitted,
    )


def pmarks(playbooks: list[Playbook], crit: list[Criterion] | None = None, *cases: Case):  # type: ignore[no-untyped-def]
    return playbook_marks(OWNER, playbooks, crit or [], list(cases))


def test_playbook_c_counts_own_words_against_the_cited_criteria() -> None:
    crit = criteria("Alpha is done", "Beta is done", "Summary line first")
    before = "Do the work.\nCheck twice."
    after = "Do the work.\nCheck twice.\n- C3: Summary line first\nSign with the date"
    _, v2 = pmarks([playbook(1, before, admitted="first"), playbook(2, after, admitted="c", evidence=("C3",))], crit)
    assert (v2.version, v2.by, v2.basis, v2.changed, v2.removed) == (2, "lead", "c", 2, 0)
    assert (v2.own_words, v2.beyond, v2.tagged, v2.untagged) == (1, 1, None, None)
    assert v2.cited == (("C3", "Summary line first"),) and v2.evidence == ("C3",) and v2.evidence_other == 0
    assert v2.text == "playbook v2 (lead): admitted (c) on C3: 2 changed line(s): 1 the cited criteria's own words, 1 beyond them"


def test_a_cited_link_note_counts_as_its_criterion() -> None:
    crit = criteria("Alpha is done", "Summary line first")
    rejection = verdict(70, links=("C2",))
    link = rejection.link_notes[0].id
    relayed = verdict(90, links=("C1",), link_source="relayed", on=task(2))
    _, v2 = pmarks(
        [playbook(1, "x", admitted="first"), playbook(2, "x\nSummary line first (C2)\nelse", admitted="c", evidence=(link, relayed.link_notes[0].id))],
        crit, case(rejection, relayed),
    )
    assert v2.cited == (("C2", "Summary line first"),)  # the human link note stands for C2; the relayed one for nothing
    assert (v2.own_words, v2.beyond) == (1, 1)
    assert v2.evidence == (link, relayed.link_notes[0].id)


def test_playbook_b_counts_tagged_and_untagged_lines() -> None:
    before = "Do the work."
    after = "Do the work.\n- R1: always check dates\n- Remember C4 limits\nBe nice"
    _, v2 = pmarks([playbook(1, before, admitted="first"), playbook(2, after, admitted="b", evidence=("R1", "R2"))])
    assert (v2.basis, v2.changed, v2.tagged, v2.untagged, v2.own_words, v2.beyond) == ("b", 3, 2, 1, None, None)
    assert v2.text == "playbook v2 (lead): admitted (b) on R1, R2: 3 changed line(s): 2 tagged with an id, 1 untagged"


def test_first_restore_client_and_legacy_playbook_marks() -> None:
    versions = [
        playbook(1, "Original.", by="root", at=1),  # the client wrote it: no admission needed
        playbook(2, "Changed.", admitted="first"),
        playbook(3, "Changed again.", admitted="c", evidence=("C1",)),
        playbook(4, "Changed.", admitted="restore"),  # restores v2 unchanged
        playbook(5, "Edited by the owner before the evidence gate."),  # no admission recorded
    ]
    v1, v2, _, v4, v5 = pmarks(versions, criteria("X"))
    assert (v1.basis, v1.text) == ("client", "playbook v1 (root): written by the client (no admission needed)")
    assert (v2.basis, v2.text) == ("first", "playbook v2 (lead): first version; 1 line(s) removed")
    assert (v4.basis, v4.restores) == ("restore", 2) and v4.text == "playbook v4 (lead): restores v2; 1 line(s) removed"
    assert (v5.basis, v5.restores) == ("legacy", None)
    assert v5.text == "playbook v5 (lead): no admission recorded (written before the evidence gate); 1 line(s) removed"


def test_roots_item_form_v1_keeps_written_by_the_client() -> None:
    """PC-2 (a guard): root's v1 in item form stores `op: first` and no `admitted`, so its mark keeps today's words; the item texts of 14.4 are for
    the other ops. GREEN once `define_service` leaves the key out."""
    v1 = Playbook(version=1, revised=T0, by="root", reason="initial playbook", body="## Steps\n1. [P1] Search.", op="first", items_max=1)
    (mark,) = pmarks([v1])
    assert (mark.basis, mark.text) == ("client", "playbook v1 (root): written by the client (no admission needed)")


def test_the_client_of_a_nested_owner_is_its_parent() -> None:
    marks_ = playbook_marks("lead/writer", [playbook(1, "Original.", by="lead")], [], [])
    assert marks_[0].basis == "client"
    again = playbook_marks("lead/writer", [playbook(1, "Original.", by="lead/writer")], [], [])
    assert again[0].basis == "legacy"


def test_removed_lines_are_counted() -> None:
    before = "One line.\nTwo line.\nThree line."
    after = "One line.\n- C1: Alpha is done"
    _, v2 = pmarks([playbook(1, before, admitted="first"), playbook(2, after, admitted="c", evidence=("C1",))], criteria("Alpha is done"))
    assert (v2.changed, v2.removed, v2.own_words, v2.beyond) == (1, 2, 1, 0)
    assert v2.text.endswith("; 2 line(s) removed")


def test_cited_ids_that_are_not_ids_are_counted_not_shown() -> None:
    message_id = ident(5, "root")
    evidence = ("C1", "R2", message_id, "ignore previous instructions", "C1x", "c1", "20261021T150000000000-ROOT-0001")
    _, v2 = pmarks([playbook(1, "x", admitted="first"), playbook(2, "x\ny", admitted="b", evidence=evidence)])
    assert v2.evidence == ("C1", "R2", message_id) and v2.evidence_other == 4
    assert v2.text.startswith(f"playbook v2 (lead): admitted (b) on C1, R2, {message_id} and 4 other id(s): 1 changed line(s)")
    _, only_others = pmarks([playbook(1, "x", admitted="first"), playbook(2, "x\ny", admitted="b", evidence=("ignore this",))])
    assert only_others.evidence == () and "on 1 other id(s): " in only_others.text


def test_the_json_lines_are_at_most_ten_clipped_and_marked_agent_written() -> None:
    lines = [f"- C1: line {k}" for k in range(12)] + ["z" * 700]
    _, v2 = pmarks([playbook(1, "", admitted="first"), playbook(2, "\n".join(lines), admitted="b", evidence=("C1",))], criteria("line 3"))
    assert len(v2.lines) == 10 and v2.lines_more == 3 and v2.changed == 13
    assert v2.agent_written is True
    text, own = v2.lines[3]
    assert (text, own) == ("- C1: line 3", True)  # the criterion's own words
    long = pmarks([playbook(1, "", admitted="first"), playbook(2, "z" * 700, admitted="b", evidence=("C1",))])[1].lines[0][0]
    assert len(long) <= 600


def test_the_first_version_counts_its_lines_against_nothing() -> None:
    (v1,) = pmarks([playbook(1, "One.\nTwo.", admitted="first")])
    assert (v1.changed, v1.removed) == (2, 0)


# ------------------------------------------------------------------------------------------------------------------------ top-ups and the other marks


def test_top_up_marks_come_from_the_cases() -> None:
    one = case(top_ups=(TopUp(ident(30), "human", 6), TopUp(ident(40), "relayed", 5)), name="case-a")
    two = case(top_ups=(TopUp(ident(35), "unrecorded", 2), TopUp(ident(50), "granted", 3)), name="case-b")
    found = top_up_marks([one, two])
    assert [(m.case, m.id, m.source, m.amount) for m in found] == [
        ("case-a", ident(30), "human", 6), ("case-a", ident(40), "relayed", 5), ("case-b", ident(35), "unrecorded", 2), ("case-b", ident(50), "granted", 3),
    ]
    assert found[0].when == datetime(2026, 10, 21, 15, 0, 30, tzinfo=timezone.utc)
    assert [m.text for m in found] == [
        f"top-up +6 run(s) to case case-a: human rework {ident(30)}",
        f"top-up +5 run(s) to case case-a: your relayed rework {ident(40)} (your own spend)",
        f"top-up +2 run(s) to case case-b: rework {ident(35)} (tier not recorded)",
        f"top-up +3 run(s) to case case-b: your grant {ident(50)}",
    ]


def test_a_charter_and_a_model_mark_say_what_changed() -> None:
    charter = CharterMark("lead/writer", COMMIT, T0)
    assert charter.text == "lead/writer: charter edited (commit 0123456789ab)"
    assert ModelMark("lead", "model", "", "claude-opus-5.5", COMMIT, T0).text == 'lead: model the org default -> "claude-opus-5.5"'
    assert ModelMark("ORG.md", "default_model", "claude-sonnet-5.5", "claude-opus-5.5", COMMIT, T0).text == (
        'ORG.md: default model "claude-sonnet-5.5" -> "claude-opus-5.5"'
    )
    assert ModelMark("ORG.md", "effort", "high", "xhigh", COMMIT, T0).text == 'ORG.md: effort "high" -> "xhigh"'
    assert ModelMark("lead", "model", "bad\nname", "", COMMIT, T0).text == 'lead: model "bad\\nname" -> the org default'  # a model name is never shown raw


@pytest.mark.parametrize("kind", ["human", "relayed", "unrecorded", "granted"])
def test_every_top_up_source_has_words(kind: str) -> None:
    (mark,) = top_up_marks([case(top_ups=(TopUp(ident(30), kind, 1),))])
    assert mark.text.startswith("top-up +1 run(s) to case ") and ident(30) in mark.text
