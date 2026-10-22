"""The small fakes that the other suites stand on: ``MemoryTextFiles``, ``StaticOrgContext``, ``ScriptedConfinementPolicy`` (and the memory role library, beyond its contract)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint._protocols import OrgContext
from hirearchy.kiro import Confinement
from hirearchy.blueprint.testing import MemoryRoleLibrary, MemoryTextFiles, ScriptedConfinementPolicy, StaticOrgContext
from hirearchy.settings import DEFAULT_CONFIG

from ._support import role


def test_memory_files_answer_what_they_hold_and_remember_what_was_read(tmp_path: Path) -> None:
    files = MemoryTextFiles({tmp_path / "a.yaml": "x: 1"})
    assert files.is_file(tmp_path / "a.yaml") and not files.is_file(tmp_path / "b.yaml") and not files.is_file(tmp_path)
    assert files.reads == []
    assert files.read(tmp_path / "a.yaml") == "x: 1" and files.reads == [tmp_path / "a.yaml"]
    with pytest.raises(KeyError):
        files.read(tmp_path / "b.yaml")
    assert files.reads == [tmp_path / "a.yaml", tmp_path / "b.yaml"]  # a read that failed was still a read


def test_memory_files_copy_what_they_are_given(tmp_path: Path) -> None:
    given = {tmp_path / "a": "1"}
    files = MemoryTextFiles(given)
    given[tmp_path / "b"] = "2"
    assert not files.is_file(tmp_path / "b")


def test_a_static_organization_is_a_few_facts_over_the_default_settings(tmp_path: Path) -> None:
    org = StaticOrgContext(tmp_path, {"max_depth": 9}, ["lead"], ["brief", "digest"])
    assert isinstance(org, OrgContext)
    assert org.config() == {**DEFAULT_CONFIG, "max_depth": 9} and org.root() == tmp_path
    assert org.exists("lead") and not org.exists("ops") and org.service_names() == {"brief", "digest"}


def test_a_static_organization_without_arguments_has_the_defaults_and_nothing_else() -> None:
    org = StaticOrgContext()
    assert org.config() == DEFAULT_CONFIG and org.root() is None and not org.exists("lead") and org.service_names() == set()


def test_a_static_organization_gives_its_settings_and_names_as_copies() -> None:
    org = StaticOrgContext(agents=["lead"], services=["brief"])
    org.config()["max_depth"] = 99
    org.service_names().add("other")
    assert org.config()["max_depth"] == DEFAULT_CONFIG["max_depth"] and org.service_names() == {"brief"}


def test_the_scripted_policy_answers_its_read_whatever_it_is_asked_and_records_the_questions() -> None:
    policy = ScriptedConfinementPolicy(read=[Path("/x")])
    answer = policy.file_confinement(Path("/o"), ("read", "shell"), Path("/w"), (Path("/i"),))
    assert answer == Confinement(("@hirearchy", "read", "shell"), (), (Path("/x"),), None, None)
    assert policy.file_confinement(Path("/o2"), ["web_fetch"], None, []).read == (Path("/x"),)
    assert policy.calls == [(Path("/o"), ["read", "shell"], Path("/w"), [Path("/i")]), (Path("/o2"), ["web_fetch"], None, [])]


def test_the_scripted_policy_without_read_answers_nowhere_and_may_carry_a_problem() -> None:
    assert ScriptedConfinementPolicy().file_confinement(Path("/o"), [], None, []) == Confinement(("@hirearchy",), (), (), None, None)
    assert ScriptedConfinementPolicy(problem="why").file_confinement(Path("/o"), [], None, []).problem == "why"


def test_the_memory_role_library_is_given_its_roles_at_once_or_one_by_one() -> None:
    library = MemoryRoleLibrary([role("writer"), role("analyst")])
    library.put(role("manager", kind="manager"))
    assert library.role_names() == ["analyst", "manager", "writer"] and library.get_role("manager") == role("manager", kind="manager")
    library.put(role("writer", title="Other"))  # a role put under a name that is there replaces it
    assert library.get_role("writer") == role("writer", title="Other")
