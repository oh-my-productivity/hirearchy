"""``KiroConfinementPolicy`` for kiro-cli V3 (docs/design/kiro-runtime-v3.md 4.2-4.5 and amendments A5, A7): the ``tools`` selector,
the permission rules, the literals and the refusals, as a pure function of the grant."""

from __future__ import annotations

import dataclasses
import itertools
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import JsonObject
from hirearchy.kiro import CHARTER_TOOLS, Confinement
from hirearchy.kiro._confinement import KiroConfinementPolicy

ORG = Path("/t/org")
WS = Path("/t/ws")
POLICY = KiroConfinementPolicy()

MCP = {"capability": "mcp", "match": ["hirearchy/*"], "effect": "allow"}
SKILL = {"capability": "skill", "effect": "deny"}
CONTEXT = {"capability": "context", "effect": "deny"}
ORG_PATTERNS = ["/t/org", "/t/org/**"]
M3 = "the path {p} contains \"{c}\", which kiro-cli's permission patterns cannot match literally, so this agent's access cannot be confined; rename it"
M4 = (
    "this agent has {n} inputs: kiro-cli compiles at most 63 path exclusions into one rule without a separate validation step; "
    "give this agent at most 29 inputs (a common parent folder counts as one)"
)


def ask(tools: Sequence[str], workspace: Path | None = None, inputs: Sequence[Path] = (), org: Path = ORG) -> Confinement:
    return POLICY.file_confinement(org, tools, workspace, inputs)


def subsets() -> list[tuple[str, ...]]:
    return [tuple(t for t, keep in zip(CHARTER_TOOLS, mask) if keep) for mask in itertools.product((False, True), repeat=len(CHARTER_TOOLS))]


def protected(ws: str) -> list[str]:
    return [
        f"{ws}/.kiro", f"{ws}/.kiro/**", f"{ws}/**/.kiro", f"{ws}/**/.kiro/**", f"{ws}/AGENTS.md", f"{ws}/**/AGENTS.md",
        f"{ws}/.git", f"{ws}/.git/**", f"{ws}/**/.git", f"{ws}/**/.git/**",
        f"{ws}/.vscode", f"{ws}/.vscode/**", f"{ws}/**/.vscode", f"{ws}/**/.vscode/**",
    ]


def fs_rules(c: Confinement, capability: str, effect: str) -> list[JsonObject]:
    return [r for r in c.rules if r.get("capability") == capability and r.get("effect") == effect]


# ------------------------------------------------------------------------------------------ the tools selector


def expected_selector(subset: Sequence[str]) -> tuple[str, ...]:
    out = ["@hirearchy"]
    out += [t for t in ("read", "write", "shell") if t in subset]
    if "web_search" in subset and "web_fetch" in subset:
        out.append("web")
    elif "web_fetch" in subset:
        out.append("web_fetch")
    elif "web_search" in subset:
        out.append("remote_web_search")
    return tuple(out)


@pytest.mark.parametrize("subset", subsets(), ids=lambda s: "+".join(s) or "none")
def test_the_selector_of_every_subset_is_the_union_of_its_tags(subset: tuple[str, ...]) -> None:
    c = ask(subset)
    assert c.tools == expected_selector(subset) and c.problem is None
    assert ask(tuple(reversed(subset)) + subset).tools == c.tools  # order and duplicates of the charter do not matter


@pytest.mark.parametrize(
    ("tools", "name"), [(["read", "Shell"], "'Shell'"), (["web"], "'web'"), ([3], "3"), (["shell", "READ"], "'READ'"), ([None], "None")]
)
def test_unknown_mixed_case_or_non_string_tools_set_a_problem_and_keep_the_valid_part(tools: list[object], name: str) -> None:
    valid = [t for t in tools if t in CHARTER_TOOLS]
    c = ask(cast("list[str]", tools), WS, [Path("/t/in")])
    assert c.problem == f"the charter's tools name {name}, which is not one of read, write, shell, web_search, web_fetch (exact, lowercase)"
    assert dataclasses.replace(c, problem=None) == ask(valid, WS, [Path("/t/in")])


def test_the_first_unknown_tool_is_the_one_named() -> None:
    assert "'a'" in (ask(cast("list[str]", ["read", "a", "b"])).problem or "")


