"""Characterization: on random organizations the new classes answer exactly what the legacy ``Org`` / ``observe`` / ``review`` /
``LenientOrg`` bodies answered. Written before the legacy bodies were replaced; removed with them."""

from __future__ import annotations

import os
import random
from pathlib import Path

import pytest

from orgmcp.agents._budget import message_budget  # noqa: F401 - the parity of the budget is checked through unspent_budget
from orgmcp.agents._caching import CachingAgentDirectory, FsCharterStamps, FsDirectoryProbe, LenientCharterReader
from orgmcp.agents._charters import FsCharterReader
from orgmcp.agents._directory import FsAgentDirectory
from orgmcp.agents._retired import FsRetiredArchive, OsArchiveFiles
from orgmcp.kernel import BOXES, OrgPaths
from orgmcp.kernel.testing import system_clock

from ._legacy import legacy

NAMES = ["a", "b", "ceo", "eng", "qa", "x1", "Upper", "work", "inbox", "runs", "ops\n", "a b", "agent", "-z", "n" * 33]
MESSAGES = [
    "---\nfrom: root\nto: ceo\ntype: task\nbudget: 5\n---\nx\n",
    "---\nfrom: root\nto: ceo\ntype: note\nbudget: '3'\n---\nx\n",
    "---\nfrom: root\nto: ceo\ntype: task\n---\nx\n",
    "---\nfrom: root\nto: ceo\ntype: task\nbudget: lots\n---\nx\n",
    "no frontmatter",
    "---\nbudget: [oops\n---\n",
    "---\nto: ceo\ntype: task\nbudget: 9\n---\nx\n",
]


def scatter(rng: random.Random, base: Path, depth: int, agent_dirs: bool) -> None:
    """Directories with random names, some of them agents, with mailboxes, run logs and strays."""
    for name in rng.sample(NAMES, rng.randint(0, 5)):
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        if agent_dirs and rng.random() < 0.7:
            (d / "AGENT.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
        for box in (*BOXES, "runs", "work", "services", ".paused"):
            if rng.random() < 0.5:
                (d / box).mkdir(exist_ok=True)
                for i in range(rng.randint(0, 3)):
                    suffix = rng.choice([".md", ".md", ".md", ".log", ".txt", ".md.tmp"])
                    hidden = "." if rng.random() < 0.15 else ""
                    text = rng.choice(MESSAGES)
                    (d / box / f"{hidden}{i}{suffix}").write_text(text, encoding="utf-8")
        if depth:
            scatter(rng, d, depth - 1, agent_dirs)


@pytest.mark.parametrize("seed", range(40))
def test_the_retired_archive_answers_what_review_and_observe_answered(tmp_path: Path, seed: int) -> None:
    rng = random.Random(seed)
    org = legacy("core").Org.init(tmp_path / "org", "mission")
    retired = org.root / ".retired"
    retired.mkdir()
    for top in rng.sample(["ceo-20260101T000000", "ceo.eng-20260101T000000", "cto-20260102T000000", "a.b.c-20260103T000000", "odd", "x-S"], 4):
        (retired / top).mkdir()
        (retired / top / "AGENT.md").write_text("---\nrole: R\n---\n", encoding="utf-8")
        scatter(rng, retired / top, 2, agent_dirs=True)
        for box in (*BOXES, "runs"):
            (retired / top / box).mkdir(exist_ok=True)
            for i in range(rng.randint(0, 3)):
                (retired / top / box / f"{i}.{'log' if box == 'runs' else 'md'}").write_text(rng.choice(MESSAGES), encoding="utf-8")
    (retired / "stray.log").write_text("x", encoding="utf-8")
    archive = FsRetiredArchive(OrgPaths(org.root), OsArchiveFiles())
    observe, review = legacy("observe"), legacy("review")
    assert [(t.path, t.top_level) for t in archive.trees()] == observe._retired_trees(org)
    assert archive.run_count() == review.retired_runs(org)
    for tree in archive.trees():
        assert archive.unspent_budget(tree) == observe._tree_unspent(tree.path), tree.name


@pytest.mark.parametrize("seed", range(40))
def test_the_directory_and_the_charters_answer_what_org_answered(tmp_path: Path, seed: int) -> None:
    rng = random.Random(1000 + seed)
    org = legacy("core").Org.init(tmp_path / "org", "mission")
    scatter(rng, org.root, 3, agent_dirs=True)
    paths = OrgPaths(org.root)
    directory, charters = FsAgentDirectory(paths), FsCharterReader(paths)
    addrs = ["root", "", "ceo", "a", "a/b", "ceo/eng", "ceo/eng/qa", "Upper", "x1", "b/ceo", "ops\n", "a/ops\n/x1", "zz", " /a/ "]
    for addr in addrs:
        assert directory.exists(addr) == org.exists(addr), addr
        assert directory.children(addr) == org.children(addr), addr
        assert directory.subtree(addr) == org.subtree(addr), addr
        assert charters.memory(addr) == org.memory(addr), addr
        try:
            expected = org.charter(addr)
        except Exception as exc:  # noqa: BLE001
            with pytest.raises(type(exc)):
                charters.charter(addr)
        else:
            assert charters.charter(addr) == expected, addr
        try:
            required = org.require(addr)
        except Exception as exc:  # noqa: BLE001
            with pytest.raises(type(exc), match="no such agent"):
                directory.require(addr)
        else:
            assert directory.require(addr) == required
    assert directory.agents() == org.agents()


@pytest.mark.parametrize("seed", range(25))
def test_the_decorators_answer_what_the_lenient_org_answered(tmp_path: Path, seed: int) -> None:
    rng = random.Random(2000 + seed)
    org = legacy("core").Org.init(tmp_path / "org", "mission")
    scatter(rng, org.root, 3, agent_dirs=True)
    for addr in ("a", "ceo", "b/ceo"):  # some charters that cannot be read
        if rng.random() < 0.5 and (org.root / addr).is_dir():
            (org.root / addr / "AGENT.md").write_text("---\nrole: [unclosed\n---\nx\n", encoding="utf-8")
    lenient = legacy("dashboard_data").LenientOrg(org.root)
    paths = OrgPaths(org.root)
    problems: dict[str, str] = {}
    directory = CachingAgentDirectory(FsAgentDirectory(paths), FsDirectoryProbe(paths), system_clock(tmp_path))
    charters = LenientCharterReader(FsCharterReader(paths), FsCharterStamps(paths), problems)
    for addr in ("root", "ceo", "a", "a/b", "ceo/eng", "b/ceo", "zz", "x1"):
        assert directory.children(addr) == lenient.children(addr), addr
        assert charters.charter(addr) == lenient.charter(addr), addr
    assert directory.agents() == lenient.agents()
    assert {k: v for k, v in problems.items()} == {k: v for k, v in lenient.bad.items() if k.endswith("/AGENT.md")}
    os.utime(org.root, ns=(1, 1))
