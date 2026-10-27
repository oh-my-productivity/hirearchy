"""``define_service(answers=, about=, words=)``: root records the user's answer to a rejection (or a change they asked for on their own).

Design 5.2 steps 1-3 and 4 (the write order), 5.4 (what is recorded), 5.7 (the replies), 12 (the link that cannot be written). The gate's
rule that every root amendment carries words (P2-UNRATED, P2-NEEDS-WORDS, P2-OPEN-REJECTION) is another commit's: here a call without the new
arguments is what it was. The rejections the definer is told about are the test's (``Basis``): ``reflection`` has the real record."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import Message, OrgError
from hirearchy.services import LINK_HEADER, AmendmentBasis, Rejection
from hirearchy.services._protocols import LinkNotes
from hirearchy.services.testing import AdmittingServiceEvidence, FlakyDelivery, FlakyLinkNotes, ServicesWorld, fs_world, memory_world

from ._support import amend, answer, define, populated, write_version
from ._support import request as ask

SERVICE = "weekly-brief"
NOTE = "Sam's CI item says before Friday, so that has a date. And always start with a Summary."
YES = "Yes, add it."
RULE = "The memo starts with a Summary line"


class Basis(AdmittingServiceEvidence):
    """A gate whose record of the service is what the test says: its rejections, its deliveries without a verdict, or a failure to read it."""

    def __init__(self) -> None:
        super().__init__()
        self.rejections: list[Rejection] = []
        self.unrated: tuple[str, ...] = ()
        self.error: Exception | None = None

    def amendment_basis(self, owner: str, service: str) -> AmendmentBasis:
        if self.error is not None:
            raise self.error
        return AmendmentBasis(tuple(self.rejections), self.unrated)


class SpyLinks(LinkNotes):
    """A link writer that records what the world looked like when it was asked, then writes through ``inner``."""

    def __init__(self, inner: LinkNotes, look: Any) -> None:
        self._inner = inner
        self._look = look
        self.calls: list[tuple[str, str, str, str, tuple[str, ...], str]] = []
        self.seen: list[Any] = []

    def write(self, actor: str, owner: str, title: str, rejection: str, ids: Any, words: str, source: str | None = "human") -> Message:
        self.calls.append((actor, owner, title, rejection, tuple(ids), words))
        self.seen.append(self._look())
        return self._inner.write(actor, owner, title, rejection, ids, words, source)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def factory(request: pytest.FixtureRequest) -> Any:
    return request.param


def build(factory: Any, tmp_path: Path, **kw: Any) -> tuple[ServicesWorld, Basis]:
    """The world of an implementation with ``ceo`` offering ``weekly-brief`` (C1 "At most 600 words", C2 "Every factual claim has a source URL")."""
    basis = Basis()
    w = populated(factory(tmp_path, basis, **kw))
    define(w)
    return w, basis


def ask_after(w: ServicesWorld, basis: Basis, topic: str = "ai") -> Message:
    """A request that clause 2 lets through (design 13.1): a fresh one, or, while a rejection of the record has no answer, a rework of that rejection's
    task (a rework is never held). These tests are about the definer and the retirement, which need rejections that stay unanswered."""
    waiting = [r for r in basis.rejections if not r.answered]
    return ask(w, topic, revises=waiting[0].task, source="human") if waiting else ask(w, topic)


def reject(w: ServicesWorld, basis: Basis, words: str = NOTE, topic: str = "ai") -> Rejection:
    """The user rejects a fresh delivery (a rework of the first unanswered rejection's task, after one); the world's record then lists the rejection
    (unanswered)."""
    task = ask_after(w, basis, topic)
    answer(w, task)
    note = w.commands.feedback("root", task.id, "reject", words, source="human")
    found = Rejection(note.id, f"R{len(basis.rejections) + 1}", task.id, task.title, tuple(x.assertion for x in basis.rejections), words, "")
    basis.rejections.append(found)
    return found


def refusal(w: ServicesWorld, **kw: Any) -> str:
    with pytest.raises(OrgError) as info:
        amend(w, **kw)
    return str(info.value)


def version(w: ServicesWorld, name: str = SERVICE, owner: str = "ceo") -> int:
    found = w.store.read_contract(owner, name)
    assert found is not None
    return int(str(found[0]["version"]))


def meta(w: ServicesWorld, kind: str = "SERVICE") -> dict[str, Any]:
    (*_, (_, current, _)) = w.store.versions("ceo", SERVICE, kind)
    return dict(current)


def inbox(w: ServicesWorld) -> list[Message]:
    return sorted(w.d.inbox("ceo"), key=lambda m: m.id)


def notes_of_the_runtime(w: ServicesWorld) -> list[Message]:
    """The amendment notes the owner got (the requests and the verdicts in its inbox are root's)."""
    return [m for m in inbox(w) if m.sender == "runtime"]


# ------------------------------------------------------------------------------ steps 1 and 2: who, and on what


def test_answers_about_words_from_an_agent_are_root_only(factory: Any, tmp_path: Path) -> None:
    w, _ = build(factory, tmp_path)
    define(w, owner="ceo/eng", name="inner", actor="ceo")
    for given in ({"answers": "x"}, {"about": "C1"}, {"words": YES}, {"answers": "x", "about": "C1", "words": YES}):
        text = refusal(w, owner="ceo/eng", name="inner", actor="ceo", add_acceptance=["Brief"], **given)
        assert text == (
            "refused: answers, about and words are root's: they record the human client's answer. An agent client amends its report's contract "
            "without them. Nothing was written."
        )
    assert version(w, "inner", "ceo/eng") == 1
    amend(w, owner="ceo/eng", name="inner", actor="ceo", add_acceptance=["Brief"])  # an agent client amends as before
    assert version(w, "inner", "ceo/eng") == 2


def test_answers_on_a_first_definition_or_a_call_that_changes_no_criterion_is_not_an_amendment(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    reject(w, basis)
    not_an_amendment = (
        "refused: answers, about and words record the user's answer to a change of the acceptance criteria; this call changes none. Pass them "
        "only with acceptance, add_acceptance or remove_acceptance on an existing service (CLI: --acceptance, --add-acceptance, --remove-acceptance). "
        "Nothing was written."
    )
    with pytest.raises(OrgError) as first:
        define(w, name="fresh", words=YES)  # a first definition
    assert str(first.value) == not_an_amendment
    assert w.catalog.read_contract("ceo", "fresh") is None
    assert refusal(w, budget=12, words=YES) == not_an_amendment  # a change, but not of the criteria
    assert refusal(w, acceptance=["Every factual claim has a source URL", "At most 600 words"], words=YES) == not_an_amendment  # a pure reordering
    assert refusal(w, budget=10, words=YES).startswith("no change: the amendment leaves the contract of `weekly-brief` exactly as it is (v1)")
    assert version(w) == 1 and notes_of_the_runtime(w) == []


# ------------------------------------------------------------------------------ step 3: the values given


def test_answers_without_about_or_about_without_answers_is_refused(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    pair = (
        "refused: answers and about go together: answers=<the rejection's message id>, about=<the C or R id your question named> "
        "(CLI: --answers, --about). Nothing was written."
    )
    assert refusal(w, add_acceptance=[RULE], answers=found.note, words=YES) == pair
    assert refusal(w, add_acceptance=[RULE], about="C1", words=YES) == pair
    assert version(w) == 1


def test_words_over_1000_characters_is_refused(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    long = "x" * 1001
    text = "refused: words (CLI: --words) is 1001 characters; the limit is 1000: the user's answer, verbatim, not a summary. Nothing was written."
    assert refusal(w, add_acceptance=[RULE], words=long) == text
    assert refusal(w, add_acceptance=[RULE], answers=found.note, about="C1", words=long) == text
    amend(w, add_acceptance=[RULE], answers=found.note, about="C1", words=" " + "x" * 1000 + " ")  # the limit is on the stripped words: 1000 is fine
    assert version(w) == 2


@pytest.mark.parametrize("error", [OrgError("the cases cannot be read"), OSError("disk")], ids=["OrgError", "OSError"])
def test_an_unreadable_basis_fails_closed(factory: Any, tmp_path: Path, error: Exception) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    basis.error = error
    for given in ({"words": YES}, {"answers": found.note, "about": "C1", "words": YES}):
        assert refusal(w, add_acceptance=[RULE], **given) == (
            f"refused: the record of `weekly-brief` cannot be read ({error}), so the contract was not changed. Try again; if it persists, tell the user."
        )
    assert version(w) == 1 and notes_of_the_runtime(w) == []


def test_answers_that_is_not_a_human_rejection_of_this_service_is_refused(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    none_yet = (
        "refused: answers (CLI: --answers) must be the message id of a rejection you recorded with feedback(..., source=\"human\") "
        "(CLI: hirearchy feedback <task id> reject --note ...) on a request of `weekly-brief`: 20261018T100000000012-root-0004. "
        "Its rejections: none yet. Nothing was written."
    )
    assert refusal(w, add_acceptance=[RULE], answers="20261018T100000000012-root-0004", about="C1", words=YES) == none_yet
    first, second = reject(w, basis), reject(w, basis, "Another one entirely, please.", "b")
    task = ask_after(w, basis, "c")
    answer(w, task)
    accepted = w.commands.feedback("root", task.id, "accept", source="human")  # an accept is no rejection
    listed = f"R1 (message {first.note}), R2 (message {second.note})"
    for wrong in (accepted.id, "R1"):
        assert refusal(w, add_acceptance=[RULE], answers=wrong, about="C1", words=YES) == (
            "refused: answers (CLI: --answers) must be the message id of a rejection you recorded with feedback(..., source=\"human\") "
            f"(CLI: hirearchy feedback <task id> reject --note ...) on a request of `weekly-brief`: {wrong}. Its rejections: {listed}. Nothing was written."
        )
    assert version(w) == 1


def test_a_second_answer_to_one_rejection_is_refused(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    again = (
        "refused: rejection R1 (message {note}) already has its answer ({how}): one rejection gets one answer. A new lasting rule needs a new "
        "rejection and its question, or words alone (CLI: --words) when the user asks for it on their own. Nothing was written."
    )
    # by link note: the record says the rejection has one
    basis.rejections[0] = replace(found, answered="20261018T100000000099-root-0001")
    assert refusal(w, add_acceptance=[RULE], answers=found.note, about="C1", words=YES) == again.format(note=found.note, how="link note 20261018T100000000099-root-0001")
    # by contract version: a version of the service says it answers it
    basis.rejections[0] = found
    amend(w, add_acceptance=[RULE], answers=found.note, about="C1", words=YES)
    assert version(w) == 2
    assert refusal(w, add_acceptance=["Another rule"], answers=found.note, about="C1", words="Yes, that too.") == again.format(note=found.note, how="contract v2")
    assert version(w) == 2


def test_about_must_name_a_criterion_in_force_or_an_earlier_rejection(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    first = reject(w, basis, "Too long.")
    second = reject(w, basis, NOTE, "b")
    w.d.clock.advance(1)
    write_version(w, 2, ["At most 600 words", "Every factual claim has a source URL", "Cite at most five sources"], initiated="user", words="Few sources.")  # C3, after both
    refused_about = (
        "refused: about (CLI: --about) must be the id your one question named: a criterion of contract v1, in force when R2 was recorded (C1, C2), "
        "or an earlier rejection (R1): {about}. A criterion this change creates cannot be what the question was about. Nothing was written."
    )
    for wrong in ("C3", "C9", "R2", "R7", "nonsense"):  # C3 did not exist when R2 was recorded; R2 is the rejection itself
        assert refusal(w, add_acceptance=[RULE], answers=second.note, about=wrong, words=YES) == refused_about.format(about=wrong.upper())
    assert version(w) == 2
    for right in ("c1", "C2", "r1"):  # case-insensitive; a criterion in force then, or an earlier rejection
        (tmp_path / f"again-{right}").mkdir()
        w2, b2 = build(factory, tmp_path / f"again-{right}")
        r1 = reject(w2, b2, "Too long.")
        r2 = reject(w2, b2, NOTE, "b")
        amend(w2, add_acceptance=[RULE], answers=r2.note, about=right, words=YES)
        assert version(w2) == 2 and meta(w2)["about"] == right.upper() and r1.note
    only_first = refusal(w, add_acceptance=[RULE], answers=first.note, about="R1", words=YES)
    assert "or an earlier rejection (none): R1." in only_first  # the first rejection has no earlier one


def test_about_falls_back_to_the_oldest_stored_version(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    old = Rejection("20000101T000000000000-root-0001", "R1", "t", "title", (), NOTE, "")  # recorded before any stored version was defined
    basis.rejections.append(old)
    w.d.clock.advance(1)
    write_version(w, 2, ["At most 600 words", "Every factual claim has a source URL", "Cite at most five sources"], initiated="user", words="Few sources.")  # C3
    text = refusal(w, add_acceptance=[RULE], answers=old.note, about="C3", words=YES)
    assert text.startswith("refused: about (CLI: --about) must be the id your one question named: a criterion of contract v1, in force when R1 was recorded (C1, C2)")
    amend(w, add_acceptance=[RULE], answers=old.note, about="C2", words=YES)
    assert version(w) == 3


def test_words_that_repeat_the_rejection_are_refused(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    text = (
        "refused: words (CLI: --words) repeats rejection R1's own note (or the note is part of it). The answer is what the user said to your one "
        "question after the rejection (e.g. \"Yes, add it.\"); an \"always ...\" inside the rejection is not it. Nothing was written."
    )
    for pasted in (NOTE, "No, not right yet. " + NOTE, NOTE.upper()):
        assert refusal(w, add_acceptance=[RULE], answers=found.note, about="C1", words=pasted) == text
    assert version(w) == 1
    amend(w, add_acceptance=[RULE], answers=found.note, about="C1", words=YES)
    assert version(w) == 2


# ------------------------------------------------------------------------------ step 4: what is written, and in which order


def test_the_answer_writes_the_contract_then_the_link_then_the_owners_note(factory: Any, tmp_path: Path) -> None:
    holder: dict[str, SpyLinks] = {}

    def spy(inner: LinkNotes) -> LinkNotes:
        holder["links"] = SpyLinks(inner, lambda: (version(w), len(inbox(w))))
        return holder["links"]

    w, basis = build(factory, tmp_path, links=spy)
    found = reject(w, basis)
    before = [m.id for m in inbox(w)]
    amend(w, add_acceptance=[RULE, "Names its week"], answers=found.note, about="c1", words=YES)
    (call,) = holder["links"].calls
    assert call == ("root", "ceo", found.title, found.note, ("C3", "C4"), YES)  # the criteria the amendment added, in order
    assert holder["links"].seen == [(2, len(before))]  # the contract is v2 already; the owner's note is not in the inbox yet
    after = [m for m in inbox(w) if m.id not in before]
    assert [(m.sender, m.type) for m in after] == [("root", "note"), ("runtime", "note")]  # the link first, then the amendment note
    link, note = after
    assert link.title == f'criterion link on "{found.title}": C3, C4' and link.reply_to == found.note and link.criterion == "C3, C4"
    assert note.title == "contract of service weekly-brief changed to v2"
    assert "C3: The memo starts with a Summary line\nC4: Names its week\n" in note.body  # confirmed: no mark
    assert "(not confirmed)" not in note.body.split("Rule (c)")[0]
    assert "The client's yes to R1 (about C1) is recorded: C3, C4 are client-confirmed.\n" in note.body


def test_the_product_link_has_the_shape_of_feedback_confirms(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    first, second = reject(w, basis, "Too long."), reject(w, basis, NOTE, "b")
    amend(w, add_acceptance=[RULE], answers=first.note, about="C1", words=YES)
    by_hand = w.commands.feedback("root", second.task, "reject", YES, source="human", criterion=["C3"], confirms=second.note)
    link = next(m for m in inbox(w) if m.reply_to == first.note and m.criterion)
    for field in ("sender", "to", "type", "wake", "source", "criterion", "feedback", "status", "budget", "revises", "service"):
        assert getattr(link, field) == getattr(by_hand, field), field
    assert link.body == LINK_HEADER.format(confirms=first.note) + "\n\n" + YES
    assert link.body.replace(first.note, "X") == by_hand.body.replace(second.note, "X")
    assert (link.source, link.wake, link.criterion) == ("human", False, "C3")
    assert link.title == f'criterion link on "{first.title}": C3' and by_hand.title == f'criterion link on "{second.title}": C3'


def test_the_versions_record_answers_about_words_or_initiated_user(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    amend(w, add_acceptance=[RULE], answers=found.note, about="c2", words=YES)
    v2 = meta(w)
    assert (v2["answers"], v2["about"], v2["words"]) == (found.note, "C2", YES) and "initiated" not in v2
    assert list(v2).index("created") < list(v2).index("answers") < list(v2).index("about") < list(v2).index("words")  # the keys follow `created`
    amend(w, add_acceptance=["Names its week"], words="Name the week, please.")
    v3 = meta(w)
    assert (v3["initiated"], v3["words"]) == ("user", "Name the week, please.") and "answers" not in v3 and "about" not in v3  # never copied
    amend(w, budget=12)
    v4 = meta(w)
    assert not {"answers", "about", "words", "initiated"} & set(v4)
    kept = {n: m for n, m, _ in w.store.versions("ceo", SERVICE, "SERVICE")}
    assert kept[2]["answers"] == found.note and kept[3]["initiated"] == "user"  # the archived versions keep theirs, immutable
    assert [c.answers for c in w.catalog.criteria("ceo", SERVICE)] == ["", "", found.note, ""]
    assert [c.user for c in w.catalog.criteria("ceo", SERVICE)] == [False, False, False, True]


def test_the_reply_records_the_answer_or_the_users_own_request(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path)
    found = reject(w, basis)
    text = amend(w, add_acceptance=[RULE, "Names its week"], answers=found.note, about="C1", words=YES)
    link = next(m for m in inbox(w) if m.reply_to == found.note and m.criterion)
    assert text.splitlines()[0].startswith("redefined service `weekly-brief` of ceo: contract v1 -> v2")
    assert text.endswith(
        f"\nRecorded as the user's answer to R1 (rejection {found.note}; your question named C1): link {link.id} names C3, C4. "
        "C3, C4 are client-confirmed: a playbook revision citing them may add their words (rule (c))."
    )
    one = amend(w, add_acceptance=["Third rule"], words="Add a third rule, please.")
    assert one.endswith(
        '\nRecorded as a change the user asked for on their own: "Add a third rule, please.". C5 is user-initiated: it travels with every '
        "request but never admits a playbook revision (rule (c))."
    )
    two = amend(w, add_acceptance=["Fourth rule", "Fifth rule"], words="y" * 200)
    assert two.endswith(
        f'\nRecorded as a change the user asked for on their own: "{"y" * 159}…". C6, C7 are user-initiated: they travel with every request but '
        "never admit a playbook revision (rule (c))."
    )
    removal = amend(w, remove_acceptance=["Fifth rule"], words="Drop the fifth.")
    assert removal.endswith('\nRecorded as a change the user asked for on their own: "Drop the fifth.".')  # nothing added: nothing is user-initiated


def test_the_owners_note_says_the_users_own_request_is_user_initiated(factory: Any, tmp_path: Path) -> None:
    w, _ = build(factory, tmp_path)
    amend(w, add_acceptance=["Names its week", "Names its year"], words="Name the week and the year.")
    (note,) = notes_of_the_runtime(w)
    assert 'The client asked for this change on their own ("Name the week and the year."): C3, C4 are user-initiated.\n' in note.body
    assert "C3: Names its week (user-initiated)\nC4: Names its year (user-initiated)\n" in note.body
    assert "(not confirmed)" not in note.body.split("Rule (c)")[0]
    amend(w, remove_acceptance=["Names its year"], words="Drop the year.")
    assert 'The client asked for this change on their own ("Drop the year.").\n' in notes_of_the_runtime(w)[-1].body


def test_a_call_without_the_new_arguments_is_unchanged(factory: Any, tmp_path: Path) -> None:
    """What does not change the acceptance criteria needs none of them (the criteria need words: the gate's tests); an agent client amends as ever."""
    w, _ = build(factory, tmp_path)
    text = amend(w, budget=12)
    assert version(w) == 2 and "Recorded as" not in text
    assert not {"answers", "about", "words", "initiated"} & set(meta(w))
    (note,) = notes_of_the_runtime(w)
    assert "budget per request: 10 -> 12 runs" in note.body and "The client" not in note.body
    define(w, owner="ceo/eng", name="inner", actor="ceo")
    amend(w, owner="ceo/eng", name="inner", actor="ceo", add_acceptance=["Brief"])
    found = w.store.read_contract("ceo/eng", "inner")
    assert found is not None and found[0]["version"] == 2 and not {"answers", "about", "words", "initiated"} & set(found[0])


# ------------------------------------------------------------------------------ section 12: the link that cannot be written


def test_a_link_write_that_fails_delivers_the_owners_note_then_raises_and_feedback_takes_the_one_recovery_link(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path, links=lambda inner: FlakyLinkNotes(inner, failures=1, error=OSError("disk full")))
    found = reject(w, basis)
    with pytest.raises(OrgError) as info:
        amend(w, add_acceptance=[RULE, "Names its week"], answers=found.note, about="C1", words=YES)
    assert str(info.value) == (
        f"the contract of `weekly-brief` is now v2 (it answers rejection {found.note}), but the link that records the user's yes could not be "
        "written (disk full). Record it with "
        f'feedback(task_id="{found.task}", verdict="reject", confirms="{found.note}", criterion=["C3", "C4"], source="human", note=<their answer, '
        "verbatim>) (CLI: --confirms, --criterion, --source human, --note)."
    )
    assert version(w) == 2 and meta(w)["answers"] == found.note  # the contract is the new version
    (note,) = notes_of_the_runtime(w)  # the owner was told, with the ids not confirmed and the missing link named
    assert note.sender == "runtime" and "C3: The memo starts with a Summary line (not confirmed)\nC4: Names its week (not confirmed)\n" in note.body
    assert "The link that records the client's yes to R1 could not be written; it follows as a criterion link.\n" in note.body
    assert "client's yes to R1 (about C1) is recorded" not in note.body  # the "recorded" line is for a yes that has its link
    # before the recovery link, every other confirmation of that rejection is refused with the one call it takes
    recovery = (
        f"refused: rejection {found.note} was answered by contract v2 of `weekly-brief`, and its link is missing (its write failed). The only link "
        f'it still takes is that one: feedback(task_id="{found.task}", verdict="reject", confirms="{found.note}", criterion=["C3", "C4"], '
        'source="human", note=<the user\'s answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was recorded.'
    )
    for ids, source in ((["C3"], "human"), (["C3", "C4"], "relayed"), (["none"], "human")):
        with pytest.raises(OrgError) as refused_link:
            w.commands.feedback("root", found.task, "reject", YES, confirms=found.note, criterion=ids, source=source)
        assert str(refused_link.value) == recovery
    link = w.commands.feedback("root", found.task, "reject", YES, source="human", criterion=["C3", "C4"], confirms=found.note)
    assert (link.reply_to, link.criterion, link.source) == (found.note, "C3, C4", "human")
    # the link is on the rejection now: one answer only
    basis.rejections[0] = replace(found, answered=link.id)
    with pytest.raises(OrgError) as second:
        w.commands.feedback("root", found.task, "reject", "Again.", source="human", criterion=["C3", "C4"], confirms=found.note)
    assert str(second.value).startswith(f"refused: rejection {found.note} was answered by contract v2 of `weekly-brief` (define_service(..., answers=")
    assert f"its link {link.id} records the user's yes" in str(second.value)


def test_a_link_write_that_fails_with_the_owners_note_failing_too_says_so(factory: Any, tmp_path: Path) -> None:
    w, basis = build(
        factory, tmp_path, links=lambda inner: FlakyLinkNotes(inner, failures=1, error=OSError("disk full")),
        delivery=lambda inner: FlakyDelivery(inner, failures=1, error=OSError("inbox gone")),
    )
    found = reject(w, basis)
    with pytest.raises(OrgError) as info:
        amend(w, add_acceptance=[RULE], answers=found.note, about="C1", words=YES)
    assert str(info.value).endswith("(CLI: --confirms, --criterion, --source human, --note); the owner was not told either (inbox gone).")
    assert "could not be written (disk full)" in str(info.value) and version(w) == 2


def test_a_note_that_fails_after_the_link_was_written_raises_as_it_always_did(factory: Any, tmp_path: Path) -> None:
    w, basis = build(factory, tmp_path, delivery=lambda inner: FlakyDelivery(inner, failures=1, error=OSError("inbox gone")))
    found = reject(w, basis)
    with pytest.raises(OSError, match="inbox gone"):
        amend(w, add_acceptance=[RULE], answers=found.note, about="C1", words=YES)
    assert version(w) == 2 and any(m.reply_to == found.note and m.criterion for m in inbox(w))  # the contract and its link are there
