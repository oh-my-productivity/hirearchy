"""The org-agent floor, end to end (docs/design/org-agent-model-floor.md, owner decision D-E4-9): every org-agent run passes ``--effort`` (``high``
unless ORG.md says ``xhigh`` or ``max``), the allowed models are claude-sonnet-5.5 and claude-opus-5.5 (only the user widens the set), and an agent
that already runs below the floor keeps running and is named to root. The scheduler runs against the stub kiro-cli of the ``isolated_kiro`` fixture;
the calls under test go through the in-process MCP servers. Every test builds its own organization in its own ``tmp_path``.
"""

import asyncio
import re
import time

import pytest
import testkit
import yaml
from testkit.e2e_world import build_server
from testkit.health_world import Scheduler
from testkit.kiro_world import kiro_runner
from testkit.mcp_server_world import OrgBinding
from testkit.mcp_server_world import build_server as build_setup_server

from hirearchy.core import ROOT
from hirearchy.kernel import join_frontmatter, split_frontmatter

ALLOWED = "allowed: claude-sonnet-5.5, claude-opus-5.5"
MODELS = [("claude-haiku-4.5", False), ("claude-sonnet-4.6", False), ("claude-sonnet-5.5", True), ("claude-opus-5.5", True)]


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


def run_to_idle(sched, limit=5.0):
    deadline = time.time() + limit
    while sched.tick() and time.time() < deadline:
        time.sleep(0.01)


def run_ceo(org) -> str:
    """One scheduler run of ``ceo`` with the default runner (the stub kiro-cli); the text of its run log."""
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    sched = Scheduler(org, echo=lambda _: None)
    sched.acquire()
    try:
        run_to_idle(sched)
    finally:
        sched.release()
    first = sorted((org.dir("ceo") / "runs").glob("*.log"))[0]  # a failed run is retried: several logs, all alike
    return first.read_text(encoding="utf-8")


def pin_model(org, addr: str, model: str) -> None:
    """A charter written before the floor: ``model`` is put in its AGENT.md directly, behind ``hire`` and ``write``."""
    path = org.dir(addr) / "AGENT.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, "model": model}, body), encoding="utf-8")


def test_a_scheduler_run_passes_effort_high_and_its_run_log_shows_it(org, isolated_kiro):
    log = run_ceo(org)
    cmd = next(line for line in log.splitlines() if line.startswith("# cmd:"))
    assert "--model claude-sonnet-5.5 --effort high --v3" in cmd
    assert "--model claude-sonnet-5.5 --effort high --v3" in (isolated_kiro / "kiro-stub.log").read_text()


def test_an_effort_below_high_in_ORG_md_refuses_every_run(org, isolated_kiro):
    path = org.root / "ORG.md"
    path.write_text(path.read_text(encoding="utf-8").replace("effort: high", "effort: medium"), encoding="utf-8")
    log = run_ceo(org)
    assert '# failed to start: kiro: effort "medium" is not allowed for org agents; allowed: high, xhigh, max' in log
    stub = isolated_kiro / "kiro-stub.log"  # no kiro-cli ran at all, so there may be no log
    assert "chat --no-interactive" not in (stub.read_text() if stub.exists() else "")


def test_an_agent_that_existed_below_the_floor_keeps_its_model(org, isolated_kiro):
    pin_model(org, "ceo/eng", "claude-haiku-4.5")
    argv, _, _ = kiro_runner()(org, "ceo/eng", "P")  # no refusal and no substitution
    assert "--model claude-haiku-4.5 --effort high" in " ".join(argv)


# ------------------------------------------------------------------------------------------------ the refusal points


def point_hire(org, model: str) -> str | None:
    """Root hires an agent on ``model`` through its MCP server: the refusal, or None when the agent exists with that model."""
    name = f"x-{slug(model)}"  # one agent per model, so a test may hire on several
    try:
        call(build_server(org, ROOT), "hire", name=name, role="X", charter="x", model=model)
    except Exception as error:
        return str(error)
    meta, _ = split_frontmatter((org.dir(name) / "AGENT.md").read_text(encoding="utf-8"))
    assert meta["model"] == model
    return None


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", model)


def point_create_org(org, model: str) -> str | None:
    """A setup-mode root creates an organization with ``default_model=model``: the refusal, or None when ORG.md says so."""
    target = org.root.parent / f"created-{slug(model)}"
    server = build_setup_server(OrgBinding(target, None, pinned=True), ROOT)
    try:
        call(server, "create_org", mission="m", default_model=model)
    except Exception as error:
        assert not (target / "ORG.md").exists()
        return str(error)
    meta, _ = split_frontmatter((target / "ORG.md").read_text(encoding="utf-8"))
    assert meta["default_model"] == model
    return None


