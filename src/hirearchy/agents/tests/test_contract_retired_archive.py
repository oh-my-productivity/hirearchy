"""Contract of ``RetiredArchive``: the files on disk and the in-memory registry pass the same tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents import RetiredArchive, RetiredTree
from hirearchy.agents.testing import IMPLEMENTATIONS, AgentsHarness

from ._support import agent, make, message

STAMP = "20261018T101500"


@pytest.fixture(params=IMPLEMENTATIONS[RetiredArchive], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AgentsHarness:
    made = make(request, tmp_path)
    assert isinstance(made.archive, RetiredArchive)
    return made


def tree(h: AgentsHarness, name: str) -> RetiredTree:
    found = [t for t in h.archive.trees() if t.name == name]
    assert len(found) == 1, name
    return found[0]


def log(h: AgentsHarness, where: str, name: str = "20260101T000000000000.log") -> None:
    h.put(f"{where}/runs/{name}", "# senders: root\n")


# ------------------------------------------------------------------------------ trees


def test_there_are_no_trees_without_a_retired_directory(h: AgentsHarness) -> None:
    assert h.archive.trees() == []


def test_an_empty_retired_directory_has_no_trees(h: AgentsHarness) -> None:
    h.put_dir(".retired")
    assert h.archive.trees() == []


def test_the_trees_are_the_directories_sorted_by_name(h: AgentsHarness) -> None:
    for name in ("zed-S", "ceo-S", "ceo.eng-S", "alpha-S"):
        h.put_dir(f".retired/{name}")
    assert [t.name for t in h.archive.trees()] == ["alpha-S", "ceo-S", "ceo.eng-S", "zed-S"]


def test_files_in_the_retired_directory_are_no_trees(h: AgentsHarness) -> None:
    h.put_dir(".retired/ceo-S")
    h.put(".retired/notes.txt", "x")
    h.put(".retired/.DS_Store", "x")
    assert [t.name for t in h.archive.trees()] == ["ceo-S"]


@pytest.mark.parametrize(
    ("name", "top_level"),
    [
        ("ceo-20261018T101500", True),
        ("ceo.eng-20261018T101500", False),
        ("ceo.eng.qa-20261018T101500", False),
        ("a-20261018T101500", True),
        ("my-team-20261018T101500", True),
        ("my-team.sub-20261018T101500", False),
        ("ceo-S", True),
        ("ceo.eng-S", False),
        ("ceo-20261018T10150", True),
        ("ceo-20261018T101500123", True),
        ("ceo", True),
        ("ceo.eng", False),
    ],
)
def test_top_level_is_read_from_the_name(h: AgentsHarness, name: str, top_level: bool) -> None:
    h.put_dir(f".retired/{name}")
    assert tree(h, name).top_level is top_level


@pytest.mark.parametrize(
    ("name", "addr"),
    [
        ("ceo-20261023T101010", "ceo"),
        ("ceo.eng-20261023T101010", "ceo/eng"),
        ("ceo.eng.qa-20261023T101010", "ceo/eng/qa"),
        ("my-team-20261023T101010", "my-team"),
        ("my-team.sub-20261023T101010", "my-team/sub"),
        ("ceo-S", "ceo-S"),  # no stamp, nothing to cut off
        ("ceo-20261023T1010", "ceo-20261023T1010"),
        ("ceo-20261023T101010123", "ceo-20261023T101010123"),
    ],
)
def test_a_retired_tree_names_its_address(h: AgentsHarness, name: str, addr: str) -> None:
    """The address of the retired agent is the directory name without its ``-<stamp>`` suffix, ``.`` read as ``/`` (design 5.10): the one rule that
    names and reads a tree, so the service continuation finds the trees of one owner."""
    h.put_dir(f".retired/{name}")
    assert tree(h, name).addr == addr


def test_a_tree_knows_its_directory(h: AgentsHarness) -> None:
    h.put_dir(".retired/ceo-S")
    found = tree(h, "ceo-S")
    assert found.path.name == "ceo-S" and found.path.parent.name == ".retired"


def test_what_archive_wrote_is_found_with_its_flag(h: AgentsHarness) -> None:
    for addr in ("ceo", "ceo/eng"):
        agent(h, addr)
    h.registry.archive("ceo/eng", STAMP)
    h.registry.archive("ceo", STAMP)
    assert [(t.name, t.top_level) for t in h.archive.trees()] == [(f"ceo-{STAMP}", True), (f"ceo.eng-{STAMP}", False)]


# ------------------------------------------------------------------------------ run_count


def test_no_retired_trees_no_runs(h: AgentsHarness) -> None:
    assert h.archive.run_count() == 0


def test_the_run_logs_of_every_retired_tree_are_counted(h: AgentsHarness) -> None:
    log(h, ".retired/ceo-S", "20260101T000000000001.log")
    log(h, ".retired/ceo-S", "20260101T000000000002.log")
    log(h, ".retired/cto-S", "20260101T000000000003.log")
    assert h.archive.run_count() == 3


def test_the_run_logs_of_agents_below_the_retired_one_are_counted(h: AgentsHarness) -> None:
    log(h, ".retired/ceo-S")
    log(h, ".retired/ceo-S/eng", "20260101T000000000002.log")
    log(h, ".retired/ceo-S/eng/qa", "20260101T000000000003.log")
    assert h.archive.run_count() == 3


def test_only_log_files_that_are_not_hidden_count(h: AgentsHarness) -> None:
    log(h, ".retired/ceo-S", "20260101T000000000001.log")
    log(h, ".retired/ceo-S", ".20260101T000000000002.log")
    log(h, ".retired/ceo-S", "20260101T000000000003.txt")
    log(h, ".retired/ceo-S", "notes")
    assert h.archive.run_count() == 1


def test_a_directory_called_something_dot_log_is_not_a_run(h: AgentsHarness) -> None:
    h.put_dir(".retired/ceo-S/runs/20260101T000000000001.log")
    assert h.archive.run_count() == 0


def test_logs_outside_a_runs_directory_do_not_count(h: AgentsHarness) -> None:
    h.put(".retired/ceo-S/stray.log", "x")
    h.put(".retired/ceo-S/work/x.log", "x")
    h.put(".retired/ceo-S/logs/x.log", "x")
    assert h.archive.run_count() == 0


def test_mailboxes_and_work_directories_are_not_searched_for_agents(h: AgentsHarness) -> None:
    for place in ("inbox", "inflight", "read", "sent", "work"):
        log(h, f".retired/ceo-S/{place}")
    log(h, ".retired/ceo-S/eng/work")
    assert h.archive.run_count() == 0


def test_a_runs_directory_is_not_searched_further(h: AgentsHarness) -> None:
    h.put(".retired/ceo-S/runs/sub/runs/20260101T000000000001.log", "x")
    log(h, ".retired/ceo-S")
    assert h.archive.run_count() == 1


def test_a_file_in_the_retired_directory_has_no_runs(h: AgentsHarness) -> None:
    h.put(".retired/runs", "x")
    h.put(".retired/ceo-S.log", "x")
    assert h.archive.run_count() == 0


def test_the_runs_of_live_agents_are_not_counted(h: AgentsHarness) -> None:
    agent(h, "ceo")
    log(h, "ceo")
    assert h.archive.run_count() == 0


def test_archived_runs_stay_counted(h: AgentsHarness) -> None:
    agent(h, "ceo")
    log(h, "ceo", "20260101T000000000001.log")
    log(h, "ceo", "20260101T000000000002.log")
    h.registry.archive("ceo", STAMP)
    assert h.archive.run_count() == 2


# ------------------------------------------------------------------------------ unspent_budget


def given(h: AgentsHarness, files: dict[str, str]) -> None:
    for path, text in files.items():
        h.put(f".retired/ceo-S/{path}", text)


def unspent(h: AgentsHarness, name: str = "ceo-S") -> int:
    return h.archive.unspent_budget(tree(h, name))


def test_a_tree_without_agents_holds_nothing(h: AgentsHarness) -> None:
    h.put_dir(".retired/ceo-S")
    assert unspent(h) == 0


def test_an_agent_holds_what_it_received_minus_what_it_sent_minus_its_runs(h: AgentsHarness) -> None:
    given(h, {
        "AGENT.md": "---\nrole: R\n---\n",
        "inbox/a.md": message(10),
        "inflight/b.md": message(5),
        "read/c.md": message(3),
        "sent/d.md": message(4),
        "sent/e.md": message(1),
        "runs/20260101T000000000001.log": "x",
        "runs/20260101T000000000002.log": "x",
        "runs/20260101T000000000003.log": "x",
    })
    assert unspent(h) == (10 + 5 + 3) - (4 + 1) - 3


def test_what_is_spent_can_exceed_what_was_received(h: AgentsHarness) -> None:
    given(h, {"AGENT.md": "x", "inbox/a.md": message(2), "sent/d.md": message(7), "runs/1.log": "x"})
    assert unspent(h) == 2 - 7 - 1


def test_every_agent_directory_of_the_tree_counts_on_its_own(h: AgentsHarness) -> None:
    given(h, {
        "AGENT.md": "x", "inbox/a.md": message(10), "sent/g.md": message(6),
        "eng/AGENT.md": "x", "eng/inbox/a.md": message(6), "eng/sent/g.md": message(2), "eng/runs/1.log": "x",
        "eng/qa/AGENT.md": "x", "eng/qa/inbox/a.md": message(2), "eng/qa/runs/1.log": "x", "eng/qa/runs/2.log": "x",
    })
    assert unspent(h) == (10 - 6) + (6 - 2 - 1) + (2 - 0 - 2)


def test_a_directory_without_a_charter_is_no_agent_and_adds_nothing(h: AgentsHarness) -> None:
    given(h, {"inbox/a.md": message(10), "runs/1.log": "x", "eng/AGENT.md": "x", "eng/inbox/a.md": message(3)})
    assert unspent(h) == 3


def test_the_directories_that_are_not_agents_are_not_searched(h: AgentsHarness) -> None:
    given(h, {
        "AGENT.md": "x", "inbox/a.md": message(1),
        "work/AGENT.md": "x", "work/inbox/a.md": message(100),
        "services/s/AGENT.md": "x", "services/s/inbox/a.md": message(100),
        ".hidden/AGENT.md": "x", ".hidden/inbox/a.md": message(100),
        "inbox/deep/AGENT.md": "x", "sent/deep/AGENT.md": "x",
    })
    assert unspent(h) == 1


def test_a_tree_is_counted_on_its_own(h: AgentsHarness) -> None:
    h.put(".retired/ceo-S/AGENT.md", "x")
    h.put(".retired/ceo-S/inbox/a.md", message(4))
    h.put(".retired/cto-S/AGENT.md", "x")
    h.put(".retired/cto-S/inbox/a.md", message(9))
    assert (unspent(h, "ceo-S"), unspent(h, "cto-S")) == (4, 9)


def test_only_message_files_count(h: AgentsHarness) -> None:
    given(h, {
        "AGENT.md": "x", "inbox/a.md": message(5), "inbox/b.txt": message(50), "inbox/.hidden.md": message(50),
        "inbox/c.md.tmp": message(50), "inbox/sub/d.md": message(50),
    })
    assert unspent(h) == 5


@pytest.mark.parametrize(
    ("text", "budget"),
    [
        (message(7), 7),
        (message("7"), 7),
        (message(0), 0),
        (message(-3), -3),
        (message(2.9), 2),
        (message(True), 1),
        (message(), 0),
        (message("null"), 0),
        (message("''"), 0),
        (message(7).replace("\n", "\r\n"), 7),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: seven\n---\nx\n", 0),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: [1]\n---\nx\n", 0),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: .nan\n---\nx\n", 0),
        ("---\nto: ceo\ntype: task\nbudget: 7\n---\nx\n", 0),
        ("---\nfrom: root\ntype: task\nbudget: 7\n---\nx\n", 0),
        ("---\nfrom: root\nto: ceo\nbudget: 7\n---\nx\n", 0),
        ("---\nfrom: ''\nto: ceo\ntype: task\nbudget: 7\n---\nx\n", 0),
        ("budget: 7\nno frontmatter\n", 0),
        ("---\nbudget: [unclosed\n---\n", 0),
        ("---\n- a list\n---\nbody\n", 0),
        ("", 0),
    ],
)
def test_a_message_counts_by_its_budget_when_it_is_a_valid_message(h: AgentsHarness, text: str, budget: int) -> None:
    given(h, {"AGENT.md": "x", "inbox/a.md": text})
    assert unspent(h) == budget


def test_the_budget_of_a_run_log_directory_is_its_log_count_only(h: AgentsHarness) -> None:
    given(h, {"AGENT.md": "x", "runs/1.log": "x", "runs/.2.log": "x", "runs/3.txt": "x", "runs/sub/4.log": "x"})
    assert unspent(h) == -1


def test_an_archived_agent_holds_what_it_held(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "R"}, "x")
    h.put("ceo/inbox/a.md", message(8))
    h.put("ceo/sent/b.md", message(3))
    h.put("ceo/runs/20260101T000000000001.log", "x")
    h.registry.archive("ceo", STAMP)
    assert unspent(h, f"ceo-{STAMP}") == 8 - 3 - 1
