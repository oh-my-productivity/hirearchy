"""The ``Org`` facade is a contract with three parts (ARCHITECTURE.md 6.4, step E2-facade).

1. It is the whole recorded surface: one case for each of the 98 methods of ``tests/architecture/org_signatures.json`` (their names, kinds and
   parameters are guarded by ``orgmcp/app/tests/test_facade_signatures.py``), grouped by the mixin that holds them.
2. Every method does what its feature does: through a runtime of spy fakes (``open_runtime(root, overrides)``) it makes exactly one call of
   exactly one port, with the arguments it was given, and returns what the port returned; through the real runtime it returns, or raises, what the
   real port did.
3. It is pure delegation (an AST check): a method is one ``return`` of a port or of a feature function, with its arguments passed through.
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org
from orgmcp.app.runtime import OrgRuntime
from orgmcp.app.tests import _signatures
from orgmcp.app.tests._mixins import MIXINS
from orgmcp.app.wiring import open_runtime, runtime_ports

from . import facade_cases, facade_rules
from .facade_cases import CASES, Case, FunctionCase, Spy, Tape, World

pytestmark = pytest.mark.architecture

RECORDED = json.loads(_signatures.SIGNATURES.read_text(encoding="utf-8"))["Org"]
PORTS = runtime_ports()  # field name -> the Protocol of its port
RED: dict[str, set[str]] = {  # the methods that still hold logic (or a bare call) when the tests are written, per test
    "fakes": {
        "dir", "ledger", "save_ledger", "commit", "end_run", "emit", "default_model", "_check_authority", "_check_allocation", "pause", "resume",
        "clear_failures", "can_message", "_next_hops", "_normalize_artifact", "_agent_line", "_quote", "_files_lines", "_render_in_context", "_upstream",
    },
    "real": {
        "dir", "ledger", "save_ledger", "default_model", "can_message", "_next_hops", "_normalize_artifact", "_agent_line", "_quote", "_files_lines",
        "_render_in_context", "_upstream",
    },
    "function": {"find_root", "init", "_wakes", "_check_lessons"},
    "direct": {"find_root", "_wakes", "_check_lessons"},
}


def params(cases: list[Case | FunctionCase], test: str) -> list[Any]:
    red = [pytest.mark.xfail(strict=True, reason="red: E2-facade")]
    return [pytest.param(c, id=facade_cases.case_id(c), marks=red if c.name in RED[test] else []) for c in cases]


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> World:
    return facade_cases.build_world(tmp_path_factory.mktemp("facade-world") / "org")


# ---------------------------------------------------------------------------------------------------------------- 1. the whole surface


def test_there_is_one_case_for_each_method_of_the_recorded_surface() -> None:
    names = [c.name for c in CASES]
    assert len(names) == len(set(names))
    assert set(names) == set(RECORDED) - {"__init__"}  # __init__ is the constructor of the facade: test_construction_*
    assert len(names) + 1 == 98


@pytest.mark.parametrize("name", sorted(set(RECORDED) - {"__init__"}))
def test_a_method_is_what_the_record_says_it_is(name: str) -> None:
    assert hasattr(Org, name) and facade_cases.kind_of(name) == RECORDED[name]["kind"]


@pytest.mark.parametrize(("module", "cls", "methods"), MIXINS, ids=[m for m, _, _ in MIXINS])
def test_the_cases_are_grouped_by_mixin(module: str, cls: str, methods: str) -> None:
    assert {c.name for c in CASES if c.mixin == module} == set(methods.split()) - {"__init__"}


def test_construction_opens_the_runtime_of_the_organization(world: World, tmp_path: Path) -> None:
    org = Org(world.root)
    assert isinstance(org.runtime, OrgRuntime) and org.runtime.root == org.root == world.root
    assert Org(str(world.root)).root == world.root


# ----------------------------------------------------------------------------------------------- 2. the same behaviour on both runtimes


@pytest.fixture
def fakes(world: World) -> tuple[Org, Tape]:
    """An ``Org`` whose runtime holds a spy for every port a case goes through: it touches no file."""
    tape = Tape()
    overrides = {PORTS[c.field]: Spy(PORTS[c.field], tape) for c in CASES if isinstance(c, Case) and c.field in PORTS}  # a case of an unknown field fails in its own test
    org = Org(world.root)
    org.runtime = open_runtime(world.root, overrides)
    return org, tape


@pytest.mark.parametrize("case", params([c for c in CASES if isinstance(c, Case)], "fakes"))
def test_on_a_runtime_of_fakes_a_method_makes_the_one_call_of_its_port(case: Case, world: World, fakes: tuple[Org, Tape]) -> None:
    org, tape = fakes
    call = case.args(world)
    result = facade_cases.invoke(org, case.name, call)
    assert len(tape.calls) == 1, f"{case.name} made {len(tape.calls)} port calls"
    made = tape.calls[0]
    assert (made.port, made.method) == (PORTS[case.field], case.port_method)
    expected = case.expect(world) if case.expect else call
    assert facade_cases.binds(made.port, made.method, made.call) == facade_cases.binds(made.port, made.method, expected)
    assert result is made.result


@pytest.mark.parametrize("case", params([c for c in CASES if isinstance(c, Case)], "real"))
def test_on_the_real_runtime_a_method_returns_or_raises_what_its_port_did(case: Case, world: World, tmp_path: Path) -> None:
    shutil.copytree(world.root, tmp_path / "org")
    org = Org(tmp_path / "org")
    tape = Tape()
    port = PORTS[case.field]
    org.runtime = dataclasses.replace(org.runtime, **{case.field: facade_cases.Recording(port, getattr(org.runtime, case.field), tape)})
    call = case.args(world)
    result: Any = None
    raised: BaseException | None = None
    try:
        result = facade_cases.invoke(org, case.name, call)
    except BaseException as error:  # noqa: BLE001 - what the port raised is what the facade must raise
        raised = error
    assert len(tape.calls) == 1, f"{case.name} made {len(tape.calls)} port calls"
    made = tape.calls[0]
    assert (made.port, made.method) == (port, case.port_method)
    expected = case.expect(world) if case.expect else call
    assert facade_cases.binds(port, made.method, made.call) == facade_cases.binds(port, made.method, expected)
    if made.error is not None:
        assert raised is made.error
    else:
        assert raised is None and result is made.result


@pytest.mark.parametrize("case", params([c for c in CASES if isinstance(c, FunctionCase)], "function"))
def test_a_static_or_class_method_calls_the_function_of_its_feature(case: FunctionCase, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module(case.module)
    calls: list[facade_cases.Call] = []
    answer = world.root if case.wrap else facade_cases.Returned(case.name)

    def spy(*positional: Any, **keywords: Any) -> Any:
        calls.append((positional, keywords))
        return answer

    monkeypatch.setattr(module, case.attribute, spy)
    call = case.args(world)
    result = facade_cases.invoke(Org(world.root), case.name, call)
    assert calls == [call]
    assert (isinstance(result, Org) and result.root == world.root) if case.wrap else result is answer


@pytest.mark.parametrize("case", params([c for c in CASES if isinstance(c, FunctionCase) and not c.wrap], "direct"))
def test_a_static_or_class_method_returns_or_raises_what_its_function_does(case: FunctionCase, world: World) -> None:
    function = getattr(importlib.import_module(case.module), case.attribute)
    call = case.args(world)
    outcomes = []
    for run in (lambda: facade_cases.invoke(Org(world.root), case.name, call), lambda: function(*call[0], **call[1])):
        try:
            outcomes.append(("returned", run()))
        except Exception as error:  # noqa: BLE001
            outcomes.append(("raised", (type(error), str(error))))
    assert outcomes[0] == outcomes[1]


def test_init_creates_the_organization_and_returns_the_facade_of_it(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "x" / ".." / "new", "a mission", {"max_hops": 7})
    assert isinstance(org, Org) and org.root == (tmp_path / "new").resolve() and (org.root / "ORG.md").is_file()
    assert org.config["max_hops"] == 7 and "a mission" in org.rules()


# --------------------------------------------------------------------------------------------------------- 3. the facade is pure delegation


@pytest.mark.xfail(strict=True, reason="red: E2-facade")
def test_facade_is_pure_delegation() -> None:
    assert facade_rules.FACADE_MODULES, "no _facade_*.py found"
    violations = facade_rules.check()
    assert not violations, "logic left in the facade (move it into the feature):\n" + "\n".join(map(str, violations))


def test_the_only_exemption_is_the_constructor_of_the_facade() -> None:
    assert set(facade_rules.EXEMPT) == {("CoreMixin", "__init__")}


@pytest.mark.xfail(strict=True, reason="red: E2-facade")
def test_no_facade_module_carries_mypy_debt() -> None:
    debt = [p.name for p in facade_rules.FACADE_MODULES if p.read_text(encoding="utf-8").startswith("# mypy: ignore-errors")]
    assert not debt, f"strict-clean the facade modules: {debt}"


GOOD = '''
from x import norm, indent

class AMixin:
    runtime: object
    def one(self, a, *rest, b=None, **more):
        """doc"""
        return self.runtime.port.method(a, *rest, key=b, **more)
    @property
    def prop(self):
        return self.runtime.port
    @staticmethod
    def two(text, n):
        return indent(text, n)
    @classmethod
    def three(cls, root):
        return cls(norm(root))
'''


def violations_of(body: str) -> list[str]:
    return [v.why for v in facade_rules.check_source(f"from x import f\nclass AMixin:\n    runtime: object\n    def m(self, a, b):\n{body}")]


def test_the_check_accepts_the_shapes_of_delegation() -> None:
    assert facade_rules.check_source(GOOD) == []


@pytest.mark.parametrize(
    "body",
    [
        "        return self.runtime.port.m(a, 1)",  # a constant is computed
        "        return self.runtime.port.m(a + b)",  # computation
        "        return self.runtime.port.m(a or b)",
        "        return self.runtime.port.m(f(a))",  # a nested call
        "        return self.runtime.port.m(a) or None",  # not a call
        "        x = self.runtime.port.m(a)\n        return x",  # two statements
        "        if a:\n            return self.runtime.port.m(a)\n        return None",  # branching
        "        for x in a:\n            return self.runtime.port.m(x)",  # a loop
        "        try:\n            return self.runtime.port.m(a)\n        except ValueError:\n            return None",
        "        self.runtime.port.m(a)",  # no return
        "        return self.other.m(a)",  # not a port of the runtime
        "        return self.runtime.m(a)",  # the runtime itself is not a port
        "        return self.runtime.port.sub.m(a)",
        "        return f(c)",  # not a parameter
        "        return self.helper(a)",
        "        return g(a)",  # not imported
        "        return self.runtime.port.m(a) if b else None",
    ],
)
def test_the_check_rejects_logic(body: str) -> None:
    assert violations_of(body), body


def test_the_check_rejects_a_function_at_module_level_and_a_loose_property() -> None:
    assert facade_rules.check_source("def helper(a):\n    return a\n")
    assert facade_rules.check_source("class AMixin:\n    @property\n    def p(self):\n        return self.runtime.port.m()\n") == []
    assert facade_rules.check_source("class AMixin:\n    @property\n    def p(self):\n        return self.runtime.port.m().x\n")
