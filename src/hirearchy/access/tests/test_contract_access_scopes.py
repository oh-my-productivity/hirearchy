"""Contract of ``AccessScopes``: the charters on disk and the in-memory fake answer the same way."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.access import AccessScopes
from hirearchy.access.testing import IMPLEMENTATIONS, AccessHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[AccessScopes], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AccessHarness:
    made = make(request, tmp_path)
    assert isinstance(made.scopes, AccessScopes)
    return made


# ------------------------------------------------------------------------------ workspace_of


def test_the_workspace_is_the_resolved_path_of_the_charter(h: AccessHarness, tmp_path: Path) -> None:
    (tmp_path / "w").mkdir(exist_ok=True)
    h.put_agent("ceo", {"role": "R", "workspace": str(tmp_path / "w" / ".." / "w")})
    assert h.scopes.workspace_of("ceo") == (tmp_path / "w").resolve()


def test_a_workspace_with_a_tilde_is_expanded(h: AccessHarness, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    h.put_agent("ceo", {"role": "R", "workspace": "~/proj"})
    assert h.scopes.workspace_of("ceo") == (tmp_path / "proj").resolve()


@pytest.mark.parametrize("meta", [{"role": "R"}, {"role": "R", "workspace": None}, {"role": "R", "workspace": ""}])
def test_an_agent_without_a_workspace_has_none(h: AccessHarness, meta: dict[str, object]) -> None:
    h.put_agent("ceo", meta)
    assert h.scopes.workspace_of("ceo") is None


@pytest.mark.parametrize("spelling", ["root", "", "/", "root/", None])
def test_root_has_no_workspace_whatever_the_spelling(h: AccessHarness, spelling: str | None) -> None:
    assert h.scopes.workspace_of(spelling) is None  # type: ignore[arg-type]


def test_an_agent_that_does_not_exist_has_no_workspace(h: AccessHarness, tmp_path: Path) -> None:
    assert h.scopes.workspace_of("nobody") is None
    assert h.scopes.workspace_of("../ceo") is None


def test_the_address_is_normalized(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "workspace": str(tmp_path / "w")})
    assert h.scopes.workspace_of(" /ceo/ ") == (tmp_path / "w").resolve()


# ------------------------------------------------------------------------------ inputs_of


def test_inputs_are_the_resolved_paths_of_the_list_in_order(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "inputs": [str(tmp_path / "b"), str(tmp_path / "a" / ".." / "a")]})
    assert h.scopes.inputs_of("ceo") == [(tmp_path / "b").resolve(), (tmp_path / "a").resolve()]


def test_a_single_string_is_one_input(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "inputs": str(tmp_path / "docs")})
    assert h.scopes.inputs_of("ceo") == [(tmp_path / "docs").resolve()]


def test_blank_entries_are_skipped_and_other_values_are_read_as_text(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "inputs": ["", "  ", str(tmp_path / "x"), 5]})
    assert h.scopes.inputs_of("ceo") == [(tmp_path / "x").resolve(), Path("5").resolve()]


@pytest.mark.parametrize("raw", [None, 7, True, {"a": 1}, []])
def test_inputs_that_are_neither_a_string_nor_a_list_are_none(h: AccessHarness, raw: object) -> None:
    h.put_agent("ceo", {"role": "R", "inputs": raw})
    assert h.scopes.inputs_of("ceo") == []


def test_an_agent_without_the_key_has_no_inputs(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R"})
    assert h.scopes.inputs_of("ceo") == []


def test_root_and_unknown_agents_have_no_inputs(h: AccessHarness) -> None:
    assert h.scopes.inputs_of("root") == [] and h.scopes.inputs_of("nobody") == []


def test_inputs_with_a_tilde_are_expanded(h: AccessHarness, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    h.put_agent("ceo", {"role": "R", "inputs": ["~/docs"]})
    assert h.scopes.inputs_of("ceo") == [(tmp_path / "docs").resolve()]


# ------------------------------------------------------------------------------ readable_roots


def team(h: AccessHarness, tmp_path: Path) -> None:
    h.put_agent("ceo", {"role": "R", "workspace": str(tmp_path / "ws-ceo"), "inputs": [str(tmp_path / "in-ceo")]})
    h.put_agent("ceo/eng", {"role": "R", "workspace": str(tmp_path / "ws-eng"), "inputs": [str(tmp_path / "in-eng")]})
    h.put_agent("ceo/eng/qa", {"role": "R", "workspace": str(tmp_path / "ws-qa")})
    h.put_agent("ceo/ops", {"role": "R"})
    h.put_agent("cto", {"role": "R", "workspace": str(tmp_path / "ws-cto"), "inputs": [str(tmp_path / "in-cto")]})


def test_a_manager_reads_its_inputs_and_every_workspace_of_its_subtree(h: AccessHarness, tmp_path: Path) -> None:
    team(h, tmp_path)
    roots = h.scopes.readable_roots("ceo")
    assert roots[0] == (tmp_path / "in-ceo").resolve()  # its inputs first, then the workspaces
    assert sorted(roots[1:]) == sorted((tmp_path / name).resolve() for name in ("ws-ceo", "ws-eng", "ws-qa"))
    assert len(roots) == 4  # not the inputs of its reports, not the workspace of anybody outside


def test_the_inputs_of_the_reports_are_not_readable_to_the_manager(h: AccessHarness, tmp_path: Path) -> None:
    team(h, tmp_path)
    assert (tmp_path / "in-eng").resolve() not in h.scopes.readable_roots("ceo")


def test_a_report_does_not_read_its_managers_workspace(h: AccessHarness, tmp_path: Path) -> None:
    team(h, tmp_path)
    assert h.scopes.readable_roots("ceo/eng") == [(tmp_path / "in-eng").resolve(), (tmp_path / "ws-eng").resolve(), (tmp_path / "ws-qa").resolve()]


def test_an_agent_without_workspace_or_inputs_reads_nothing(h: AccessHarness, tmp_path: Path) -> None:
    team(h, tmp_path)
    assert h.scopes.readable_roots("ceo/ops") == []


def test_the_address_of_readable_roots_is_normalized(h: AccessHarness, tmp_path: Path) -> None:
    team(h, tmp_path)
    assert h.scopes.readable_roots(" /ceo/eng/qa/ ") == [(tmp_path / "ws-qa").resolve()]


def test_root_reads_the_workspace_of_everybody(h: AccessHarness, tmp_path: Path) -> None:
    team(h, tmp_path)
    expected = {(tmp_path / name).resolve() for name in ("ws-ceo", "ws-eng", "ws-qa", "ws-cto")}
    assert set(h.scopes.readable_roots("root")) == expected and len(h.scopes.readable_roots("root")) == 4


def test_an_unknown_agent_reads_nothing(h: AccessHarness, tmp_path: Path) -> None:
    team(h, tmp_path)
    assert h.scopes.readable_roots("nobody") == []


# ------------------------------------------------------------------------------ unconfined_read


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        ({}, True),
        ({"role": "R", "tools": ["read"]}, True),
        ({"workspace": None}, True),
        ({"workspace": ""}, True),
        ({"workspace": "/w"}, False),
        ({"inputs": []}, False),
        ({"inputs": None}, False),
        ({"inputs": ["/in"]}, False),
        ({"workspace": "/w", "inputs": []}, False),
    ],
)
def test_a_charter_is_unconfined_when_it_has_no_workspace_and_no_inputs_key(h: AccessHarness, meta: dict[str, object], expected: bool) -> None:
    assert h.scopes.unconfined_read(meta) is expected