def point_charter_rewrite(org, model: str) -> str | None:
    """Root rewrites the charter of ``ceo`` through its MCP ``write``, setting ``model``: the refusal, or None when the charter says so."""
    meta, body = split_frontmatter((org.dir("ceo") / "AGENT.md").read_text(encoding="utf-8"))
    try:
        call(build_server(org, ROOT), "write", path="ceo/AGENT.md", content=join_frontmatter({**meta, "model": model}, body))
    except Exception as error:
        return str(error)
    assert split_frontmatter((org.dir("ceo") / "AGENT.md").read_text(encoding="utf-8"))[0]["model"] == model
    return None


def point_org_md_default_model(org, model: str) -> str | None:
    """Root rewrites ORG.md through its MCP ``write`` with ``default_model: model``: the refusal, or None when ORG.md says so."""
    meta, body = split_frontmatter((org.root / "ORG.md").read_text(encoding="utf-8"))
    try:
        call(build_server(org, ROOT), "write", path="ORG.md", content=join_frontmatter({**meta, "default_model": model}, body))
    except Exception as error:
        return str(error)
    assert split_frontmatter((org.root / "ORG.md").read_text(encoding="utf-8"))[0]["default_model"] == model
    return None


def point_blueprint(mutate):
    """The shipped research blueprint with ``model`` put in by ``mutate``, proposed by root: the DRAFT text with its errors, or None when it is ready."""

    def point(org, model: str) -> str | None:
        bp = yaml.safe_load((testkit.REPO / "examples" / "blueprint-research.yaml").read_text(encoding="utf-8"))
        mutate(bp, model)
        out = call(build_server(org, ROOT), "propose_org", blueprint=yaml.safe_dump(bp, sort_keys=False))
        return out if "DRAFT - NOT READY" in out else None

    return point


def set_tiers(bp, model: str) -> None:
    bp["needs"]["models"] = {"cheap": model, "strong": model}


def set_lead_model(bp, model: str) -> None:
    bp["agents"][0]["model"] = model


POINTS = {
    "hire": point_hire,
    "blueprint tier": point_blueprint(set_tiers),
    "blueprint agent model": point_blueprint(set_lead_model),
    "create_org default_model": point_create_org,
    "charter rewrite": point_charter_rewrite,
    "ORG.md default_model": point_org_md_default_model,
}


@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("model, admitted", MODELS)
def test_each_refusal_point_refuses_or_admits(org, point, model, admitted):
    refusal = POINTS[point](org, model)
    if admitted:
        assert refusal is None
    else:
        assert refusal is not None and f'model "{model}" is not allowed' in refusal and ALLOWED in refusal


def widen(org, *ids: str) -> None:
    """The user widens the set by editing ORG.md by hand."""
    path = org.root / "ORG.md"
    path.write_text(path.read_text(encoding="utf-8").replace("effort: high", f"effort: high\nextra_allowed_models: [{', '.join(ids)}]"), encoding="utf-8")


def test_a_widened_set_admits_another_model(org):
    assert point_hire(org, "claude-sonnet-4.6") is not None
    assert point_charter_rewrite(org, "claude-sonnet-4.6") is not None
    widen(org, "claude-sonnet-4.6")
    assert point_hire(org, "claude-sonnet-4.6") is None
    assert point_charter_rewrite(org, "claude-sonnet-4.6") is None  # a root rewrite admits it after the hand edit
    assert point_org_md_default_model(org, "claude-sonnet-4.6") is None
    assert point_blueprint(set_tiers)(org, "claude-sonnet-4.6") is None  # and a plan with that tier is ready
    assert point_hire(org, "claude-haiku-4.5") is not None  # still outside the widened set


def test_root_cannot_widen_the_set_through_write(org):
    server = build_server(org, ROOT)
    meta, body = split_frontmatter((org.root / "ORG.md").read_text(encoding="utf-8"))
    before = (org.root / "ORG.md").read_text(encoding="utf-8")
    message = fails(server, "write", path="ORG.md", content=join_frontmatter({**meta, "extra_allowed_models": ["claude-haiku-4.5"]}, body))
    assert "only the user can widen the allowed models, by editing ORG.md themselves" in message and "claude-haiku-4.5" in message
    assert (org.root / "ORG.md").read_text(encoding="utf-8") == before
    assert point_hire(org, "claude-haiku-4.5") is not None  # and the set is the same as before


