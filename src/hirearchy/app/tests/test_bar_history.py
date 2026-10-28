"""``GitBarHistory``: the charter and model changes the org's git history shows (design 7), over ``MemoryOrgHistory`` and a fake clock."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from hirearchy.app._bar_history import GitBarHistory
from hirearchy.kernel.testing import FakeClock
from hirearchy.reflection import BarChanges, CharterMark, ModelMark
from hirearchy.reflection._ports import BarHistory
from hirearchy.snapshots import Change, OrgHistory
from hirearchy.snapshots.testing import MemoryOrgHistory

AGENT = "lead/AGENT.md"
UNPARSABLE = "---\nkey: [unclosed\n---\nbody\n"


def charter(body: str = "Do the work.", model: str | None = None) -> bytes:
    head = "name: lead\n" + (f"model: {model}\n" if model is not None else "")
    return f"---\n{head}---\n{body}\n".encode()


def org_md(**keys: str) -> bytes:
    return ("---\n" + "".join(f"{key}: {value}\n" for key, value in keys.items()) + "---\nOrg.\n").encode()


def at(minute: int) -> datetime:
    return datetime(2026, 10, 22, 19, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)


def bar(history: OrgHistory, clock: FakeClock | None = None) -> GitBarHistory:
    return GitBarHistory(history, clock or FakeClock())


def test_it_is_a_bar_history() -> None:
    assert isinstance(bar(MemoryOrgHistory()), BarHistory)


def test_a_changed_charter_body_is_a_charter_mark() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: charter("one")}, at(0))
    second = history.commit({AGENT: charter("two")}, at(1))
    history.commit({"other.md": b"x\n"}, at(2))
    assert bar(history).changes(["lead"]) == BarChanges(known=True, marks=(CharterMark("lead", second, at(1)),))


def test_a_changed_frontmatter_without_a_changed_body_is_no_charter_mark() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: b"---\nname: lead\n---\nbody\n"}, at(0))
    history.commit({AGENT: b"---\nname: lead\nextra: 1\n---\nbody\n"}, at(1))
    assert bar(history).changes(["lead"]) == BarChanges(known=True)


def test_a_changed_model_is_a_model_mark_and_empty_reads_the_org_default() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: charter(model=None)}, at(0))
    second = history.commit({AGENT: charter(model="claude-opus-5.5")}, at(1))
    third = history.commit({AGENT: charter(model="  ")}, at(2))  # blank = the org default again
    fourth = history.commit({AGENT: charter(model="claude-sonnet-5.5")}, at(3))
    assert bar(history).changes(["lead"]).marks == (
        ModelMark("lead", "model", "", "claude-sonnet-5.5", fourth, at(3)),
        ModelMark("lead", "model", "claude-opus-5.5", "", third, at(2)),
        ModelMark("lead", "model", "", "claude-opus-5.5", second, at(1)),
    )


def test_a_commit_that_changes_the_body_and_the_model_gives_both_marks() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: charter("one", "a")}, at(0))
    second = history.commit({AGENT: charter("two", "b")}, at(1))
    assert bar(history).changes(["lead"]).marks == (CharterMark("lead", second, at(1)), ModelMark("lead", "model", "a", "b", second, at(1)))


def test_org_md_default_model_and_effort_compare_through_the_runtime_readers() -> None:
    history = MemoryOrgHistory()
    history.commit({"ORG.md": org_md()}, at(0))  # both missing = the defaults
    second = history.commit({"ORG.md": org_md(default_model="claude-opus-5.5", effort="xhigh")}, at(1))
    history.commit({"ORG.md": org_md(default_model="claude-opus-5.5", effort="xhigh", max_message_chars="500")}, at(2))  # another key: no mark
    fourth = history.commit({"ORG.md": org_md(default_model="''", effort="''")}, at(3))  # null-like values read as the defaults again
    changes = bar(history).changes([])
    assert changes.known and not changes.truncated and changes.skipped == 0
    assert changes.marks == (
        ModelMark("ORG.md", "default_model", "claude-opus-5.5", "claude-sonnet-5.5", fourth, at(3)),
        ModelMark("ORG.md", "effort", "xhigh", "high", fourth, at(3)),
        ModelMark("ORG.md", "default_model", "claude-sonnet-5.5", "claude-opus-5.5", second, at(1)),
        ModelMark("ORG.md", "effort", "high", "xhigh", second, at(1)),
    )


def test_an_org_md_whose_values_are_null_compares_as_the_default() -> None:
    history = MemoryOrgHistory()
    history.commit({"ORG.md": b"---\ndefault_model: null\n---\nOrg.\n"}, at(0))
    history.commit({"ORG.md": b"---\ndefault_model:\neffort: high\n---\nOrg.\n"}, at(1))
    assert bar(history).changes([]) == BarChanges(known=True)


def test_a_version_that_is_not_utf8_is_not_compared_and_counts_once_in_skipped() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: charter("one")}, at(0))
    history.commit({AGENT: b"---\nname: lead\n---\n\xff\xfe\n"}, at(1))  # not UTF-8
    history.commit({AGENT: charter("three")}, at(2))
    history.commit({AGENT: charter("four")}, at(3))
    found = bar(history).changes(["lead"])
    assert found.skipped == 1  # one version, though it belongs to two pairs
    assert [mark.commit for mark in found.marks] == [history.head()]  # only the pair (four, three) is compared


def test_a_version_whose_frontmatter_does_not_parse_is_not_compared_and_counts_once_in_skipped() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: charter("one")}, at(0))
    history.commit({AGENT: UNPARSABLE.encode()}, at(1))
    history.commit({AGENT: charter("three")}, at(2))
    history.commit({AGENT: charter("four")}, at(3))
    found = bar(history).changes(["lead"])
    assert (found.known, found.skipped, found.truncated) == (True, 1, False)
    assert [mark.commit for mark in found.marks] == [history.head()]


def test_a_org_md_that_does_not_parse_is_skipped_too() -> None:
    history = MemoryOrgHistory()
    history.commit({"ORG.md": org_md()}, at(0))
    history.commit({"ORG.md": UNPARSABLE.encode()}, at(1))
    assert bar(history).changes([]) == BarChanges(known=True, skipped=1)


def test_a_version_above_64_kib_counts_in_skipped() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: charter("one")}, at(0))
    history.commit({AGENT: charter("x" * 70_000)}, at(1))
    found = bar(history).changes(["lead"])
    assert (found.marks, found.skipped) == ((), 1)


def test_the_oldest_listed_version_gives_no_mark_and_a_full_list_is_truncated() -> None:
    history = MemoryOrgHistory()
    for n in range(45):
        history.commit({AGENT: charter(f"v{n}")}, at(n))
    found = bar(history).changes(["lead"])
    assert found.truncated is True and len(found.marks) == 39  # 40 commits listed: 39 pairs, the oldest has no predecessor in the list
    assert all(isinstance(mark, CharterMark) for mark in found.marks)
    short = MemoryOrgHistory()
    for n in range(2):
        short.commit({AGENT: charter(f"v{n}")}, at(n))
    one = bar(short).changes(["lead"])
    assert (len(one.marks), one.truncated) == (1, False)  # the first commit has no predecessor: no mark, and the list was not full


def test_a_path_with_a_single_commit_gives_no_mark() -> None:
    history = MemoryOrgHistory()
    history.commit({AGENT: charter("one")}, at(0))
    assert bar(history).changes(["lead"]) == BarChanges(known=True)


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
        memory.commit({AGENT: charter(f"v{n}")}, at(n))
    clock = FakeClock()
    slow = SlowText(memory, clock, 2.0)
    found = GitBarHistory(slow, clock).changes(["lead"])
    assert slow.texts == 3  # read at 0 s, 2 s and 4 s; at 6 s the bound (5 s) is passed, so the rest is not read
    assert found.truncated is True and found.known is True
    assert [type(mark) for mark in found.marks] == [CharterMark, CharterMark]  # the pairs (v9, v8) and (v8, v7)


def test_within_the_bound_nothing_is_truncated() -> None:
    memory = MemoryOrgHistory()
    for n in range(4):
        memory.commit({AGENT: charter(f"v{n}")}, at(n))
    clock = FakeClock()
    found = GitBarHistory(SlowText(memory, clock, 1.0), clock).changes(["lead"])
    assert found.truncated is False and len(found.marks) == 3


def test_each_version_is_read_once_though_it_belongs_to_two_pairs() -> None:
    memory = MemoryOrgHistory()
    for n in range(5):
        memory.commit({AGENT: charter(f"v{n}")}, at(n))
    clock = FakeClock()
    slow = SlowText(memory, clock, 0.0)
    GitBarHistory(slow, clock).changes(["lead"])
    assert slow.texts == 5


def test_no_history_is_unknown() -> None:
    assert bar(MemoryOrgHistory()).changes(["lead"]) == BarChanges(known=False)
    assert BarChanges() == BarChanges(known=False, marks=(), truncated=False, skipped=0)


def test_a_repository_that_never_changed_the_files_is_known_with_no_marks() -> None:
    history = MemoryOrgHistory()
    history.commit({"other.md": b"x\n"}, at(0))
    assert bar(history).changes(["lead"]) == BarChanges(known=True)


def test_the_paths_asked_are_every_charter_and_org_md() -> None:
    history = MemoryOrgHistory()
    history.commit({"lead/AGENT.md": charter("a"), "lead/writer/AGENT.md": charter("w1"), "ORG.md": org_md()}, at(0))
    history.commit({"lead/AGENT.md": charter("b"), "lead/writer/AGENT.md": charter("w2")}, at(1))
    found = bar(history).changes(["lead", "lead/writer"])
    assert sorted((mark.addr, type(mark).__name__) for mark in found.marks) == [("lead", "CharterMark"), ("lead/writer", "CharterMark")]
    assert bar(history).changes(["lead"]).marks == (CharterMark("lead", history.head() or "", at(1)),)
