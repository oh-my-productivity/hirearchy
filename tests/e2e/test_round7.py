import asyncio
import re
from pathlib import Path

import pytest
import testkit
import yaml
from testkit.cli_world import main
from testkit.e2e_world import ROOT_INSTRUCTIONS, binding_at, bpm, build_server, ex, file_confinement, resolve_binding, skill_source

from orgmcp.core import ROOT, Org


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


@pytest.fixture
def dirs(tmp_path):
    d = {n: (tmp_path / n).resolve() for n in ("docs", "docs/hr", "other", "proj")}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def org(tmp_path, dirs):
    o = Org.init(tmp_path / "org", "round 7", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read"], inputs=[str(dirs["docs"])])
    return o


# ---------------------------------------------------------------------------------------- hire with inputs
def test_root_hire_tool_takes_inputs(org, dirs):
    server = build_server(binding_at(org.root), ROOT)
    assert "hired reader" in call(server, "hire", name="reader", role="R", charter="Read.", tools=["read"], inputs=[str(dirs["docs"])])
    assert org.charter("reader")[0]["inputs"] == [str(dirs["docs"])] and org.inputs_of("reader") == [dirs["docs"]]
    call(server, "hire", name="plain", role="P", charter="Nothing.")  # old calls without inputs keep working
    assert "inputs" not in org.charter("plain")[0]
    assert "absolute path" in fails(server, "hire", name="rel", role="R", charter="x", tools=["read"], inputs=["docs"])
    assert "organization directory" in fails(server, "hire", name="bad", role="R", charter="x", inputs=[str(org.dir("lead"))])


def test_manager_hire_tool_narrows_inputs(org, dirs):
    server = build_server(binding_at(org.root), "lead")
    call(server, "hire", name="kid", role="K", charter="x", tools=["read"], inputs=[str(dirs["docs/hr"])])
    assert org.inputs_of("lead/kid") == [dirs["docs/hr"]]
    assert "inside your inputs or workspace" in fails(server, "hire", name="far", role="F", charter="x", inputs=[str(dirs["other"])])
    assert "cannot grant tools" in fails(server, "hire", name="big", role="B", charter="x", tools=["write"], inputs=[str(dirs["docs"])])


def test_cli_hire_inputs_is_repeatable(org, dirs, capsys):
    main(["--root", str(org.root), "hire", "root", "reader", "--role", "R", "--charter", "Read.", "--tools", "read",
          "--inputs", str(dirs["docs"]), "--inputs", str(dirs["other"])])
    assert org.inputs_of("reader") == [dirs["docs"], dirs["other"]]
    main(["--root", str(org.root), "hire", "root", "plain", "--role", "P", "--charter", "x"])
    assert "inputs" not in org.charter("plain")[0]


KNOWN_WARNINGS = {"path-delivery", "path-parent", "workspace-new", "shell-unconfined"}


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    """The 'user's current directory' the examples build their absolute paths from."""
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    return work


def filled(kind: str, base: Path) -> dict:
    """An example with its path placeholders replaced by real folders (prose placeholders are valid YAML as they are)."""
    for name in ("docs", "data", "proj", "deliverables"):
        (base / name).mkdir(exist_ok=True)
    text = ex.example(kind, base)
    text = (text.replace("<folder-with-your-files>", "docs").replace("<folder-with-your-data>", "data")
            .replace("<project-folder>", "proj").replace("<name>", "result"))
    return yaml.safe_load(text)


def paths_in(text: str) -> set[str]:
    return {p.rstrip(".") for p in re.findall(r"/[\w./-]+", text)}


@pytest.mark.parametrize("kind", ex.KINDS)
def test_plan_and_access_line_show_exactly_the_applied_confinement(kind, cwd, tmp_path):
    bp = filled(kind, cwd)
    roots = [tmp_path]
    agents = {a.addr: a for a in bpm._resolve(bp, None, roots, [])}
    o = Org.init(tmp_path / "org", "x", {"poll_seconds": 0.05})
    bpm.apply(o, bp, allowed_roots=roots)
    shells = 0
    for addr, agent in agents.items():
        tools = o.charter(addr)[0].get("tools") or []
        _, settings = file_confinement(o.root, tools, o.workspace_of(addr), o.inputs_of(addr))
        enforced = set()
        for rule in settings.values():
            enforced |= {p[:-3] if p.endswith("/**") else p for p in rule["allowedPaths"]}
        # built-in read also reaches the organization's own files; the plan says so in words (no path: it does not exist yet)
        assert ("read" in tools) == (str(o.root) in enforced), addr
        enforced.discard(str(o.root))
        plan, technical = bpm._agent_access(agent), bpm._access(agent)
        if "read" in tools:
            assert "organization" in plan and "organization" in technical, (addr, plan, technical)
        told = {str(o.workspace_of(addr))} if "shell" in tools and o.workspace_of(addr) else set()
        if "read" not in tools:  # no built-in read: the inputs are opened with orgmcp `read` by absolute path
            told |= set(map(str, o.inputs_of(addr)))
        for line in (plan, technical):
            assert paths_in(line) == enforced | told, (addr, line, enforced)
            assert ("NOT confined" in line) == ("shell" in tools), (addr, line)
        shells += "shell" in tools
        assert ("write" in tools) == ("changes files only in" in plan), (addr, plan)
        if "write" not in tools and "shell" not in tools:
            assert "cannot change your files" in plan
    # code: engineer, tester, code-reviewer; analysis: analyst, data-checker; and the manager holding what they hold
    assert shells == {"code": 4, "analysis": 3}.get(kind, 0)


def test_plan_words_for_each_access_shape():
    def line(**kw):
        return bpm._agent_access(bpm.Agent(addr="a", name="a", parent=None, where="agents[a]", **kw))
    assert line(tools=["read"], inputs=["/in"]) == "can read files only in /in and the organization's own files; cannot change your files"
    assert line(tools=["read"]) == "can read no files outside the organization; cannot change your files"
    assert line(tools=[]) == "cannot change your files"
    assert line(tools=["web_search", "web_fetch"]) == "can search the web and read web pages; cannot change your files"
    assert line(tools=[], inputs=["/in"]) == "can read /in through the organization's read tool; cannot change your files"
    assert line(tools=["read", "write"], workspace="/ws", inputs=["/in"]) \
        == "can read files in /ws, /in (/in read-only) and the organization's own files; changes files only in /ws"
    assert line(tools=["write"]) == "changes no files (no workspace)"
    shell = line(tools=["read", "shell", "write"], workspace="/ws")
    assert shell.startswith("can read files in /ws and the organization's own files; changes files only in /ws; can run commands, which are NOT confined")
    assert "told to stay in /ws" in shell and "cannot change your files" not in shell
    manager = line(tools=["read"], inputs=["/in"], kind="manager", children=["a/k"])
    assert manager == "directs the team; does not produce the work itself; can read files only in /in and the organization's own files; cannot change your files"
    assert line(tools=[], kind="manager", children=["a/k"]) == "directs the team; does not produce the work itself"


# ------------------------------------------------------------- blueprint_example kinds pass propose_org
EXAMPLES_DIR = testkit.REPO / "examples"


@pytest.fixture
def root_server(tmp_path, cwd, monkeypatch):
    for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "org"))
    return build_server(*resolve_binding())


