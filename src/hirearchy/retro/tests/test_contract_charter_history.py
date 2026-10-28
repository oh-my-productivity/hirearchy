"""Contract of ``CharterHistory`` (the consumer port of ``retro``, design 4.1): what a reader of the organization's committed charters may rely on.

Here the fake the other tests of ``retro`` use, ``ScriptedCharterHistory``, which answers the pairs, subjects and start it was given. Its git twin is
``app/tests/test_charter_history.py``, which reads the same shapes from commits."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hirearchy.retro._ports import CharterHistory, CharterPair, CharterVersions, KeyChange
from hirearchy.retro.testing import ScriptedCharterHistory

AT = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def pair(path: str, commit: str, minutes: int, **fields: object) -> CharterPair:
    return CharterPair(path, commit, AT + timedelta(minutes=minutes), **fields)  # type: ignore[arg-type]


LEAD_TOOLS = pair("lead/AGENT.md", "c3", 3, keys=(KeyChange("tools", '["read"]', '["read", "write"]'), KeyChange("model", None, "claude-opus-5.5")))
LEAD_BODY = pair("lead/AGENT.md", "c2", 2, body_differs=True)
OTHER = pair("other/AGENT.md", "c2", 2, added_before=("- A [change 1]",), added_after=("- A [change 1]", "- B [change 2]"))
ORG = pair("ORG.md", "c1", 1, depth=("4", "5"))


def test_it_is_a_charter_history() -> None:
    assert isinstance(ScriptedCharterHistory(), CharterHistory)


def test_versions_are_consecutive_pairs_newest_first_with_the_keys_that_differ() -> None:
    history = ScriptedCharterHistory([LEAD_TOOLS, LEAD_BODY, OTHER])
    found = history.versions(["lead"])
    assert found == CharterVersions(known=True, pairs=(LEAD_TOOLS, LEAD_BODY))  # the pairs of the agents asked for, in the order given (newest first)
    assert found.pairs[0].keys == (KeyChange("tools", '["read"]', '["read", "write"]'), KeyChange("model", None, "claude-opus-5.5"))
    assert history.versions(["other", "lead"]).pairs == (LEAD_TOOLS, LEAD_BODY, OTHER) and history.calls == [("versions", "lead"), ("versions", "other", "lead")]


def test_the_added_section_before_and_after() -> None:
    (found,) = ScriptedCharterHistory([OTHER]).versions(["other"]).pairs
    assert found.added_before == ("- A [change 1]",) and found.added_after == ("- A [change 1]", "- B [change 2]") and not found.body_differs


def test_org_md_pairs_give_max_depth_before_and_after() -> None:
    found = ScriptedCharterHistory([LEAD_TOOLS, ORG]).versions([])  # ORG.md is always asked
    assert found.pairs == (ORG,) and found.pairs[0].depth == ("4", "5") and found.pairs[0].addr == ""
    assert LEAD_TOOLS.addr == "lead" and pair("a/b/AGENT.md", "c", 0).addr == "a/b"


def test_known_is_false_without_a_history() -> None:
    assert ScriptedCharterHistory([LEAD_TOOLS], known=False).versions(["lead"]) == CharterVersions(known=False)
    assert CharterVersions() == CharterVersions(known=False, pairs=(), truncated=False, skipped=0)


def test_the_read_is_bounded_and_says_truncated() -> None:
    found = ScriptedCharterHistory([LEAD_TOOLS], truncated=True, skipped=2).versions(["lead"])
    assert (found.known, found.truncated, found.skipped, found.pairs) == (True, True, 2, (LEAD_TOOLS,))
    assert ScriptedCharterHistory([LEAD_TOOLS]).versions(["lead"]).truncated is False


def test_subject_reads_the_commit_message() -> None:
    history = ScriptedCharterHistory(subjects={"c1": "root: applied extension abc123", "c2": ""})
    assert history.subject("c1") == "root: applied extension abc123" and history.subject("c2") == "" and history.subject("zz") is None
    assert history.calls == [("subject", "c1"), ("subject", "c2"), ("subject", "zz")]


def test_org_started_is_the_time_of_the_commit_that_added_org_md_or_none() -> None:
    assert ScriptedCharterHistory(started=AT).org_started() == AT
    assert ScriptedCharterHistory().org_started() is None and ScriptedCharterHistory(known=False, started=AT).org_started() is None


def test_a_deleted_and_a_created_charter_are_pairs_of_their_own_kind() -> None:
    deleted, created = pair("lead/AGENT.md", "c9", 9, kind="deleted"), pair("lead/AGENT.md", "c8", 8, kind="created")
    assert (LEAD_BODY.kind, deleted.kind, created.kind) == ("edit", "deleted", "created")
    assert ScriptedCharterHistory([deleted, created]).versions(["lead"]).pairs == (deleted, created)
