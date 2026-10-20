# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import hashlib

import pytest
from testkit.legacy.orgmcp.core import ROOT, Org


@pytest.fixture
def team(org, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    inputs = tmp_path / "in"
    inputs.mkdir()
    kw = dict(workspace=str(ws), inputs=[str(inputs)])
    org.hire(ROOT, "plain", "Plain", "x")
    org.hire(ROOT, "sh", "Shell", "x", tools=["shell"], **kw)
    org.hire(ROOT, "rd", "Reader", "x", tools=["read"], **kw)
    org.hire(ROOT, "wr", "Writer", "x", tools=["write"], **kw)
    org.hire(ROOT, "dev", "Dev", "x", tools=["read", "write", "shell"], **kw)
    return org


# ------------------------------------------------------------------------------------------------ prompts
def files_of(org, who):
    return org.run_prompt(who, []).split("- Files:")[1].split("# New messages")[0]


def test_write_only_agent_is_told_org_write_and_plain_read(team):
    text = team.run_prompt("wr", [])
    files = files_of(team, "wr")
    assert "orgmcp tools (shown as `@orgmcp/org_write`, `@orgmcp/read`, ...)" in files
    assert "the orgmcp write tool is `@orgmcp/org_write` for you: use it for MEMORY.md and org files" in files
    assert "Read org files with `@orgmcp/read`." in files and "org_read" not in files
    assert '`@orgmcp/org_write`(path="wr/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`)' in text
    assert '`@orgmcp/write`(' not in text


def test_read_only_agent_is_told_org_read_and_plain_write(team):
    text = team.run_prompt("rd", [])
    files = files_of(team, "rd")
    assert "orgmcp tools (shown as `@orgmcp/write`, `@orgmcp/org_read`, ...)" in files and "(orgmcp `write` only)" in files
    assert "written with `@orgmcp/write`, never with the built-in `write`." in files
    assert "ABSOLUTE path" in files and "`@orgmcp/org_read` for you" in files and "org_write" not in files
    assert '`@orgmcp/write`(path="rd/MEMORY.md", ...)' in text


def test_no_prompt_text_of_an_aliased_agent_names_the_hidden_tool_as_usable(team):
    for who in ("dev", "wr"):
        text = team.run_prompt(who, [])
        assert "`@orgmcp/write`(" not in text and "save it with `@orgmcp/write`" not in text
    assert "(it hides `@orgmcp/read`)" not in team.run_prompt("dev", [])


def test_stray_notice_uses_the_name_the_agent_has(team):
    team.save_ledger("strays", {"dev": {"paths": ["/x/dev"], "told": False}})
    notice = team.stray_notice("dev")
    assert "`@orgmcp/org_write`" in notice and "`@orgmcp/write`" not in notice
    team.save_ledger("strays", {"plain": {"paths": ["/x/plain"], "told": False}})
    assert "`@orgmcp/write`" in team.stray_notice("plain")  # not reachable in practice (no built-in write): text unchanged


# Prompts of agents WITHOUT built-in read/write as produced by main before this change (sha256[:16] of the prompt with
# the sandbox path replaced by T): the new text must be byte-identical.
def test_prompts_of_agents_without_built_in_read_write_are_byte_identical_to_before(tmp_path):
    tmp_path = tmp_path.resolve()
    ws = tmp_path / "ws"
    ws.mkdir()
    inp = tmp_path / "in"
    inp.mkdir()
    org = Org.init(tmp_path / "o", "m")
    org.hire(ROOT, "plain", "P", "x")
    org.hire(ROOT, "sh", "S", "x", tools=["shell"], workspace=str(ws))
    org.hire(ROOT, "ro", "S", "x", inputs=[str(inp)])
    got = {a: hashlib.sha256(org.run_prompt(a, []).replace(str(tmp_path), "T").encode()).hexdigest()[:16] for a in ("plain", "sh", "ro")}
    assert got == EXPECTED_HASHES


EXPECTED_HASHES = {'plain': '9702a6f35d3507be', 'sh': '68c442a5689fafa2', 'ro': 'f0e00465fe120e01'}
