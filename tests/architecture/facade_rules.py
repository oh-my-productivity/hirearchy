"""The rule "the ``Org`` facade is pure delegation" (ARCHITECTURE.md 6.4), as an AST check over ``orgmcp/app/_facade_*.py``.

A method of a facade mixin has, after an optional docstring, ONE statement:

* ``return self.runtime.<field>.<method>(<arguments>)`` (a property may return ``self.runtime.<field>`` itself): the call of a port;
* ``return <function>(<arguments>)``: a static or class delegation to a feature function (an imported name, not a local one);
* ``return cls(<function>(<arguments>))``: a classmethod that builds the facade around what the feature function made.

The arguments are passed through: a parameter of the method by name (``x``, ``*x``, ``name=x``, ``**x``), nothing computed, no constant, no
nested call. No branching, no loop, no ``try``, no ``with``, no assignment, no ``await``/``yield``. Module-level functions are not allowed in a
facade module either (that would be logic that has not moved), only the mixin classes, imports, ``__all__`` and the process hook that
``telemetry`` installs.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .paths import SRC

APP = SRC / "app"
FACADE_MODULES = sorted(APP.glob("_facade_*.py"))


@dataclass(frozen=True)
class Violation:
    module: str
    method: str
    line: int
    why: str

    def __str__(self) -> str:
        return f"{self.module}:{self.line} {self.method}: {self.why}"


# (mixin, method) -> why it is not under the rule.
EXEMPT: dict[tuple[str, str], str] = {
    ("CoreMixin", "__init__"): "constructs the runtime of the organization (Org.__init__ is the facade's own constructor, not a delegation)",
}


def _params(function: ast.FunctionDef) -> set[str]:
    a = function.args
    return {p.arg for p in (*a.posonlyargs, *a.args, *a.kwonlyargs, *filter(None, (a.vararg, a.kwarg)))}


def _is_self_runtime(node: ast.expr) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "runtime" and isinstance(node.value, ast.Name) and node.value.id == "self"


def _is_port(node: ast.expr) -> bool:
    """``self.runtime.<field>``"""
    return isinstance(node, ast.Attribute) and _is_self_runtime(node.value)


def _argument_problems(call: ast.Call, params: set[str]) -> Iterator[str]:
    values: list[ast.expr] = []
    for arg in call.args:
        values.append(arg.value if isinstance(arg, ast.Starred) else arg)
    values += [kw.value for kw in call.keywords]
    for value in values:
        if not isinstance(value, ast.Name):
            yield f"argument `{ast.unparse(value)}` is computed, not passed through"
        elif value.id not in params:
            yield f"argument `{value.id}` is not a parameter of the method"


def _call_problems(call: ast.expr, params: set[str], imported: set[str], *, classmethod_: bool) -> Iterator[str]:
    if not isinstance(call, ast.Call):
        yield f"`{ast.unparse(call)}` is not a call"
        return
    func = call.func
    if isinstance(func, ast.Attribute) and _is_port(func.value):
        yield from _argument_problems(call, params)  # self.runtime.<field>.<method>(...)
    elif isinstance(func, ast.Name) and func.id in imported and func.id not in params:
        yield from _argument_problems(call, params)  # <imported function>(...)
    elif classmethod_ and isinstance(func, ast.Name) and func.id == "cls" and len(call.args) == 1 and not call.keywords:
        yield from _call_problems(call.args[0], params, imported, classmethod_=False)  # cls(<imported function>(...))
    else:
        yield f"`{ast.unparse(func)}(...)` is neither a port of the runtime nor an imported feature function"


def _decorators(function: ast.FunctionDef) -> set[str]:
    return {d.id for d in function.decorator_list if isinstance(d, ast.Name)}


def method_problems(function: ast.FunctionDef, imported: set[str]) -> list[str]:
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]  # the docstring
    if len(body) != 1:
        return [f"the body has {len(body)} statements besides the docstring, not one return"]
    statement = body[0]
    if not isinstance(statement, ast.Return) or statement.value is None:
        return [f"`{ast.unparse(statement).splitlines()[0]}` is not a `return <delegation>`"]
    params = _params(function)
    value = statement.value
    if "property" in _decorators(function) and _is_port(value):
        return []  # a property that is a field of the runtime
    return list(_call_problems(value, params, imported, classmethod_="classmethod" in _decorators(function)))


def _imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
    return names


def check_source(source: str, module: str = "<facade>") -> list[Violation]:
    tree = ast.parse(source)
    imported = _imported_names(tree)
    found: list[Violation] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found.append(Violation(module, node.name, node.lineno, "a function at module level: its logic belongs to a feature"))
        if not isinstance(node, ast.ClassDef) or not node.name.endswith("Mixin"):
            continue
        for member in node.body:
            if not isinstance(member, ast.FunctionDef) or (node.name, member.name) in EXEMPT:
                continue
            found += [Violation(module, f"{node.name}.{member.name}", member.lineno, why) for why in method_problems(member, imported)]
    return found


def check(modules: list[Path] | None = None) -> list[Violation]:
    return [v for path in (modules or FACADE_MODULES) for v in check_source(path.read_text(encoding="utf-8"), path.name)]
