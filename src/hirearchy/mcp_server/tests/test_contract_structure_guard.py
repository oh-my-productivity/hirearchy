"""Contract of ``StructureGuard`` (package-private to ``mcp_server``): it refuses, with an ``OrgError`` that says what to do instead, and only for root;
for any other actor nothing is refused. The guard that refuses (``RootStructureGuard``) and the one that never does (``AllowingStructureGuard``, for
the tests of the tools themselves) both keep the second half; the first half is the refusing guard's alone."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from hirearchy.kernel import ROOT, OrgError, OrgPaths
from hirearchy.mcp_server._ports import StructureGuard
from hirearchy.mcp_server._root_structure import RootStructureGuard
from hirearchy.mcp_server.testing import AllowingStructureGuard, ScriptedFiles
from hirearchy.settings.testing import MemoryOrgSettings

from .test_tools_services import Catalog

HERE = Path("/memory/org")
GUARDS = [RootStructureGuard, AllowingStructureGuard]


@pytest.fixture(params=GUARDS, ids=lambda factory: factory.__name__)
def guard(request: pytest.FixtureRequest) -> StructureGuard:
    made = request.param(lambda: Catalog({}), lambda: ScriptedFiles(HERE), lambda: MemoryOrgSettings(), lambda: OrgPaths(HERE)) \
        if request.param is RootStructureGuard else request.param()
    assert isinstance(made, StructureGuard)
    return made


@pytest.mark.parametrize("me", ["ceo", "ceo/mgr"])
def test_an_agent_is_never_refused(guard: StructureGuard, me: str) -> None:
    guard.hire(me)
    guard.retire(me, "eng")
    guard.new_service(me, "ceo/eng", "brief")
    guard.write(me, "ceo/eng/AGENT.md", "---\nrole: E\n---\n", False)
    guard.write(me, "ORG.md", "---\nmax_depth: 9\n---\n", False)


def test_the_refusing_guard_refuses_root_in_words_that_name_the_way_and_say_nothing_was_done() -> None:
    guard = RootStructureGuard(lambda: Catalog({}), lambda: ScriptedFiles(HERE), lambda: MemoryOrgSettings("---\nmax_depth: 4\n---\n"), lambda: OrgPaths(HERE))
    calls: list[Callable[[], None]] = [
        lambda: guard.hire(ROOT), lambda: guard.retire(ROOT, "ceo"), lambda: guard.new_service(ROOT, "ceo", "brief"),
        lambda: guard.write(ROOT, "ceo/AGENT.md", "x", False), lambda: guard.write(ROOT, "ORG.md", "---\nmax_depth: 9\n---\n", False),
    ]
    for refused in calls:
        with pytest.raises(OrgError) as info:
            refused()
        text = str(info.value)
        assert text.startswith("refused: ") and 'extend="current"' in text
        assert text.endswith(("Nothing was created.", "Nothing was retired.", "Nothing was written."))


def test_the_allowing_guard_refuses_nobody() -> None:
    guard = AllowingStructureGuard()
    guard.hire(ROOT)
    guard.retire(ROOT, "ceo")
    guard.new_service(ROOT, "ceo", "brief")
    guard.write(ROOT, "ceo/AGENT.md", "x", False)
    guard.write(ROOT, "ORG.md", "---\nmax_depth: 9\n---\n", False)