@pytest.mark.parametrize("subset", subsets(), ids=lambda s: "+".join(s) or "none")
def test_tools_always_start_with_at_hirearchy_even_with_a_problem(subset: tuple[str, ...]) -> None:
    assert ask(subset).tools[0] == "@hirearchy"
    broken = ask((*subset, "nope"))
    assert broken.problem is not None and broken.tools[0] == "@hirearchy"


# ------------------------------------------------------------------------------------------ the rules


def test_no_tools_is_rules_1_11_12() -> None:
    c = ask([])
    assert c.tools == ("@hirearchy",)
    assert c.rules == (MCP, SKILL, CONTEXT)
    assert c.read == () and c.write is None and c.problem is None


def test_shell_and_both_web_tools_is_the_4_5_example() -> None:
    c = ask(["shell", "web_search", "web_fetch"], None, [])
    assert c.tools == ("@hirearchy", "shell", "web")
    assert c.rules == (
        MCP,
        {"capability": "shell", "match": ["*"], "effect": "allow"},
        {"capability": "web_fetch", "match": ["*"], "effect": "allow"},
        {"capability": "web_search", "match": ["*"], "effect": "allow"},
        SKILL,
        CONTEXT,
    )


def test_shell_alone_is_rules_1_8_11_12() -> None:
    assert ask(["shell"], WS, [Path("/t/in")]).rules == (MCP, {"capability": "shell", "match": ["*"], "effect": "allow"}, SKILL, CONTEXT)


def test_read_write_shell_with_workspace_and_inputs_is_the_4_5_example() -> None:
    org, ws, handbook = Path("/Users/u/acme/org"), Path("/Users/u/proj"), Path("/Users/u/handbook")
    c = ask(["read", "write", "shell"], ws, [handbook], org)
    read = ["/Users/u/proj", "/Users/u/proj/**", "/Users/u/handbook", "/Users/u/handbook/**", "/Users/u/acme/org", "/Users/u/acme/org/**"]
    assert c.tools == ("@hirearchy", "read", "write", "shell")
    assert c.rules == (
        MCP,
        {"capability": "fs_read", "effect": "allow", "match": read},
        {"capability": "fs_write", "effect": "allow", "match": ["/Users/u/proj/**"]},
        {"capability": "fs_write", "effect": "deny", "match": ["/Users/u/acme/org", "/Users/u/acme/org/**"]},
        {"capability": "fs_read", "effect": "deny", "match": ["/**"], "exclude": read},
        {"capability": "fs_write", "effect": "deny", "match": ["/**"], "exclude": ["/Users/u/proj/**"]},
        {"capability": "fs_write", "effect": "deny", "match": protected("/Users/u/proj")},
        {"capability": "shell", "match": ["*"], "effect": "allow"},
        SKILL,
        CONTEXT,
    )
    assert c.read == (ws, handbook, org) and c.write == ws and c.problem is None


def test_read_without_workspace_or_inputs_reads_only_the_org() -> None:
    """The former legacy charter (design 3.6): confined like any other."""
    c = ask(["read"])
    assert c.tools == ("@hirearchy", "read")
    assert c.rules == (
        MCP,
        {"capability": "fs_read", "effect": "allow", "match": ORG_PATTERNS},
        {"capability": "fs_read", "effect": "deny", "match": ["/**"], "exclude": ORG_PATTERNS},
        {"capability": "fs_write", "effect": "deny", "match": ["/**"]},
        SKILL,
        CONTEXT,
    )
    assert c.read == (ORG,) and c.write is None


def test_write_without_workspace_writes_nowhere() -> None:
    c = ask(["write"])
    assert c.tools == ("@hirearchy", "write")
    assert c.rules == (
        MCP,
        {"capability": "fs_write", "effect": "deny", "match": ORG_PATTERNS},
        {"capability": "fs_read", "effect": "deny", "match": ["/**"]},
        {"capability": "fs_write", "effect": "deny", "match": ["/**"]},
        SKILL,
        CONTEXT,
    )
    assert c.read == () and c.write is None


def test_a_write_only_agent_reads_nothing() -> None:
    c = ask(["write"], WS, [Path("/t/in")])
    assert c.rules == (
        MCP,
        {"capability": "fs_write", "effect": "allow", "match": ["/t/ws/**"]},
        {"capability": "fs_write", "effect": "deny", "match": ORG_PATTERNS},
        {"capability": "fs_read", "effect": "deny", "match": ["/**"]},  # no exclude: rule 5 denies every read, `code` included
        {"capability": "fs_write", "effect": "deny", "match": ["/**"], "exclude": ["/t/ws/**"]},
        {"capability": "fs_write", "effect": "deny", "match": protected("/t/ws")},
        SKILL,
        CONTEXT,
    )
    assert c.read == () and c.write == WS


