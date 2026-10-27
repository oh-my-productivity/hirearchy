"""The message as a value: ``meta to_text render cut_body parse from_parts`` and ``latest_results``.

``parse`` must equal what the file reader of the mail package (``CachingMessageParser.parse``; the former ``Message.load``
was its classmethod) builds from the same file, for every fixture."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from hirearchy.kernel import (
    RENDER_BODY_CHARS,
    RUN_CREDIT_TITLE,
    RUNTIME,
    Message,
    credited_stems,
    is_run_credit,
    latest_results,
    run_credit_title,
)
from hirearchy.kernel.tests._reach import reach

MID = "20261018T100000000001-ceo-ab12"


def fixtures() -> list[Message]:
    return [
        Message("root", "ceo", "note", "hello", id=MID, created="2026-10-18T10:00:00"),
        Message("ceo", "ceo/eng", "task", "## Goal\nbuild it\n\n## Acceptance\n- works", title="Build: the thing", budget=5, hops=2,
                id=MID, created="2026-10-18T10:00:00", trace=MID),
        Message("ceo/eng", "ceo", "result", "## Summary\ndone", status="done", reply_to=MID, budget=3, id=MID + "x", created="c"),
        Message("runtime", "ceo", "note", "budget back", wake=False, budget=1, id=MID, created="c"),
        Message("ceo", "ceo/eng", "task", "again", revises="20261018T090000000001-ceo-0000", id=MID, created="c"),
        Message("eng", "ceo", "result", "ok", status="blocked", supersedes="20261018T090000000002-eng-0001", reply_to=MID, id=MID, created="c"),
        Message("ceo", "ceo/eng", "task", "request", service="research", contract=2, playbook=0, id=MID, created="c"),
        Message("ceo", "eng", "note", "verdict", feedback="accept", reply_to=MID, id=MID, created="c"),
        Message("ceo", "eng", "note", "unicode é ✓\n\ttabbed\n  indented", title="título", id=MID, created="c"),
        Message("a", "b", "note", "x" * (RENDER_BODY_CHARS + 50), id=MID, created="c"),
    ]


def test_meta_has_the_always_fields_in_order_and_omits_the_empty_optional_ones() -> None:
    m = Message("root", "ceo", "note", "hi", id="i1", created="2026-10-18T10:00:00")
    assert list(m.meta().items()) == [
        ("id", "i1"), ("from", "root"), ("to", "ceo"), ("type", "note"), ("title", ""), ("created", "2026-10-18T10:00:00"), ("hops", 0),
    ]


def test_meta_with_every_optional_field_in_order() -> None:
    m = Message("a", "b", "result", "x", title="T", reply_to="r", status="done", budget=2, hops=1, wake=False, revises="v", supersedes="s",
                service="svc", contract=1, playbook=0, feedback="reject", trace="tr", id="i", created="c")
    assert list(m.meta()) == ["id", "from", "to", "type", "title", "created", "hops", "wake", "reply_to", "status", "budget", "revises",
                              "supersedes", "service", "contract", "playbook", "feedback", "trace"]
    assert m.meta()["wake"] is False and m.meta()["contract"] == 1 and m.meta()["playbook"] == 0


def test_to_text_is_frontmatter_then_body_with_one_trailing_newline() -> None:
    m = Message("root", "ceo", "note", "hello\n\n", title="T", id="i1", created="c")
    assert m.to_text() == "---\nid: i1\nfrom: root\nto: ceo\ntype: note\ntitle: T\ncreated: c\nhops: 0\n---\nhello\n"


@pytest.mark.parametrize("original", fixtures(), ids=lambda m: f"{m.type}-{m.title or m.body[:8]!s}")
def test_parse_round_trips_to_text(original: Message) -> None:
    assert Message.parse(original.to_text()) == original


@pytest.mark.parametrize("original", fixtures(), ids=lambda m: f"{m.type}-{m.title or m.body[:8]!s}")
def test_parse_equals_the_file_reader_of_the_mail_package_on_every_fixture(original: Message, tmp_path: Path) -> None:
    path = tmp_path / f"{MID}.md"
    path.write_text(original.to_text(), encoding="utf-8")
    loaded = reach("mail._parser").CachingMessageParser().parse(path)
    parsed = Message.parse(path.read_text(encoding="utf-8"), path)
    assert asdict(parsed) == asdict(loaded)
    assert parsed.path == path and parsed.render() == loaded.render() and parsed.to_text() == loaded.to_text()


def test_parse_normalises_newlines_like_the_file_reader(tmp_path: Path) -> None:
    raw = b"---\r\nfrom: root\r\nto: ceo\r\ntype: note\r\n---\r\nline1\r\nline2\r\n"
    path = tmp_path / "20260101T000000000000-root-aaaa.md"
    path.write_bytes(raw)
    parsed = Message.parse(raw.decode("utf-8"), path)
    assert parsed.body == "line1\nline2" and parsed.sender == "root"
    assert asdict(parsed) == asdict(reach("mail._parser").CachingMessageParser().parse(path))
    assert Message.parse("---\rfrom: root\r---\rbody\r").body == "body"


def test_a_file_without_frontmatter_is_a_note_with_defaults() -> None:
    m = Message.parse("just text\n", Path("/org/ceo/inbox/20260101T000000000000-root-aaaa.md"))
    assert (m.sender, m.to, m.type, m.body, m.title, m.budget, m.hops, m.wake) == ("", "", "note", "just text", "", 0, 0, True)
    assert m.id == "20260101T000000000000-root-aaaa" and m.created == ""  # the id falls back to the file stem
    assert Message.parse("just text").id == ""


def test_field_coercions() -> None:
    text = ("---\nfrom: 5\nto: ceo\ntype: task\nbudget: '4'\nhops: 2.0\nwake: false\nrevises: 123\ncontract: '3'\nplaybook: 0\n"
            "service: s\nfeedback: ''\ntrace: t\nid: 7\ncreated: 2026-10-18\n---\nb")
    m = Message.parse(text)
    assert (m.sender, m.budget, m.hops, m.wake, m.revises, m.contract, m.playbook) == ("5", 4, 2, False, "123", 3, 0)
    assert (m.service, m.feedback, m.trace, m.id, m.created) == ("s", None, "t", "7", "2026-10-18")


@pytest.mark.parametrize(("raw", "expected"), [("true", None), ("abc", None), ("1.5", 1), ("''", None), ("~", None), ("[1]", None), ("7", 7)])
def test_optional_integer_fields_read_as_absent_unless_whole_numbers(raw: str, expected: int | None) -> None:
    assert Message.parse(f"---\ncontract: {raw}\n---\nb").contract == expected


def test_wake_is_false_only_for_an_explicit_false() -> None:
    assert [Message.parse(f"---\nwake: {v}\n---\nb").wake for v in ("false", "no", "0", "true", "null", "'false'")] == [False, False, True, True, True, True]


def test_a_malformed_number_raises_like_the_loader() -> None:
    with pytest.raises(ValueError):
        Message.parse("---\nbudget: lots\n---\nb")


def test_from_parts_builds_from_an_already_split_file() -> None:
    m = Message.from_parts({"from": "a", "to": "b", "type": "task", "budget": 2}, "  body  \n", Path("/x/y/idx.md"))
    assert (m.sender, m.to, m.type, m.budget, m.body, m.id, m.path) == ("a", "b", "task", 2, "body", "idx", Path("/x/y/idx.md"))


def test_cut_body_keeps_short_bodies_and_points_to_the_file_for_the_rest() -> None:
    m = Message("a", "eng", "note", "x" * 10, id="i1", path=Path("/o/eng/inbox/i1.md"))
    assert m.cut_body(10) == "x" * 10 and m.cut_body(0) == "x" * 10
    assert m.cut_body(4) == ("xxxx\n\n[... message cut: 6 more of 10 characters. "
                             'Read the rest with read(path="eng/inbox/i1.md") if you need it.]')


def test_cut_body_where_defaults_follow_the_recipient_and_the_path() -> None:
    to_root = Message("a", "root", "note", "y" * 10, id="i2", path=Path("/o/inbox/i2.md"))
    assert to_root.cut_body(1).endswith('read(path="inbox/i2.md") if you need it.]')
    no_path = Message("a", "ceo", "note", "y" * 10, id="i3")
    assert no_path.cut_body(1).endswith('read(path="ceo/<box>/i3.md") if you need it.]')
    assert no_path.cut_body(1, "elsewhere/f.md").endswith('read(path="elsewhere/f.md") if you need it.]')
    assert Message("a", "root", "note", "y" * 10, id="i4").cut_body(1).endswith('read(path="<box>/i4.md") if you need it.]')


def test_cut_body_trims_the_blanks_before_the_cut() -> None:
    assert Message("a", "b", "note", "ab  \ncd", id="i").cut_body(4).startswith("ab\n\n[... message cut: 3 more of 7")


def test_render_of_a_task_a_result_and_a_service_request() -> None:
    task = Message("ceo", "eng", "task", "do it", title="T", budget=3, id="t1")
    assert task.render() == "### task t1\nfrom: ceo | to: eng | title: T | budget: 3 runs\n\ndo it\n"
    result = Message("eng", "ceo", "result", "ok", status="done", reply_to="t1", budget=2, id="r1")
    assert result.render() == "### result r1\nfrom: eng | to: ceo | reply_to: t1 | status: done | returns 2 run(s)\n\nok\n"
    request = Message("ceo", "eng", "task", "ask", service="research", contract=2, playbook=0, revises="t0", supersedes="t00", feedback="reject", id="q1")
    assert request.render() == ("### task q1\nfrom: ceo | to: eng | revises: t0 | supersedes: t00 | service: research (contract v2, playbook v0)"
                                " | feedback: reject\n\nask\n")
    assert Message("a", "b", "note", "n", service="s", id="n1").render() == "### note n1\nfrom: a | to: b | service: s\n\nn\n"


def test_render_cuts_a_long_body_at_the_limit() -> None:
    m = Message("a", "ceo", "note", "z" * 30, id="n1", path=Path("/o/ceo/inbox/n1.md"))
    assert m.render(10).endswith(m.cut_body(10) + "\n")
    assert m.render() == "### note n1\nfrom: a | to: ceo\n\n" + "z" * 30 + "\n"


def test_latest_results_picks_the_highest_id_per_task() -> None:
    blocked = Message("e", "c", "result", "b", status="blocked", reply_to="t1", id="2026-a")
    done = Message("e", "c", "result", "d", status="done", reply_to="t1", id="2026-b")
    other = Message("e", "c", "result", "o", status="failed", reply_to="t2", id="2026-0")
    note = Message("e", "c", "note", "n", reply_to="t1", id="2026-z")
    orphan = Message("e", "c", "result", "x", id="2026-y")
    assert latest_results([done, blocked, other, note, orphan]) == {"t1": done, "t2": other}
    assert latest_results([blocked, done]) == {"t1": done}
    assert latest_results([]) == {}


def credit(to: str = "ceo", stem: str = "20261022T202454859379", **fields: object) -> Message:
    base: dict[str, object] = {"sender": RUNTIME, "to": to, "type": "note", "budget": 1, "wake": False, "title": run_credit_title(to, stem), "body": "returns a run"}
    return Message(**{**base, **fields})  # type: ignore[arg-type]


def test_run_credit_title_and_is_run_credit() -> None:
    assert run_credit_title("ceo/eng", "20261022T202454859379") == f"{RUN_CREDIT_TITLE} ceo/eng@20261022T202454859379"
    assert is_run_credit(credit())
    assert not is_run_credit(credit(sender="ceo"))  # only the runtime credits a run
    assert not is_run_credit(credit(budget=0))  # a credit returns a run
    assert not is_run_credit(credit(type="task"))
    assert not is_run_credit(credit(title="budget reclaimed by ceo"))
    assert not is_run_credit(credit(title=run_credit_title("ceo/eng", "20261022T202454859379")))  # names another agent than the one it was sent to


def test_credited_stems_of_a_received_box() -> None:
    box = [credit(stem="20261022T200000000001"), Message("root", "ceo", "note", "hi", id="n1"), credit(stem="20261022T200000000002"), credit(sender="ceo", stem="20261022T200000000003")]
    assert credited_stems(box) == {"20261022T200000000001", "20261022T200000000002"}


def test_no_credit_gives_an_empty_set() -> None:
    assert credited_stems([]) == set()
    assert credited_stems([Message("root", "ceo", "note", "hi", id="n1")]) == set()


def test_acknowledges_round_trips_through_the_frontmatter_and_shows_in_the_header() -> None:
    m = Message("ceo", "ceo/eng", "note", "Acknowledged.", title="playbook acknowledgement: retire P3 of weekly-brief",
                acknowledges="weekly-brief edit P3 0123456789ab", id="n1", created="c")
    assert m.meta()["acknowledges"] == "weekly-brief edit P3 0123456789ab"
    back = Message.parse(m.to_text())
    assert back == m and back.acknowledges == "weekly-brief edit P3 0123456789ab"
    assert Message.parse("---\nfrom: ceo\nacknowledges: ''\n---\nb").acknowledges is None
    assert m.render() == (
        "### note n1\nfrom: ceo | to: ceo/eng | title: playbook acknowledgement: retire P3 of weekly-brief"
        " | acknowledges: weekly-brief edit P3 0123456789ab\n\nAcknowledged.\n"
    )
    plain = Message("ceo", "ceo/eng", "note", "x", id="n2")
    assert plain.acknowledges is None and "acknowledges" not in plain.meta() and "acknowledges" not in plain.render()
