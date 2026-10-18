"""Contract of ``AuthorityPolicy``: authority only narrows down the tree, and the texts of the refusals are the ones agents are shown."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.access import AuthorityPolicy
from orgmcp.access.testing import IMPLEMENTATIONS, AccessHarness
from orgmcp.kernel import OrgError

from ._support import make, outside


@pytest.fixture(params=IMPLEMENTATIONS[AuthorityPolicy], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AccessHarness:
    made = make(request, tmp_path)
    assert isinstance(made.authority, AuthorityPolicy)
    return made


def allowed(h: AccessHarness, actor: str, tools: list[str], workspace: str | None, inputs: list[str] | None = None) -> None:
    h.authority.check_authority(actor, tools, workspace, inputs)


def refused(h: AccessHarness, actor: str, tools: list[str], workspace: str | None, inputs: list[str] | None = None) -> str:
    with pytest.raises(OrgError) as caught:
        h.authority.check_authority(actor, tools, workspace, inputs)
    return str(caught.value)


# ------------------------------------------------------------------------------ tools


def test_tools_the_grantor_holds_can_be_granted(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R", "tools": ["read", "write", "shell"]})
    allowed(h, "ceo", ["read", "shell"], None)
    allowed(h, "ceo", ["read", "write", "shell"], None)
    allowed(h, "ceo", [], None)


def test_tools_the_grantor_lacks_are_refused_sorted(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R", "tools": ["read"]})
    assert refused(h, "ceo", ["web", "read", "shell"], None) == "you cannot grant tools you do not have yourself: shell, web"


def test_a_grantor_without_tools_cannot_grant_any(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R"})
    assert refused(h, "ceo", ["read"], None) == "you cannot grant tools you do not have yourself: read"
    h.put_agent("ceo", {"role": "R", "tools": None})
    assert refused(h, "ceo", ["read"], None) == "you cannot grant tools you do not have yourself: read"


def test_a_tool_given_twice_is_one_tool(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R", "tools": ["read"]})
    allowed(h, "ceo", ["read", "read"], None)
    assert refused(h, "ceo", ["shell", "shell"], None) == "you cannot grant tools you do not have yourself: shell"


def test_root_holds_no_tools(h: AccessHarness) -> None:
    assert refused(h, "root", ["read"], None) == "you cannot grant tools you do not have yourself: read"
    allowed(h, "root", [], None)


# ------------------------------------------------------------------------------ workspace


def test_a_workspace_inside_the_grantors_is_allowed(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "workspace": str(tmp_path / "ws")})
    allowed(h, "ceo", [], str(tmp_path / "ws"))
    allowed(h, "ceo", [], str(tmp_path / "ws" / "sub" / "deeper"))
    allowed(h, "ceo", [], str(tmp_path / "ws" / "a" / ".." / "b"))


def test_a_workspace_outside_the_grantors_is_refused_with_the_grantors_own_spelling(h: AccessHarness, tmp_path: Path) -> None:
    mine = str(tmp_path / "ws")
    h.put_agent("ceo", {"role": "R", "workspace": mine})
    expected = f"a report's workspace must be inside yours ({mine})"
    assert refused(h, "ceo", [], str(tmp_path / "other")) == expected
    assert refused(h, "ceo", [], str(tmp_path)) == expected  # the parent directory is wider
    assert refused(h, "ceo", [], str(tmp_path / "ws-sibling")) == expected  # a longer name is not a subdirectory
    assert refused(h, "ceo", [], str(tmp_path / "ws" / ".." / "other")) == expected  # resolved before it is compared


def test_a_grantor_without_a_workspace_cannot_assign_one(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R"})
    assert refused(h, "ceo", [], str(tmp_path / "ws")) == "you have no workspace, so you cannot assign one"
    h.put_agent("ceo", {"role": "R", "workspace": ""})
    assert refused(h, "ceo", [], str(tmp_path / "ws")) == "you have no workspace, so you cannot assign one"


@pytest.mark.parametrize("workspace", [None, ""])
def test_no_workspace_to_assign_is_never_a_problem(h: AccessHarness, workspace: str | None) -> None:
    h.put_agent("ceo", {"role": "R"})
    allowed(h, "ceo", [], workspace)


def test_a_tilde_workspace_is_expanded_on_both_sides(h: AccessHarness, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    h.put_agent("ceo", {"role": "R", "workspace": "~/ws"})
    allowed(h, "ceo", [], "~/ws/sub")
    assert refused(h, "ceo", [], "~/elsewhere") == "a report's workspace must be inside yours (~/ws)"


# ------------------------------------------------------------------------------ inputs


def test_inputs_inside_the_inputs_or_the_workspace_of_the_grantor_are_allowed(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "workspace": str(tmp_path / "ws"), "inputs": [str(tmp_path / "a"), str(tmp_path / "b")]})
    allowed(h, "ceo", [], None, [str(tmp_path / "a"), str(tmp_path / "b" / "docs"), str(tmp_path / "ws" / "x")])


def test_an_input_outside_all_of_them_is_refused_naming_the_resolved_bases_and_the_input(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "workspace": str(tmp_path / "ws"), "inputs": [str(tmp_path / "a")]})
    bases = f"{(tmp_path / 'ws').resolve()}, {(tmp_path / 'a').resolve()}"  # the workspace first, then the inputs
    assert refused(h, "ceo", [], None, [str(tmp_path / "a"), str(tmp_path / "c")]) == (
        f"a report's inputs must be inside your inputs or workspace ({bases}): {tmp_path / 'c'}"
    )


def test_the_inputs_are_named_as_they_were_given(h: AccessHarness, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    h.put_agent("ceo", {"role": "R", "inputs": [str(tmp_path / "a")]})
    assert refused(h, "ceo", [], None, ["~/c/../d"]).endswith("): ~/c/../d")


def test_a_grantor_with_neither_workspace_nor_inputs_cannot_assign_inputs(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R"})
    assert refused(h, "ceo", [], None, [str(tmp_path / "a")]) == "you have no workspace or inputs, so you cannot assign inputs"
    h.put_agent("ceo", {"role": "R", "inputs": []})
    assert refused(h, "ceo", [], None, [str(tmp_path / "a")]) == "you have no workspace or inputs, so you cannot assign inputs"


@pytest.mark.parametrize("inputs", [None, []])
def test_no_inputs_to_assign_is_never_a_problem(h: AccessHarness, inputs: list[str] | None) -> None:
    h.put_agent("ceo", {"role": "R"})
    allowed(h, "ceo", [], None, inputs)


def test_the_checks_run_in_order_tools_then_workspace_then_inputs(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R"})
    assert refused(h, "ceo", ["shell"], str(tmp_path / "w"), [str(tmp_path / "i")]).startswith("you cannot grant tools")
    assert refused(h, "ceo", [], str(tmp_path / "w"), [str(tmp_path / "i")]).startswith("you have no workspace, so")
    assert refused(h, "ceo", [], None, [str(tmp_path / "i")]).startswith("you have no workspace or inputs")


def test_a_grantor_that_does_not_exist_is_the_error_of_the_charter_reader(h: AccessHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.authority.check_authority("nobody", [], None)


# ------------------------------------------------------------------------------ check_inputs


def test_absolute_paths_outside_the_organization_pass_as_given(h: AccessHarness) -> None:
    given = [str(outside(h, "a")), str(outside(h, "b", "c"))]
    assert h.authority.check_inputs(given) == given


def test_one_string_is_one_input_and_none_is_no_input(h: AccessHarness) -> None:
    assert h.authority.check_inputs(str(outside(h, "a"))) == [str(outside(h, "a"))]
    assert h.authority.check_inputs(None) == [] and h.authority.check_inputs([]) == [] and h.authority.check_inputs("") == []


def test_blank_entries_are_dropped_and_the_others_are_stripped(h: AccessHarness) -> None:
    assert h.authority.check_inputs(["", "   ", f"  {outside(h, 'a')}  "]) == [str(outside(h, "a"))]


def test_tuples_and_other_values_are_read_as_text(h: AccessHarness) -> None:
    assert h.authority.check_inputs((str(outside(h, "a")),)) == [str(outside(h, "a"))]
    with pytest.raises(OrgError, match="^an input must be an absolute path \\(got `5`\\)$"):
        h.authority.check_inputs([5])


def test_a_relative_input_is_refused_with_the_text_it_was_given(h: AccessHarness) -> None:
    with pytest.raises(OrgError) as caught:
        h.authority.check_inputs([str(outside(h, "a")), "  docs/x "])
    assert str(caught.value) == "an input must be an absolute path (got `docs/x`)"


def test_a_tilde_input_is_absolute_after_its_expansion(h: AccessHarness, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(outside(h, "home")))
    assert h.authority.check_inputs(["~/docs"]) == ["~/docs"]


def test_an_input_inside_the_organization_is_refused(h: AccessHarness) -> None:
    for inside in (h.root, h.root / "ceo", h.root / "ceo" / "work" / ".." / "x"):
        with pytest.raises(OrgError) as caught:
            h.authority.check_inputs([str(inside)])
        assert str(caught.value) == f"an input must not overlap the organization directory ({h.root}): {inside}"


def test_an_input_that_contains_the_organization_is_refused(h: AccessHarness) -> None:
    with pytest.raises(OrgError) as caught:
        h.authority.check_inputs([str(h.root.parent)])
    assert str(caught.value) == f"an input must not overlap the organization directory ({h.root}): {h.root.parent}"


def test_the_first_bad_input_decides(h: AccessHarness) -> None:
    with pytest.raises(OrgError, match="absolute"):
        h.authority.check_inputs([str(outside(h, "a")), "rel", str(h.root)])
    with pytest.raises(OrgError, match="overlap"):
        h.authority.check_inputs([str(outside(h, "a")), str(h.root), "rel"])
