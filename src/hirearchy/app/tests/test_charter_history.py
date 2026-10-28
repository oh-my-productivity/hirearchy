"""``GitCharterHistory``: the committed versions of the charters and ORG.md, read as pairs (design 4.1, 4.5), over ``MemoryOrgHistory`` and a fake clock.

The pairs carry what the files themselves say (the frontmatter keys that differ, the lines of the added section, whether the body outside it differs), so a
label is read from content and never from a commit message."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from hirearchy.app._charter_history import GitCharterHistory
from hirearchy.kernel.testing import FakeClock
from hirearchy.retro._ports import CharterHistory, CharterPair, CharterVersions, KeyChange
from hirearchy.snapshots import Change, OrgHistory
from hirearchy.snapshots.testing import MemoryOrgHistory

LEAD, OTHER = "lead/AGENT.md", "other/AGENT.md"
UNPARSABLE = b"---\nkey: [unclosed\n---\nbody\n"
HEADING = "## Added by your changes"


def charter(body: str = "Do the work.", **meta: str) -> bytes:
    head = "".join(f"{key}: {value}\n" for key, value in {"role": "Lead", **meta}.items())
    return f"---\n{head}---\n{body}\n".encode()


def with_added(*lines: str, body: str = "Do the work.", **meta: str) -> bytes:
    return charter(f"{body}\n\n{HEADING}\n" + "\n".join(lines), **meta)


def org_md(**keys: object) -> bytes:
    return ("---\n" + "".join(f"{key}: {value}\n" for key, value in keys.items()) + "---\nOrg.\n").encode()


def at(minute: int) -> datetime:
    return datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)


def charters(history: OrgHistory, clock: FakeClock | None = None) -> GitCharterHistory:
    return GitCharterHistory(history, clock or FakeClock())


def test_it_is_a_charter_history() -> None:
    assert isinstance(charters(MemoryOrgHistory()), CharterHistory)


def test_known_is_false_without_a_history() -> None:
    assert charters(MemoryOrgHistory()).versions(["lead"]) == CharterVersions(known=False)  # no commit at all: the history answers none
    assert charters(MemoryOrgHistory()).org_started() is None and charters(MemoryOrgHistory()).subject("a" * 40) is None


def test_versions_are_consecutive_pairs_newest_first_with_the_keys_that_differ() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: charter(tools="[read]")}, at(0))
    second = history.commit({LEAD: charter(tools="[read, write]")}, at(1))
    third = history.commit({LEAD: charter(tools="[read, write]", model="claude-opus-5.5")}, at(2))
    history.commit({"other.md": b"x\n"}, at(3))  # a commit that touches no charter is no pair
    found = charters(history).versions(["lead"])
    assert found == CharterVersions(known=True, pairs=(
        CharterPair(LEAD, third, at(2), keys=(KeyChange("model", None, "claude-opus-5.5"),)),
        CharterPair(LEAD, second, at(1), keys=(KeyChange("tools", '["read"]', '["read", "write"]'),)),
    ))
    assert [p.addr for p in found.pairs] == ["lead", "lead"] and all(not p.body_differs and p.kind == "edit" for p in found.pairs)


def test_a_key_that_goes_away_reads_none_and_the_values_read_as_text() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: charter(max_children="3", can_hire="true", note="hello")}, at(0))
    second = history.commit({LEAD: charter(max_children="2", can_hire="false")}, at(1))
    (pair,) = charters(history).versions(["lead"]).pairs
    assert pair.commit == second
    assert pair.keys == (KeyChange("can_hire", "true", "false"), KeyChange("max_children", "3", "2"), KeyChange("note", "hello", None))  # sorted by key


def test_the_added_section_before_and_after() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: with_added("- First line [change aaa]")}, at(0))
    second = history.commit({LEAD: with_added("- First line [change aaa]", "", "- Second line [change bbb]")}, at(1))
    (pair,) = charters(history).versions(["lead"]).pairs
    assert pair == CharterPair(
        LEAD, second, at(1), added_before=("- First line [change aaa]",), added_after=("- First line [change aaa]", "- Second line [change bbb]"),
    )


def test_a_change_outside_the_added_section_is_a_body_difference_and_one_inside_it_is_not() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: with_added("- A [change aaa]", body="Do the work.")}, at(0))
    history.commit({LEAD: with_added("- A [change aaa]", "- B [change bbb]", body="Do the work.")}, at(1))
    third = history.commit({LEAD: with_added("- A [change aaa]", "- B [change bbb]", body="Do the work carefully.")}, at(2))
    inside, outside = charters(history).versions(["lead"]).pairs[::-1]
    assert (outside.commit, outside.body_differs, outside.added_before == outside.added_after) == (third, True, True)
    assert (inside.body_differs, len(inside.added_after) - len(inside.added_before)) == (False, 1)


def test_an_extension_line_a_leads_body_edit_and_a_hand_edit() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: with_added("- A [change aaa]"), OTHER: charter("Review.")}, at(0))
    line = history.commit({LEAD: with_added("- A [change aaa]", "- B [change bbb]")}, at(1))
    body = history.commit({OTHER: charter("Review everything.")}, at(2), message="lead/review: run 1")
    hand = history.commit({OTHER: charter("Review everything.", tools="[read, write]")}, at(3), message="hand edit")
    lead = charters(history).versions(["lead", "other"]).pairs
    assert [(p.addr, p.commit) for p in lead] == [("other", hand), ("other", body), ("lead", line)]
    assert (lead[0].keys, lead[0].body_differs) == ((KeyChange("tools", None, '["read", "write"]'),), False)  # a frontmatter change of a charter
    assert (lead[1].keys, lead[1].body_differs, lead[1].added_after) == ((), True, ())  # a body edit
    assert (lead[2].keys, lead[2].body_differs, lead[2].added_after[-1]) == ((), False, "- B [change bbb]")  # an extension's tagged line


def test_a_commit_that_sweeps_two_writers_edits_labels_each_by_its_content() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: with_added("- A [change aaa]"), OTHER: charter("Review.")}, at(0))
    swept = history.commit({LEAD: with_added("- A [change aaa]", "- B [change bbb]"), OTHER: charter("Review all of it.")}, at(1), message="lead: run 3")
    by_addr = {p.addr: p for p in charters(history).versions(["lead", "other"]).pairs}
    assert by_addr["lead"].commit == by_addr["other"].commit == swept  # one commit, two pairs
    assert (by_addr["lead"].body_differs, by_addr["lead"].added_after[-1]) == (False, "- B [change bbb]")  # the extension's line
    assert (by_addr["other"].body_differs, by_addr["other"].added_after) == (True, ())  # the other writer's body edit


def test_org_md_pairs_give_max_depth_before_and_after() -> None:
    history = MemoryOrgHistory()
    history.commit({"ORG.md": org_md()}, at(0))  # no max_depth: the default, 4
    second = history.commit({"ORG.md": org_md(max_depth=5)}, at(1), message="root: applied extension abc")
    history.commit({"ORG.md": org_md(max_depth=5, default_model="x")}, at(2))  # another key: no pair
    fourth = history.commit({"ORG.md": org_md(max_depth="6")}, at(3))
    found = charters(history).versions([])
    assert found.pairs == (CharterPair("ORG.md", fourth, at(3), depth=("5", "6")), CharterPair("ORG.md", second, at(1), depth=("4", "5")))
    assert found.pairs[0].addr == ""


def test_a_deleted_charter_and_a_created_one_are_pairs_of_their_own_kind() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: charter("one")}, at(0))
    deleted = history.commit({LEAD: None}, at(1))  # the tree moved to .retired/
    created = history.commit({LEAD: charter("a new agent at the old address")}, at(2))
    history.commit({LEAD: charter("a new agent at the old address, edited")}, at(3))
    kinds = [(p.kind, p.commit) for p in charters(history).versions(["lead"]).pairs]
    assert kinds == [("edit", history.head()), ("created", created), ("deleted", deleted)]


def test_a_version_that_cannot_be_compared_is_skipped_once() -> None:
    history = MemoryOrgHistory()
    history.commit({LEAD: charter("one")}, at(0))
    history.commit({LEAD: UNPARSABLE}, at(1))
    history.commit({LEAD: charter("three")}, at(2))
    history.commit({LEAD: charter("four")}, at(3))
    found = charters(history).versions(["lead"])
    assert (found.known, found.skipped, found.truncated) == (True, 1, False)
    assert [p.commit for p in found.pairs] == [history.head()]  # only the pair (four, three) is compared
    big = MemoryOrgHistory()
    big.commit({LEAD: charter("one")}, at(0))
    big.commit({LEAD: charter("x" * 70_000)}, at(1))
    assert (charters(big).versions(["lead"]).pairs, charters(big).versions(["lead"]).skipped) == ((), 1)


def test_the_read_is_bounded_and_says_truncated() -> None:
    history = MemoryOrgHistory()
    for n in range(45):
        history.commit({LEAD: charter(f"v{n}")}, at(n))
    found = charters(history).versions(["lead"])
    assert found.truncated is True and len(found.pairs) == 39  # 40 commits listed: 39 pairs, the oldest has no predecessor in the list
    short = MemoryOrgHistory()
    short.commit({LEAD: charter("v0")}, at(0))
    short.commit({LEAD: charter("v1")}, at(1))
    one = charters(short).versions(["lead"])
    assert (len(one.pairs), one.truncated) == (1, False)


class SlowText(OrgHistory):
    """An ``OrgHistory`` whose ``text`` takes ``seconds`` of the fake clock."""

    def __init__(self, inner: OrgHistory, clock: FakeClock, seconds: float) -> None:
        self.inner, self.clock, self.seconds = inner, clock, seconds
        self.texts = 0

    def first_commit_with(self, path: str) -> str | None:
        return self.inner.first_commit_with(path)

    def blob(self, commit: str, path: str) -> str | None:
        return self.inner.blob(commit, path)

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        self.texts += 1
        self.clock.advance(self.seconds)
        return self.inner.text(commit, path, limit)

    def head(self) -> str | None:
        return self.inner.head()

    def subject(self, commit: str) -> str | None:
        return self.inner.subject(commit)

    def changes(self, paths: Sequence[str], limit: int) -> list[Change] | None:
        return self.inner.changes(paths, limit)


def test_the_five_second_bound_stops_reading_and_truncates() -> None:
    memory = MemoryOrgHistory()
    for n in range(10):
        memory.commit({LEAD: charter(f"v{n}")}, at(n))
    clock = FakeClock()
    slow = SlowText(memory, clock, 2.0)
    found = GitCharterHistory(slow, clock).versions(["lead"])
    assert slow.texts == 3  # read at 0 s, 2 s and 4 s; at 6 s the bound (5 s) is passed, so the rest is not read
    assert found.truncated is True and found.known is True and len(found.pairs) == 2  # the pairs (v9, v8) and (v8, v7)


def test_subject_reads_the_commit_message() -> None:
    history = MemoryOrgHistory()
    first = history.commit({"ORG.md": org_md()}, at(0), message="init")
    second = history.commit({"ORG.md": org_md(max_depth=5)}, at(1), message="root: applied extension abc123\n\nthe body of the message")
    reader = charters(history)
    assert reader.subject(second) == "root: applied extension abc123" and reader.subject(first) == "init"
    assert reader.subject("f" * 40) is None and reader.subject("not a commit") is None


def test_org_started_is_the_time_of_the_commit_that_added_org_md_or_none() -> None:
    history = MemoryOrgHistory()
    history.commit({"a.md": b"x\n"}, at(0))
    assert charters(history).org_started() is None  # ORG.md was never committed
    history.commit({"ORG.md": org_md()}, at(5))
    history.commit({"ORG.md": org_md(max_depth=5)}, at(9))
    assert charters(history).org_started() == at(5)
    assert charters(MemoryOrgHistory()).org_started() is None