def test_a_read_only_agent_with_a_workspace_writes_nowhere() -> None:
    c = ask(["read"], WS)
    assert {"capability": "fs_write", "effect": "deny", "match": ["/**"]} in c.rules  # rule 6 has no exclude without write
    assert not fs_rules(c, "fs_write", "allow") and c.write is None
    assert c.read == (WS, ORG)


def test_a_workspace_inside_the_org_has_no_org_write_deny() -> None:
    ws = Path("/t/org/ws")
    c = ask(["read", "write"], ws)
    assert {"capability": "fs_write", "effect": "deny", "match": ORG_PATTERNS} not in c.rules
    assert {"capability": "fs_write", "effect": "allow", "match": ["/t/org/ws/**"]} in c.rules
    assert {"capability": "fs_write", "effect": "deny", "match": protected("/t/org/ws")} in c.rules
    assert c.write == ws and c.read == (ws, ORG)


def test_a_workspace_equal_to_the_org() -> None:
    c = ask(["read", "write"], ORG)
    assert {"capability": "fs_write", "effect": "deny", "match": ORG_PATTERNS} not in c.rules
    assert c.read == (ORG,) and c.write == ORG  # the org is listed once
    assert fs_rules(c, "fs_read", "allow")[0]["match"] == ORG_PATTERNS


def test_a_file_input_is_P_and_P_slash_star_star() -> None:
    c = ask(["read"], None, [Path("/t/in/notes.md")])
    assert fs_rules(c, "fs_read", "allow")[0]["match"] == ["/t/in/notes.md", "/t/in/notes.md/**", *ORG_PATTERNS]


def test_duplicate_inputs_are_listed_once() -> None:
    c = ask(["read"], WS, [Path("/t/in"), Path("/t/in"), WS, ORG])
    assert fs_rules(c, "fs_read", "allow")[0]["match"] == ["/t/ws", "/t/ws/**", "/t/in", "/t/in/**", *ORG_PATTERNS]
    assert c.read == (WS, Path("/t/in"), ORG)


def test_rule_7_is_the_14_protected_patterns_in_order() -> None:
    c = ask(["write"], WS)
    (rule,) = [r for r in fs_rules(c, "fs_write", "deny") if r.get("match") == protected("/t/ws")]
    assert len(cast("list[str]", rule["match"])) == 14 and set(rule) == {"capability", "effect", "match"}


def test_no_empty_match_or_exclude_rule_7_iff_write_and_workspace_read_rule_iff_read() -> None:
    inputs: tuple[list[Path], ...] = ([], [Path("/t/in-a")], [Path("/t/in-a"), Path("/t/in-b")])
    for subset, ws, ins in itertools.product(subsets(), (None, WS, Path("/t/org/ws"), ORG), inputs):
        c = ask(subset, ws, ins)
        for rule in c.rules:
            assert rule.get("match", ["x"]) != [] and rule.get("exclude", ["x"]) != [], (subset, ws, rule)
        rule7 = [r for r in fs_rules(c, "fs_write", "deny") if ".kiro" in str(r.get("match"))]
        assert bool(rule7) == ("write" in subset and ws is not None), (subset, ws)
        assert bool(fs_rules(c, "fs_read", "allow")) == ("read" in subset), (subset, ws)
        assert c.rules[0] == MCP and c.rules[-2:] == (SKILL, CONTEXT)


def test_escaping_table() -> None:
    def literal(name: str) -> str:
        c = ask(["write"], Path(f"/t/{name}"))
        return str(fs_rules(c, "fs_write", "allow")[0]["match"][0])  # type: ignore[index]

    assert literal("a[b") == "/t/a[[]b/**"
    assert literal("a]b") == "/t/a[]]b/**"
    assert literal("a*b") == "/t/a[*]b/**"
    assert literal("a?b") == "/t/a[?]b/**"
    assert literal("a b (x)|y !z") == "/t/a b (x)|y !z/**"  # spaces, parentheses, bars and bangs are kept
    assert literal("w [1]*?") == "/t/w [[]1[]][*][?]/**"  # one pass: a `[` written by an escape is not escaped again