def test_root_cannot_lower_the_effort_through_write(org):
    meta, body = split_frontmatter((org.root / "ORG.md").read_text(encoding="utf-8"))
    message = fails(build_server(org, ROOT), "write", path="ORG.md", content=join_frontmatter({**meta, "effort": "medium"}, body))
    assert 'effort "medium" is not allowed for org agents; allowed: high, xhigh, max' in message
    assert split_frontmatter((org.root / "ORG.md").read_text(encoding="utf-8"))[0]["effort"] == "high"


def test_root_repairs_an_ORG_md_with_broken_yaml_and_still_rewrites_charters(org):
    (org.root / "ORG.md").write_text("---\nmax_depth: 4\nextra_allowed_models: [claude-sonnet-4.6\n---\n# Organization\n", encoding="utf-8")
    server = build_server(org, ROOT)
    charter = join_frontmatter({"role": "CEO", "model": "claude-opus-5.5"}, "# Role\n\nNew body.")
    call(server, "write", path="ceo/AGENT.md", content=charter)  # a charter rewrite does not need ORG.md to parse
    assert "model: claude-opus-5.5" in (org.dir("ceo") / "AGENT.md").read_text(encoding="utf-8")
    message = fails(server, "write", path="ORG.md", content=join_frontmatter({"max_depth": 4, "effort": "medium"}, "# Organization\n"))
    assert 'effort "medium" is not allowed for org agents' in message  # the repair is checked against the built-in floor
    fixed = join_frontmatter({"max_depth": 4}, "# Organization\n")
    call(server, "write", path="ORG.md", content=fixed)
    assert (org.root / "ORG.md").read_text(encoding="utf-8") == fixed


# ------------------------------------------------------------------------------------ ORG.md whose settings block cannot be parsed

BROKEN_ORG_MD = "---\nmax_depth: 4\nextra_allowed_models: [claude-sonnet-4.6\n---\n# Organization\n"  # the hand edit of the widening channel slipped
PARSER_TEXT = re.compile(r"while (parsing|scanning)|ParserError|ScannerError|did not find expected|<unicode string>")  # what YAML says, never the user's to read


def break_org_md(org) -> None:
    (org.root / "ORG.md").write_text(BROKEN_ORG_MD, encoding="utf-8")


def test_root_status_and_whoami_answer_while_ORG_md_cannot_be_parsed(org):
    """As before the floor: the skill's first step (whoami / status) must not stop at a parser error; no agent is claimed to be below an unknown set."""
    pin_model(org, "ceo/eng", "claude-haiku-4.5")
    break_org_md(org)
    root = build_server(org, ROOT)
    assert "root (human)" in call(root, "status") and "eng [Engineer]" in call(root, "status")
    assert "Address: `root`" in call(root, "whoami")
    for tool in ("status", "whoami"):
        assert "Model floor" not in call(root, tool)
    (org.root / "ORG.md").write_text("---\nmax_depth: 4\n---\n# Organization\n", encoding="utf-8")  # repaired: the agent is named again
    assert FLOOR_NOTE in call(root, "status")


def test_a_run_is_built_with_effort_high_while_ORG_md_cannot_be_parsed(org, isolated_kiro):
    """The run command of an agent whose charter names its model needs nothing else of ORG.md: it is neither refused nor skipped."""
    pin_model(org, "ceo/eng", "claude-opus-5.5")
    break_org_md(org)
    argv, _, _ = kiro_runner()(org, "ceo/eng", "P")
    assert "--model claude-opus-5.5 --effort high --v3" in " ".join(argv)


def research_blueprint() -> str:
    return (testkit.REPO / "examples" / "blueprint-research.yaml").read_text(encoding="utf-8")


def plan_id_of(server, text: str) -> str:
    return re.search(r"^plan_id: (\w+)$", call(server, "propose_org", blueprint=text), re.M).group(1)


