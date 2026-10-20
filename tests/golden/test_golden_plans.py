"""Golden: ``propose_org`` text (PLAN FOR YOU + details + plan_id) for the shipped examples and every ``blueprint_example``."""

import asyncio
import re
from pathlib import Path

import pytest
from golden_support import check

from orgmcp.blueprint import EXAMPLE_KINDS
from orgmcp.server import OrgBinding, build_server

PROJECT = Path(__file__).resolve().parents[2]
PLAN_ID = re.compile(r"[0-9a-f]{12}")


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


@pytest.fixture
def cwd(tmp_path, monkeypatch, norm):
    """The user's current directory: where the templates put ``deliverables/`` and project folders."""
    d = tmp_path / "cwd"
    d.mkdir()
    for name in ("docs", "data", "proj"):
        (d / name).mkdir()
    monkeypatch.chdir(d)
    norm.add(d, "<CWD>")
    return d


def root_server(gorg):
    return build_server(gorg, "root")


def scrub_ids(text: str) -> str:
    """plan_id is a hash of the blueprint, which holds tmp paths for the templates: the value is not golden there."""
    return re.sub(r"plan_id(: |=\")" + PLAN_ID.pattern, lambda m: f"plan_id{m.group(1)}<PLAN_ID>", text)


@pytest.mark.parametrize("name", ["blueprint-research", "blueprint-service"])
def test_propose_org_for_the_shipped_examples(name, gorg, cwd, norm):
    text = (PROJECT / "examples" / f"{name}.yaml").read_text(encoding="utf-8")
    out = norm(call(root_server(gorg), "propose_org", blueprint=text))
    check(f"plans/example_{name}.txt", out)  # the plan_id is exact here: the example holds no tmp path
    assert re.search(r"plan_id: [0-9a-f]{12}", out)


def test_propose_org_without_an_organization(tmp_path, cwd, norm):
    text = (PROJECT / "examples" / "blueprint-research.yaml").read_text(encoding="utf-8")
    where = tmp_path / "later" / "org"
    norm.add(where, "<FUTURE_ORG>")
    server = build_server(OrgBinding(where, None, pinned=True), "root")
    check("plans/example_blueprint-research_no_org.txt", norm(call(server, "propose_org", blueprint=text)))


def fill(text: str) -> str:
    """What the assistant does with a template: every placeholder gets the user's (here: a fixed) value."""
    for placeholder, value in (("<folder-with-your-files>", "docs"), ("<folder-with-your-data>", "data"),
                               ("<project-folder>", "proj"), ("<name>", "briefs"), ("<service-name>", "my-service"),
                               ("<input-name>", "topic"), ("<PLACEHOLDER>", "x")):
        text = text.replace(placeholder, value)
    return re.sub(r"<[A-Z][^<>\n]*>", "Sample text", text)


CASES = [(kind, service) for kind in EXAMPLE_KINDS for service in (False, True)]


@pytest.mark.parametrize("kind, service", CASES, ids=[f"{k}{'-service' if s else ''}" for k, s in CASES])
def test_blueprint_example_templates_and_their_plans(kind, service, gorg, cwd, norm):
    server = root_server(gorg)
    label = f"{kind}{'_service' if service else ''}"
    template = call(server, "blueprint_example", kind=kind, service=service)
    check(f"plans/template_{label}.yaml", norm(template))
    check(f"plans/propose_raw_template_{label}.txt", scrub_ids(norm(call(server, "propose_org", blueprint=template))))
    check(f"plans/propose_filled_template_{label}.txt", scrub_ids(norm(call(server, "propose_org", blueprint=fill(template)))))


def test_blueprint_example_default_arguments(gorg, cwd, norm):
    server = root_server(gorg)
    assert call(server, "blueprint_example") == call(server, "blueprint_example", kind="research", service=False)
