"""Only a person's own decision can exempt a hire from the authority bound (design 5.6).

``Hiring.hire(approved=True)`` skips the check that a non-root hirer grants no ``can_hire`` and no larger ``max_children``. Three callers may pass
it: the blueprint applier (an approved plan, applied from MCP ``apply_org`` after the user said yes, or by the user at the terminal), the CLI's
``hire`` (the human at the terminal) and the ``Org`` facade (pure delegation). No MCP tool takes the parameter, so no agent can reach it.
"""

import ast

from architecture.paths import SRC

ALLOWED = {"blueprint/_team.py", "cli/_commands_org.py", "app/_facade_hierarchy.py"}


def _library_modules():
    """Every module of ``src/hirearchy`` that is not a test (``tests/`` directories and ``testing.py`` fakes are out)."""
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC)
        if "tests" in rel.parts or rel.name == "testing.py":
            continue
        yield rel.as_posix(), ast.parse(path.read_text(encoding="utf-8"))


def _hire_calls_passing_approved(tree: ast.Module) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "hire"
        and any(k.arg == "approved" for k in node.keywords)
    ]


def test_only_the_blueprint_team_builder_the_cli_and_the_facade_pass_approved_to_hire():
    callers = {rel: lines for rel, tree in _library_modules() if (lines := _hire_calls_passing_approved(tree))}
    assert set(callers) == ALLOWED, callers
    assert not [rel for rel in callers if rel.startswith("mcp_server/")]
