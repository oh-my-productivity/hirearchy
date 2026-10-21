"""``GuardedOrgFileWriter``: which collaborator it asks for what, and in which order, with recording fakes.

What it writes and refuses is the contract (``test_contract_org_file_writer.py`` and the suites next to it); this pins the seams: a charter
goes to the registry of the agents and nothing else does, the guard decides before anything is touched, the authority policy and the
scopes are asked about the merged frontmatter, and the settings are read when the write happens."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from hirearchy.access import AccessScopes, AuthorityPolicy
from hirearchy.access.testing import DEFAULT_ORG_MD
from hirearchy.agents.testing import MemoryAgents
from hirearchy.kernel import OrgError, OrgPaths
from hirearchy.orgfiles._charter_merge import CharterMerger
from hirearchy.orgfiles._guard import PathGuard
from hirearchy.orgfiles._writer import GuardedOrgFileWriter
from hirearchy.orgfiles.testing import MemoryOrgFileStore
from hirearchy.settings.testing import MemoryOrgSettings


class RecordingAgents(MemoryAgents):
    def __init__(self) -> None:
        super().__init__()
        self.rewrites: list[tuple[str, str]] = []

    def rewrite_charter(self, addr: str, text: str) -> None:
        self.rewrites.append((addr, text))
        super().rewrite_charter(addr, text)


class RecordingStore(MemoryOrgFileStore):
    def __init__(self, agents: MemoryAgents) -> None:
        super().__init__(agents)
        self.writes: list[tuple[Path, str]] = []

    def write_text(self, path: Path, text: str) -> None:
        self.writes.append((path, text))
        super().write_text(path, text)


class RecordingAuthority(AuthorityPolicy):
    def __init__(self) -> None:
        self.checked: list[tuple[str, list[str], str | None, list[str] | None]] = []
        self.inputs_seen: list[object] = []

    def check_authority(self, actor: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str] | None = None) -> None:
        self.checked.append((actor, list(tools), workspace, None if inputs is None else list(inputs)))

    def check_inputs(self, inputs: object) -> list[str]:
        self.inputs_seen.append(inputs)
        return ["normalized"]


class AnswerScopes(AccessScopes):
    def __init__(self, unconfined: set[str]) -> None:
        self.unconfined = unconfined
        self.asked: list[Mapping[str, object]] = []

    def workspace_of(self, addr: str) -> Path | None:
        raise AssertionError("the writer never asks for a workspace")

    def inputs_of(self, addr: str) -> list[Path]:
        raise AssertionError("the writer never asks for inputs")

    def readable_roots(self, addr: str) -> list[Path]:
        raise AssertionError("the writer never asks for the readable roots")

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        self.asked.append(dict(meta))
        return "unconfined" in str(meta.get("role"))


class Parts:
    """A writer over recording collaborators, with a manager ``lead`` and its report ``rev`` (and a stranger)."""

    def __init__(self, scopes: AccessScopes | None = None, authority: AuthorityPolicy | None = None) -> None:
        self.settings = MemoryOrgSettings(DEFAULT_ORG_MD)
        self.agents = RecordingAgents()
        self.store = RecordingStore(self.agents)
        self.authority = authority or RecordingAuthority()
        self.scopes = scopes or AnswerScopes(set())
        paths = OrgPaths(self.store.root)
        self.writer = GuardedOrgFileWriter(
            paths, self.store, PathGuard(paths, self.store, self.agents), CharterMerger(), self.agents, self.agents, self.agents,
            self.scopes, self.authority, self.settings,
        )
        self.agents.create("lead", {"role": "Lead", "tools": ["read"]}, "body")
        self.agents.create("lead/rev", {"role": "Reviewer", "tools": ["read"], "model": "m"}, "body")
        self.agents.rewrites.clear()
        self.store.writes.clear()


def test_an_ordinary_file_goes_to_the_store_and_never_to_the_registry() -> None:
    p = Parts()
    p.writer.write("lead", "lead/work/n.md", "text")
    assert p.store.writes == [(p.store.root / "lead" / "work" / "n.md", "text")] and p.agents.rewrites == []


def test_a_charter_goes_to_the_registry_under_the_address_of_the_agent_and_never_to_the_store() -> None:
    p = Parts()
    p.writer.write("lead", "lead/rev/AGENT.md", "---\nrole: R2\n---\nnew\n")
    assert p.store.writes == []
    assert p.agents.rewrites == [("lead/rev", "---\nrole: R2\ntools:\n- read\nmodel: m\n---\nnew\n")]


def test_root_s_charter_edit_goes_to_the_registry_untouched() -> None:
    p = Parts()
    p.writer.write("root", "lead/AGENT.md", "as given")
    assert p.agents.rewrites == [("lead", "as given")] and p.store.writes == []


def test_a_refusal_of_the_guard_touches_nothing_and_asks_nobody() -> None:
    p = Parts()
    with pytest.raises(OrgError):
        p.writer.write("lead", "lead/inbox/x.md", "x")
    with pytest.raises(OrgError):
        p.writer.write("lead", "lead/rev/AGENT.md.", "---\nrole: R\n---\n")
    assert p.store.writes == [] and p.agents.rewrites == []
    assert isinstance(p.authority, RecordingAuthority) and p.authority.checked == [] and p.authority.inputs_seen == []


def test_the_authority_policy_is_asked_about_the_merged_tools_workspace_and_inputs() -> None:
    p = Parts()
    p.agents.rewrite_charter("lead/rev", "---\nrole: Reviewer\ntools: [read, shell]\nworkspace: /w/rev\ninputs: [/i/a]\n---\nold\n")
    p.writer.write("lead", "lead/rev/AGENT.md", "---\nrole: R2\n---\nnew\n")
    assert isinstance(p.authority, RecordingAuthority)
    assert p.authority.inputs_seen == [["/i/a"]]
    assert p.authority.checked == [("lead", ["read", "shell"], "/w/rev", ["normalized"])]


def test_a_charter_without_tools_or_inputs_asks_with_empty_lists() -> None:
    p = Parts()
    p.agents.rewrite_charter("lead/rev", "---\nrole: Reviewer\n---\nold\n")
    p.writer.write("lead", "lead/rev/AGENT.md", "---\nrole: R2\n---\nnew\n")
    assert isinstance(p.authority, RecordingAuthority)
    assert p.authority.inputs_seen == [None] and p.authority.checked == [("lead", [], None, ["normalized"])]


def test_the_scopes_decide_whether_a_read_tool_is_unconfined() -> None:
    scopes = AnswerScopes(set())
    p = Parts(scopes)
    p.writer.write("lead", "lead/rev/AGENT.md", "---\nrole: R2\n---\nnew\n")  # confined: the manager's own charter is not even asked
    assert scopes.asked == [{"role": "R2", "tools": ["read"], "model": "m"}]
    p.writer.write("lead", "lead/rev/AGENT.md", "---\nrole: R3\n---\nnew\n", append=True)  # an append is not merged: only the new text is asked
    assert len(scopes.asked) == 1  # the chunk has no tools: there is nothing to ask


def test_a_charter_that_is_unconfined_is_refused_when_the_manager_is_confined() -> None:
    scopes = AnswerScopes(set())
    p = Parts(scopes)
    with pytest.raises(OrgError, match="needs an `inputs:` list"):
        p.writer.write("lead", "lead/rev/AGENT.md", "---\nrole: an unconfined one\n---\nnew\n")
    assert scopes.asked == [{"role": "an unconfined one", "tools": ["read"], "model": "m"}, {"role": "Lead", "tools": ["read"]}]  # then the manager's own
    assert p.agents.rewrites == [] and p.store.writes == []
    assert isinstance(p.authority, RecordingAuthority) and p.authority.checked == []


def test_the_cap_is_read_from_the_settings_at_the_time_of_the_write() -> None:
    p = Parts()
    p.settings.write_raw("---\nmemory_max_words: 2\n---\n")
    with pytest.raises(OrgError, match="would be 3 words; the limit is 2"):
        p.writer.write("lead", "lead/MEMORY.md", "a b c")
    p.settings.write_raw("---\nmemory_max_words: 3\n---\n")
    p.writer.write("lead", "lead/MEMORY.md", "a b c")
    assert p.store.writes == [(p.store.root / "lead" / "MEMORY.md", "a b c")]


def test_an_append_reads_the_old_text_through_the_store() -> None:
    p = Parts()
    p.store.put(p.store.root / "lead" / "work" / "log.md", "old ")
    p.writer.write("lead", "lead/work/log.md", "new", append=True)
    assert p.store.writes == [(p.store.root / "lead" / "work" / "log.md", "old new")]