@pytest.mark.parametrize("where", ["workspace", "input", "org"])
@pytest.mark.parametrize(
    ("char", "shown"),
    [("{", "{"), ("}", "}"), ("\\", "\\"), ("\n", "\\x0a"), ("\x7f", "\\x7f"), ("\x01", "\\x01"), ("+(", "+("), ("@(", "@("), ("!(", "!(")],
)
def test_refused_characters(where: str, char: str, shown: str) -> None:
    bad = Path(f"/t/bad{char}x")
    shown_path = f"/t/bad{shown}x"
    if where == "workspace":
        c = ask(["read", "write"], bad, [Path("/t/in")])
        assert Path("/t/in") in c.read and c.write is None
    elif where == "input":
        c = ask(["read", "write"], WS, [bad])
        assert c.read == (WS, ORG) and c.write == WS
    else:
        c = ask(["read", "write"], WS, [], org=bad)
        assert c.read == (WS, bad)
    assert c.problem == M3.format(p=shown_path, c=shown)


def test_a_refused_workspace_is_absent_from_every_rule() -> None:
    c = ask(["read", "write", "shell"], Path("/t/bad{x"), [Path("/t/in")])
    assert c.problem is not None
    assert "bad" not in repr(c.rules)
    assert c == dataclasses.replace(ask(["read", "write", "shell"], None, [Path("/t/in")]), problem=c.problem)


def test_the_first_problem_wins_in_the_order_tools_org_workspace_inputs() -> None:
    tools = cast("list[str]", ["read", "x"])
    assert "'x'" in (ask(tools, Path("/t/w{"), [Path("/t/i{")], Path("/t/o{")).problem or "")
    assert "/t/o{" in (ask(["read"], Path("/t/w{"), [Path("/t/i{")], Path("/t/o{")).problem or "")
    assert "/t/w{" in (ask(["read"], Path("/t/w{"), [Path("/t/i{")]).problem or "")
    assert "/t/i{" in (ask(["read"], WS, [Path("/t/i{")]).problem or "")


def test_extglob_openers_are_refused() -> None:
    """A5: kiro's matcher runs with ``noext: true`` (bundle: ``matchExpandedPattern``), so ``+(`` ``@(`` ``!(`` are literal; they are
    still refused, because no probe ran them. A bare ``(``, ``)``, ``+``, ``@`` or ``!`` is fine."""
    for opener in ("+(", "@(", "!("):
        assert ask(["read"], Path(f"/t/a{opener}b)")).problem == M3.format(p=f"/t/a{opener}b)", c=opener)
    for fine in ("a (b)", "a+b", "a@b", "a!b", "a(b", "a)b", "(a)", "a|b"):
        assert ask(["read"], Path(f"/t/{fine}")).problem is None, fine


def test_more_than_29_inputs_is_a_problem_that_suggests_a_common_parent() -> None:
    c = ask(["read"], WS, [Path(f"/t/in/{i:02d}") for i in range(30)])
    assert c.problem == M4.format(n=30) and "common parent folder" in c.problem
    assert len(c.read) == 32  # nothing is dropped: the other fields follow the grant


def test_29_inputs_are_accepted() -> None:
    assert ask(["read"], WS, [Path(f"/t/in/{i:02d}") for i in range(29)]).problem is None


def test_30_inputs_without_read_are_accepted() -> None:
    """A7 scope: without ``read`` no kiro rule lists the inputs, so nothing is compiled that could cross the limit."""
    inputs = [Path(f"/t/in/{i:02d}") for i in range(30)]
    for tools in (["write"], ["shell"], [], ["write", "shell", "web_fetch"]):
        assert ask(tools, WS, inputs).problem is None, tools


def test_30_duplicate_inputs_are_one_input() -> None:
    assert ask(["read"], WS, [Path("/t/in")] * 30).problem is None


def test_the_org_root_is_resolved_through_a_symlink(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    c = ask(["read", "write"], None, [], tmp_path / "link")
    assert c.read == (real.resolve(),)
    assert fs_rules(c, "fs_write", "deny")[0]["match"] == [str(real.resolve()), f"{real.resolve()}/**"]


def test_the_arguments_are_not_changed() -> None:
    tools, inputs = ["write", "read"], [Path("/t/in-a")]
    ask(tools, WS, inputs)
    assert tools == ["write", "read"] and inputs == [Path("/t/in-a")]


def test_the_confinement_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        ask([]).problem = "x"  # type: ignore[misc]
