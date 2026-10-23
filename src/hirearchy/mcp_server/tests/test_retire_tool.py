# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.
"""The ``retire`` tool: the refund it reports, and, for root, what the services of the retired agent keep and what is still open in them (design 5.10).

Defining one of those services again for the same agent continues its contract, playbook and cases, so root tells the user. The note is advisory:
it is read before the retirement and appended after it, a record that cannot be read adds nothing, and the retirement never depends on it."""

from collections.abc import Mapping

import pytest
from testkit.reach.hirearchy.core import ROOT

from hirearchy.kernel import OrgError
from hirearchy.mcp_server._tools_hiring import HiringTools
from hirearchy.mcp_server.testing import ScriptedHiring, ScriptedRetirement
from hirearchy.services import AmendmentBasis, Rejection
from hirearchy.services.testing import AdmittingServiceEvidence

from ._support import call, described, serve
from .test_tools_services import Catalog

ENG = "ceo/eng"


def test_retire_tool_reports_the_refund(org):
    import asyncio

    from testkit.mcp_server_world import build_server

    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=4)
    result = asyncio.run(build_server(org, "ceo").call_tool("retire", {"name": ENG, "reason": "done"}))
    blocks = result[0] if isinstance(result, tuple) else result
    text = "\n".join(getattr(b, "text", "") for b in blocks)
    assert "retired ceo/eng" in text and "4 unspent run(s)" in text and "returned to ceo" in text


FIRST, SECOND = "20261018T100000000001-root-0001", "20261018T090000000002-root-0002"
REJECTION = Rejection(FIRST, "R1", "20261018T090000000001-root-0001", "Brief: ai", (), "Too long.", "")


class RecordOf(AdmittingServiceEvidence):
    """The record each service has (an empty one for the others), or a failure to read it."""

    def __init__(self, bases: Mapping[str, AmendmentBasis], error: Exception | None = None) -> None:
        super().__init__()
        self._bases = bases
        self._error = error

    def amendment_basis(self, owner: str, service: str) -> AmendmentBasis:
        if self._error is not None:
            raise self._error
        return self._bases.get(service, AmendmentBasis((), ()))


class UnreadableCatalog(Catalog):
    def __init__(self, error: Exception) -> None:
        super().__init__({"ceo": ["weekly-brief"]})
        self._error = error

    def service_names(self, addr: str) -> list[str]:
        raise self._error


class UntouchedCatalog(Catalog):
    """The catalog nobody may ask: the tools that print today's text never read the services."""

    def service_names(self, addr: str) -> list[str]:
        raise AssertionError(f"the services of {addr} were read")


def group(retirement: ScriptedRetirement | None = None, catalog: Catalog | None = None, evidence: AdmittingServiceEvidence | None = None) -> HiringTools:
    retiring, offered, record = retirement or ScriptedRetirement(), catalog or Catalog({}), evidence or RecordOf({})
    return HiringTools(lambda: ScriptedHiring(), lambda: retiring, lambda: offered, lambda: record)


def test_root_retire_of_an_owner_names_kept_services_and_open_items() -> None:
    record = RecordOf({"weekly-brief": AmendmentBasis((REJECTION,), (SECOND, "20261018T090000000003-root-0003"))})
    retirement = ScriptedRetirement(refunded=3, to="root")
    out = call(serve(group(retirement, Catalog({"ceo": ["memo", "weekly-brief"]}), record), ROOT), "retire", name="ceo", reason="restructure")
    assert out == (
        "retired root/ceo; 3 unspent run(s) of budget returned to root\n"
        "Kept with ceo: memo, weekly-brief. Defining one of them again for ceo continues its contract, playbook and cases (when a request of it has a "
        f"result). Still open in `weekly-brief`: rejection R1 (message {FIRST}) has no answer; 2 delivered request(s) without a verdict: "
        f"{SECOND}, 20261018T090000000003-root-0003. Tell the user."
    )
    assert retirement.log.of("retire_team") == [((ROOT, "ceo", "restructure"), {})]


def test_root_retire_of_an_owner_with_nothing_open_only_names_what_is_kept() -> None:
    out = call(serve(group(catalog=Catalog({"ceo": ["weekly-brief"]})), ROOT), "retire", name="ceo", reason="restructure")
    assert out == (
        "retired root/ceo\nKept with ceo: weekly-brief. Defining one of them again for ceo continues its contract, playbook and cases (when a request "
        "of it has a result). Tell the user."
    )


def test_root_retire_of_an_agent_without_services_adds_nothing() -> None:
    assert call(serve(group(catalog=Catalog({"ops": ["x"]})), ROOT), "retire", name="ceo", reason="done") == "retired root/ceo"


@pytest.mark.parametrize("error", [OrgError("the cases cannot be read"), OSError("disk")], ids=["OrgError", "OSError"])
def test_a_read_error_before_the_retirement_adds_nothing(error: Exception) -> None:
    for catalog, evidence in ((UnreadableCatalog(error), RecordOf({})), (Catalog({"ceo": ["weekly-brief"]}), RecordOf({}, error))):
        retirement = ScriptedRetirement()
        assert call(serve(group(retirement, catalog, evidence), ROOT), "retire", name="ceo", reason="done") == "retired root/ceo"
        assert retirement.log.of("retire_team") == [((ROOT, "ceo", "done"), {})]  # the retirement still happened


def test_an_agents_retire_and_a_nested_retire_print_todays_text() -> None:
    """Only root's retirement of a top-level agent says anything: an agent retiring its report, and root retiring a nested agent, read no service."""
    untouched = UntouchedCatalog({"ceo": ["weekly-brief"], "ceo/eng": ["inner"]})
    assert call(serve(group(ScriptedRetirement(refunded=4, to="ceo"), untouched), "ceo"), "retire", name="eng", reason="done") == (
        "retired ceo/eng; 4 unspent run(s) of budget returned to ceo"
    )
    assert call(serve(group(catalog=untouched), ROOT), "retire", name="ceo/eng", reason="done") == "retired ceo/eng"  # (the terminal has no retire command)


def test_the_retire_docstring_is_unchanged() -> None:
    assert " ".join(described(serve(group(), ROOT))["retire"].split()) == (
        'Remove a direct report and its team (name: its short name or full address, e.g. "eng" or "ceo/eng"). '
        "Their open tasks are reported to you as failed, and the team's unspent budget is returned to you."
    )