def fill_text(server, kind: str, base: Path) -> str:
    """What the assistant does: fetch the example and replace the placeholders it needs with the user's values."""
    for name in ("docs", "data", "proj", "deliverables"):
        (base / name).mkdir(exist_ok=True)
    text = call(server, "blueprint_example", kind=kind)
    return (text.replace("<folder-with-your-files>", "docs").replace("<folder-with-your-data>", "data")
            .replace("<project-folder>", "proj").replace("<name>", "result"))


@pytest.mark.parametrize("kind", ex.KINDS)
def test_every_example_kind_proposes_cleanly_once_filled(kind, root_server, cwd):
    out = call(root_server, "propose_org", blueprint=fill_text(root_server, kind, cwd))
    assert bpm.PLAN_HEADING in out and bpm.PLAN_DRAFT_HEADING not in out
    assert re.search(r"^plan_id: [0-9a-f]{12}$", out, re.M) and "Errors (" not in out
    codes = {i.code for i in bpm.validate(yaml.safe_load(fill_text(root_server, kind, cwd)), allowed_roots=[cwd.parent])}
    assert codes <= KNOWN_WARNINGS, codes  # in particular no `unknown-key`: needs.inputs is a known key


def test_documents_example_with_its_placeholder_folder_is_a_draft_that_names_the_folder(root_server, cwd):
    out = call(root_server, "propose_org", blueprint=call(root_server, "blueprint_example", kind="documents"))
    assert bpm.PLAN_DRAFT_HEADING in out and "folder-with-your-files" in out and re.search(r"^plan_id: none", out, re.M)


def test_example_criteria_match_the_exhaustive_verifier_templates(root_server, cwd):
    for kind, needle in (("research", "n of m factual claims verified' with n = m"), ("documents", "criteria met: n of m with n = m"),
                         ("analysis", "Figures checked: n of m match' with n = m")):
        criteria = yaml.safe_load(fill_text(root_server, kind, cwd))["task"]["acceptance"]
        assert any(needle in c for c in criteria), kind
        assert not any("at least 6" in c for c in criteria), kind
    assert "at least 6" not in (EXAMPLES_DIR / "blueprint-research.yaml").read_text()
    research = yaml.safe_load((EXAMPLES_DIR / "blueprint-research.yaml").read_text())
    assert any("n of m factual claims verified' with n = m" in c for c in research["task"]["acceptance"])
    # the wording asks for what the templates report
    assert "n of m factual claims verified" in bpm.get_role("fact-checker").body and "criteria met: n of m" in bpm.get_role("reviewer").body
    assert "Figures checked: n of m match" in bpm.get_role("data-checker").body


# ------------------------------------------------------------------------------ skill and instructions
def test_skill_and_instructions_mention_read_only_inputs_within_the_limits(root_server):
    skill = skill_source().read_text()
    assert len(skill.splitlines()) <= 125 and len(ROOT_INSTRUCTIONS) < 2800
    for needle in ("`needs.inputs`", "can never change them", "never give an agent the built-in `write` tool",
                   "copy the deliverable", "NOT confined", "n of m, n = m"):
        assert needle in skill, needle
    assert "at least 6" not in skill and "never ask for \"at least N\"" in skill
    assert "`needs.inputs` (read-only)" in root_server.instructions and "built-in `write` only for code" in root_server.instructions


def test_readme_documents_the_integrated_features():
    readme = (testkit.REPO / "README.md").read_text()
    for needle in ("hire ... --inputs PATH", "`inputs` parameter of the `hire` tool", "`plan_id`", "blueprint_example(kind)",
                   "progress(wait_seconds=N)", "--until-done", "n of m factual claims verified (n = m required); k wrong, u unsupported, p not-checkable; j judgement statements, each resting on verified facts: yes",
                   "`code-reviewer` now has `read` and `shell`", "`manager` verifies with its own `read` output",
                   "relevance over length", "same\n   computation as the `Access:` line"):
        assert needle in readme, needle
    assert readme.count("<<<<<<<") == 0 and "at least 6" not in readme