BROKEN_CALLS = {  # label: (tool, arguments of the call given the plan_id of the research blueprint, what its refusal says; None = the call answers)
    "status": ("status", lambda pid: {}, None),
    "whoami": ("whoami", lambda pid: {}, None),
    "hire with a model": ("hire", lambda pid: dict(name="ops", role="Ops", charter="c", model="claude-opus-5.5"), "ORG.md cannot be read"),
    "hire without a model": ("hire", lambda pid: dict(name="ops", role="Ops", charter="c"), "ORG.md cannot be read"),
    "charter rewrite to a floor model": (
        "write", lambda pid: dict(path="ceo/AGENT.md", content="---\nrole: CEO\nmodel: claude-opus-5.5\n---\nNew body.\n"), None),
    "charter rewrite below the floor": (
        "write", lambda pid: dict(path="ceo/AGENT.md", content="---\nrole: CEO\nmodel: claude-haiku-4.5\n---\nNew body.\n"),
        'model "claude-haiku-4.5" is not allowed'),
    "ORG.md repair": ("write", lambda pid: dict(path="ORG.md", content="---\nmax_depth: 4\n---\n# Organization\n"), None),
    "ORG.md repair that widens the set": (
        "write", lambda pid: dict(path="ORG.md", content="---\nmax_depth: 4\nextra_allowed_models: [claude-haiku-4.5]\n---\nx\n"),
        "only the user can widen the allowed models"),
    "ORG.md repair below the floor": (
        "write", lambda pid: dict(path="ORG.md", content="---\nmax_depth: 4\neffort: medium\n---\nx\n"), 'effort "medium" is not allowed'),
    "propose_org": ("propose_org", lambda pid: dict(blueprint=research_blueprint()), "ORG.md cannot be read"),
    "apply_org": (
        "apply_org", lambda pid: dict(blueprint=research_blueprint(), approved=True, plan_id=pid), "ORG.md cannot be read"),
    "blueprint_example": ("blueprint_example", lambda pid: dict(kind="research"), None),
}


@pytest.mark.parametrize("label", BROKEN_CALLS)
def test_no_root_tool_of_the_floor_shows_a_yaml_error_while_ORG_md_cannot_be_parsed(org, label):
    """Every root call the floor touches (status, whoami, hire, write, propose_org, apply_org ...): it answers, or refuses in words that do not
    quote the parser; one that needs ORG.md says so by name, and the floor still holds."""
    tool, make_args, refusal = BROKEN_CALLS[label]
    root = build_server(org, ROOT)
    pid = plan_id_of(root, research_blueprint())  # the plan the user approved, before the slip
    break_org_md(org)
    args = make_args(pid)
    if refusal is None:
        text = call(root, tool, **args)
    else:
        text = fails(root, tool, **args)
        assert refusal in text
    assert not PARSER_TEXT.search(text), text
    assert not (org.dir("ops") / "AGENT.md").exists()  # nothing was hired


def test_create_org_on_a_root_with_an_ORG_md_that_cannot_be_parsed_says_it_is_one(org):
    break_org_md(org)
    server = build_setup_server(OrgBinding(org.root, None, pinned=True), ROOT)
    text = fails(server, "create_org", mission="m")
    assert not PARSER_TEXT.search(text), text


def test_a_blueprint_tier_outside_the_set_is_an_error_line_of_the_draft(org):
    out = point_blueprint(set_tiers)(org, "claude-haiku-4.5")
    assert out is not None and 'needs.models.cheap: model "claude-haiku-4.5" is not allowed' in out and "needs.models.strong:" in out
    assert "PLAN FOR YOU" not in out.split("DRAFT - NOT READY")[0]  # nothing to show the user yet


def test_a_blueprint_with_the_widened_set_is_ready(org):
    assert point_blueprint(set_tiers)(org, "claude-sonnet-4.6") is not None
    widen(org, "claude-sonnet-4.6")
    assert point_blueprint(set_tiers)(org, "claude-sonnet-4.6") is None


FLOOR_NOTE = (
    "Model floor: below the allowed models (claude-sonnet-5.5, claude-opus-5.5): ceo/eng on claude-haiku-4.5. Fix: set model: claude-sonnet-5.5 in "
    "each one's AGENT.md (you for your direct reports, the manager for the others); they keep running as they are until then."
)


def test_root_status_and_whoami_name_an_existing_agent_below_the_floor(org):
    pin_model(org, "ceo/eng", "claude-haiku-4.5")  # an agent made before the floor
    root, ceo = build_server(org, ROOT), build_server(org, "ceo")
    for tool in ("status", "whoami"):
        text = call(root, tool)
        assert FLOOR_NOTE in text and len([line for line in text.splitlines() if line.startswith("Model floor")]) == 1
        assert "Model floor" not in call(ceo, tool)  # the agents are not told
    # the agent keeps its model (nothing is substituted), and the line is gone once its model is allowed
    assert "--model claude-haiku-4.5" in " ".join(kiro_runner()(org, "ceo/eng", "P")[0])
    call(ceo, "write", path="ceo/eng/AGENT.md", content="---\nrole: Engineer\nmodel: claude-sonnet-5.5\n---\nBuild things.\n")  # the manager's fix
    for tool in ("status", "whoami"):
        assert "Model floor" not in call(root, tool)
