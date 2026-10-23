"""A corpus of mutated blueprints, for the characterization of ``validate`` (no test lives here).

``cases(tmp)`` returns ``{name: blueprint}``: the shipped research example, a services-only variant, a code blueprint and a documents
blueprint, each followed by the mutations that make one rule fire. ``golden/validate_corpus.json`` holds what the ``validate`` of
``main`` answered for every case (captured before the validator moved): every issue as ``[level, path, message, code]``, with the
temporary directory written ``<TMP>``. The cases named ``org:...`` are validated against an organization (``ORG_CASES``)."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import yaml

REPO = Path(__file__).resolve().parents[4]
RESEARCH = REPO / "examples" / "blueprint-research.yaml"
GOLDEN = Path(__file__).resolve().parent / "golden" / "validate_corpus.json"
Bp = dict[str, object]

CRITERIA = [
    "At most 600 words as counted by read.",
    'Has exactly the sections "This week" and "Our assessment", in that order.',
    "Every sentence with a number, name, version, date or price cites the URL of the page that states it; the fact-checker fetched that page.",
]


def service(**over: object) -> Bp:
    sv: Bp = {
        "name": "weekly-brief",
        "description": "A one-page, sourced brief on the past week's news about a topic.",
        "inputs": [{"name": "topic", "description": "what the brief is about", "required": True},
                   {"name": "week", "description": "ISO week", "required": False}],
        "acceptance": list(CRITERIA),
        "deliverable": {"description": "One markdown file", "format": "markdown", "max_words": 600},
        "budget": 22,
    }
    sv.update(over)
    return sv


def research(tmp: Path) -> Bp:
    (tmp / "deliverables").mkdir(exist_ok=True)
    bp = cast(Bp, yaml.safe_load(RESEARCH.read_text(encoding="utf-8")))
    cast(Bp, cast(Bp, bp["needs"])["deliverable"])["path"] = str(tmp / "deliverables" / "competitors.md")
    return bp


def services_only(tmp: Path) -> Bp:
    bp = research(tmp)
    cast(Bp, bp["needs"]).pop("deliverable")
    bp.pop("task")
    bp["services"] = [service(deliverable={"description": "One markdown file", "format": "markdown", "max_words": 600,
                                           "path": str(tmp / "deliverables" / "briefs")})]
    return bp


def code(tmp: Path) -> Bp:
    ws = tmp / "proj"
    ws.mkdir(exist_ok=True)
    return {
        "mission": "Build a small CLI that converts CSV to markdown tables.",
        "needs": {
            "scope": "csv2md CLI only; no web UI",
            "deliverable": {"description": "A Python package csv2md with a CLI", "format": "python package"},
            "quality_bar": "tests pass from a clean checkout", "workspace": str(ws), "budget_runs": 30,
            "model_policy": "one model for all", "review": True, "approval": "approve plan first", "progress": "one line on request",
            "code": {"tests": "pytest, one per criterion", "packaging": "uv + pyproject", "commits": "local commits, never push"},
        },
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"}, {"name": "cr", "template": "code-reviewer"}]}],
        "task": {"title": "Build csv2md", "goal": "Implement the csv2md CLI in the workspace",
                 "acceptance": ["`uv run pytest -q` passes with at least 5 tests", "`csv2md in.csv` prints a markdown table to stdout",
                                "the work is committed locally and nothing is pushed"]},
    }


def documents(tmp: Path) -> Bp:
    (tmp / "notes").mkdir(exist_ok=True)
    return {
        "mission": "Turn the meeting notes into a memo.",
        "needs": {"scope": "weekly memo", "kind": "writing", "inputs": [str(tmp / "notes")],
                  "deliverable": {"description": "memo", "format": "markdown", "max_words": 300},
                  "quality_bar": "every action item has an owner", "sources": "the notes only, no web", "budget_runs": 30,
                  "model_policy": "one model for all", "review": True, "approval": "plan", "progress": "on request"},
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "writer", "template": "writer", "tools": ["read"]}, {"name": "reviewer", "template": "reviewer", "tools": ["read"]}]}],
        "task": {"title": "Memo", "goal": "Write the memo",
                 "acceptance": ["At most 300 words as counted by read", "Every action item has an owner"]},
    }


Mutation = Callable[[Bp], object]


def _d(b: object, *keys: str) -> Bp:
    for key in keys:
        b = cast(Bp, b)[key]
    return cast(Bp, b)


def _kids(b: Bp) -> list[Bp]:
    return cast("list[Bp]", cast("list[Bp]", b["agents"])[0]["children"])


def _top(b: Bp) -> Bp:
    return cast("list[Bp]", b["agents"])[0]


def _first_service(b: Bp) -> Bp:
    return cast("list[Bp]", b["services"])[0]


def _tier_mix(b: Bp) -> Bp:
    _d(b, "needs")["models"] = {"cheap": "claude-haiku-4.5", "strong": "claude-sonnet-4.6"}
    _d(b, "needs")["model_policy"] = "cheap drafting, strong review"
    return b


def _service_update(**over: object) -> Mutation:
    return lambda b: _first_service(b).update(over)


def _request(**task: object) -> Mutation:
    return lambda b: b.update(task=task)


# (name, base, mutation). Bases: research (a plain task), services (services only), code, documents.
MUTATIONS: list[tuple[str, str, Mutation]] = [
    ("research:valid", "research", lambda b: None),
    ("services:valid", "services", lambda b: None),
    ("code:valid", "code", lambda b: None),
    ("documents:valid", "documents", lambda b: None),
    ("research:empty", "research", lambda b: (b.clear())),
    ("research:unknown-top-key", "research", lambda b: b.update(color="red")),
    ("research:no-mission", "research", lambda b: b.pop("mission")),
    ("research:no-needs", "research", lambda b: b.pop("needs")),
    ("research:no-task", "research", lambda b: b.pop("task")),
    ("research:task-is-text", "research", lambda b: b.update(task="do it")),
    ("research:unknown-needs-key", "research", lambda b: _d(b, "needs").update(colour="red")),
    ("research:unknown-task-key", "research", lambda b: _d(b, "task").update(colour="red")),
    ("research:no-agents", "research", lambda b: b.pop("agents")),
    ("research:agents-not-a-list", "research", lambda b: b.update(agents="lead")),
    ("research:agent-not-a-mapping", "research", lambda b: b.update(agents=["lead"])),
    ("research:agents-empty", "research", lambda b: b.update(agents=[])),
    ("research:two-tops", "research", lambda b: cast("list[Bp]", b["agents"]).append({"name": "other", "template": "manager"})),
    ("research:bad-name", "research", lambda b: _top(b).update(name="Lead Agent")),
    ("research:reserved-name", "research", lambda b: _top(b).update(name="root")),
    ("research:duplicate-sibling", "research", lambda b: _kids(b).append({"name": "writer", "template": "writer"})),
    ("research:unknown-template", "research", lambda b: _kids(b)[0].update(template="wizard")),
    ("research:no-template-no-charter", "research", lambda b: _kids(b)[0].pop("template")),
    ("research:custom-charter", "research", lambda b: (_kids(b)[0].pop("template"), _kids(b)[0].update(charter="Do the research.", tools=["web_search", "web_fetch"]))),
    ("research:unknown-agent-key", "research", lambda b: _kids(b)[0].update(colour="red")),
    ("research:scale-zero", "research", lambda b: _kids(b)[0].update(scale=0)),
    ("research:scale-text", "research", lambda b: _kids(b)[0].update(scale="2")),
    ("research:scale-two", "research", lambda b: _kids(b)[0].update(scale=2)),
    ("research:max-children-bad", "research", lambda b: _top(b).update(max_children=-1)),
    ("research:max-children-low", "research", lambda b: _top(b).update(max_children=1)),
    ("research:cannot-hire", "research", lambda b: _top(b).update(can_hire=False)),
    ("research:worker-with-children", "research", lambda b: _kids(b)[0].update(children=[{"name": "helper", "template": "researcher"}])),
    ("research:tools-beyond-manager", "research", lambda b: _top(b).update(tools=["read"])),
    ("research:no-deliverable", "research", lambda b: _d(b, "needs").pop("deliverable")),
    ("research:deliverable-text", "research", lambda b: _d(b, "needs").update(deliverable="a report")),
    ("research:deliverable-no-format", "research", lambda b: _d(b, "needs", "deliverable").pop("format")),
    ("research:deliverable-bad-max-words", "research", lambda b: _d(b, "needs", "deliverable").update(max_words=0)),
    ("research:deliverable-unknown-key", "research", lambda b: _d(b, "needs", "deliverable").update(colour="red")),
    ("research:limit-not-in-criteria", "research", lambda b: _d(b, "needs", "deliverable").update(max_words=999)),
    ("research:deliverable-relative-path", "research", lambda b: _d(b, "needs", "deliverable").update(path="out/report.md")),
    ("research:deliverable-outside-roots", "research", lambda b: _d(b, "needs", "deliverable").update(path="/usr/local/report.md")),
    ("research:deliverable-in-kiro", "research", lambda b: _d(b, "needs", "deliverable").update(path="~/.kiro/report.md")),
    ("research:deliverable-parent-missing", "research", lambda b: _d(b, "needs", "deliverable").update(path="<TMP>/missing/dir/report.md")),
    ("research:no-criteria", "research", lambda b: _d(b, "task").pop("acceptance")),
    ("research:criteria-vague", "research", lambda b: _d(b, "task").update(acceptance=["Good quality", "Make it nice and thorough please"])),
    ("research:criteria-as-text", "research", lambda b: _d(b, "task").update(acceptance="- At most 1500 words as counted by read.\n- Covers exactly 5 apps in a table.")),
    ("research:no-title-goal", "research", lambda b: (_d(b, "task").pop("title"), _d(b, "task").pop("goal"))),
    ("research:task-to-worker", "research", lambda b: _d(b, "task").update(to="lead/writer")),
    ("research:task-budget-zero", "research", lambda b: _d(b, "task").update(budget=0)),
    ("research:task-budget-over-cap", "research", lambda b: _d(b, "task").update(budget=30)),
    ("research:task-budget-low", "research", lambda b: _d(b, "task").update(budget=10)),
    ("research:task-budget-tight", "research", lambda b: _d(b, "task").update(budget=19)),
    ("research:no-cap", "research", lambda b: _d(b, "needs").pop("budget_runs")),
    ("research:bad-cap", "research", lambda b: _d(b, "needs").update(budget_runs=0)),
    ("research:low-cap", "research", lambda b: _d(b, "needs").update(budget_runs=12)),
    ("research:no-review-decision", "research", lambda b: _d(b, "needs").pop("review")),
    ("research:review-text-no", "research", lambda b: _d(b, "needs").update(review="no, skip it")),
    ("research:no-verifier", "research", lambda b: _kids(b).pop()),
    ("research:no-author", "research", lambda b: _top(b).update(children=[{"name": "factcheck", "template": "fact-checker"}])),
    ("research:no-web-tools", "research", lambda b: _kids(b)[0].update(tools=[])),
    ("research:partial-web-tools", "research", lambda b: [_kids(b)[0].update(tools=["web_search"]), _kids(b)[2].update(tools=["web_search"])]),
    ("research:verifier-no-web", "research", lambda b: _kids(b)[2].update(template="reviewer", tools=[])),
    ("research:offline-current", "research", lambda b: (_d(b, "needs").update(sources="no web, our notes only"), _d(b, "task").update(goal="Report the latest prices"))),
    ("research:current-facts-no-web", "research", lambda b: (_kids(b)[0].update(tools=[]), _d(b, "needs").update(sources="our notes", quality_bar="latest releases"), _d(b, "task").update(goal="x"))),
    ("research:write-tool-noncode", "research", lambda b: _kids(b)[1].update(tools=["write"])),
    ("research:shell-tool", "research", lambda b: _kids(b)[1].update(tools=["shell"])),
    ("research:read-nothing", "research", lambda b: _kids(b)[2].update(tools=["web_search", "web_fetch", "read"])),
    ("research:model-mix-no-policy", "research", lambda b: (_d(b, "needs").pop("model_policy"), _kids(b)[0].update(model="claude-haiku-4.5"))),
    ("research:tiered-single-model", "research", lambda b: _d(b, "needs").update(model_policy="cheap drafting, strong review")),
    ("research:tiered", "research", _tier_mix),
    ("research:tiered-weak-reviewer", "research", lambda b: (_tier_mix(b), _kids(b)[2].update(model="cheap"), _kids(b)[1].update(model="cheap"))),
    ("research:cheap-lead", "research", lambda b: (_tier_mix(b), _top(b).update(model="cheap"))),
    ("research:lead-shares-drafter-model", "research", lambda b: (_tier_mix(b), _top(b).update(model="claude-haiku-4.5"), _kids(b)[0].update(model="claude-haiku-4.5"))),
    ("research:no-elicited", "research", lambda b: [_d(b, "needs").pop(k) for k in ("scope", "approval", "progress")]),
    ("research:inputs-missing-path", "research", lambda b: _d(b, "needs").update(inputs=["<TMP>/not-there"])),
    ("research:inputs-bad-entry", "research", lambda b: _d(b, "needs").update(inputs=[42])),
    ("research:inputs-not-a-list", "research", lambda b: _top(b).update(inputs=7)),
    ("research:inputs-relative", "research", lambda b: _d(b, "needs").update(inputs=["rel/dir"])),
    ("research:reviewer-told-to-edit", "research", lambda b: _kids(b)[2].update(charter="Apply the corrections directly to the report.")),
    ("research:criterion-told-to-edit", "research", lambda b: cast("list[object]", _d(b, "task")["acceptance"]).append("The fact-checker applies the corrections directly to the report.")),
    ("research:workspace-relative", "research", lambda b: _d(b, "needs").update(workspace="rel/ws")),
    ("research:workspace-new", "research", lambda b: _d(b, "needs").update(workspace="<TMP>/fresh-ws")),
    ("research:workspace-parent-missing", "research", lambda b: _d(b, "needs").update(workspace="<TMP>/no/parent/ws")),
    ("research:workspace-is-a-file", "research", lambda b: _d(b, "needs").update(workspace="<TMP>/deliverables/competitors.md")),
    ("research:write-without-workspace", "research", lambda b: _kids(b)[1].update(tools=["write", "shell"])),
    ("code:no-code-needs", "code", lambda b: _d(b, "needs").pop("code")),
    ("code:no-test-criterion", "code", lambda b: _d(b, "task").update(acceptance=["`csv2md in.csv` prints a markdown table to stdout", "nothing is pushed anywhere"])),
    ("code:no-engineer", "code", lambda b: _top(b).update(children=[{"name": "qa", "template": "tester"}, {"name": "cr", "template": "code-reviewer"}])),
    ("code:kind-writing", "code", lambda b: _d(b, "needs").update(kind="writing")),
    ("code:workspace-in-workspace", "code", lambda b: _kids(b)[0].update(workspace="<TMP>/elsewhere")),
    ("code:workspace-outside-manager", "code", lambda b: (_top(b).update(workspace="<TMP>/proj/inner"), _kids(b)[0].update(workspace="<TMP>/proj"))),
    ("code:manager-without-workspace", "code", lambda b: (_top(b).update(workspace=None), _kids(b)[0].update(workspace="<TMP>/proj"))),
    ("code:input-overlaps-workspace", "code", lambda b: _d(b, "needs").update(inputs=["<TMP>/proj"])),
    ("code:input-overlap-allowed", "code", lambda b: _d(b, "needs").update(inputs=[{"path": "<TMP>/proj", "allow_overlap": True}])),
    ("code:verifier-explicit-inputs", "code", lambda b: _kids(b)[2].update(inputs=[])),
    ("code:input-not-held-by-manager", "code", lambda b: _kids(b)[0].update(inputs=["<TMP>/proj/../notes-elsewhere"])),
    ("code:too-deep", "code", lambda b: _kids(b)[0].update(children=[{"name": "a", "template": "engineer", "children": [{"name": "b", "template": "engineer"}]}])),
    ("documents:valid-read", "documents", lambda b: None),
    ("documents:current-facts-no-web", "documents", lambda b: _d(b, "needs").update(sources="our notes", quality_bar="the latest releases and prices")),
    ("documents:verifier-blind", "documents", lambda b: _kids(b)[1].update(inputs=[])),
    ("documents:reviewer-no-read", "documents", lambda b: _kids(b)[1].update(tools=[])),
    ("documents:writer-write", "documents", lambda b: _kids(b)[0].update(tools=["read", "write"], workspace="<TMP>/notes-out")),
    ("services:no-task", "services", lambda b: None),
    ("services:plain-task-beside", "services", lambda b: b.update(task={"to": "lead", "title": "One-off", "goal": "Do it once"})),
    ("services:unknown-service-key", "services", _service_update(schedule="weekly")),
    ("services:bad-name", "services", _service_update(name="Weekly Brief")),
    ("services:empty-name", "services", _service_update(name="")),
    ("services:owner-worker", "services", _service_update(owner="lead/writer")),
    ("services:owner-top", "services", _service_update(owner="lead")),
    ("services:no-description", "services", _service_update(description="")),
    ("services:description-lines", "services", _service_update(description="two\nlines")),
    ("services:description-long", "services", _service_update(description="x" * 301)),
    ("services:inputs-text", "services", _service_update(inputs="topic")),
    ("services:inputs-bad-name", "services", _service_update(inputs=[{"name": "Topic"}])),
    ("services:inputs-twice", "services", _service_update(inputs=[{"name": "topic"}, {"name": "topic"}])),
    ("services:inputs-unknown-key", "services", _service_update(inputs=[{"name": "topic", "color": "red"}])),
    ("services:acceptance-empty", "services", _service_update(acceptance=[])),
    ("services:acceptance-text", "services", _service_update(acceptance="just words")),
    ("services:acceptance-vague", "services", _service_update(acceptance=["Good quality", *CRITERIA])),
    ("services:no-limit-criterion", "services", _service_update(acceptance=CRITERIA[1:])),
    ("services:told-to-edit", "services", lambda b: cast("list[object]", _first_service(b)["acceptance"]).append("The fact-checker applies the corrections directly to the report.")),
    ("services:deliverable-no-description", "services", _service_update(deliverable={"format": "markdown"})),
    ("services:deliverable-bad-max-words", "services", _service_update(deliverable={"description": "d", "max_words": 0})),
    ("services:deliverable-relative", "services", _service_update(deliverable={"description": "d", "path": "relative/dir"})),
    ("services:deliverable-unknown-key", "services", _service_update(deliverable={"description": "d", "colour": "red"})),
    ("services:deliverable-no-format", "services", _service_update(deliverable={"description": "d"})),
    ("services:deliverable-text", "services", _service_update(deliverable="one file")),
    ("services:deliverable-path-parent", "services", _service_update(deliverable={"description": "d", "format": "md", "path": "<TMP>/nowhere/at/all"})),
    ("services:budget-zero", "services", _service_update(budget=0)),
    ("services:budget-true", "services", _service_update(budget=True)),
    ("services:budget-text", "services", _service_update(budget="lots")),
    ("services:budget-over-cap", "services", _service_update(budget=26)),
    ("services:budget-low", "services", _service_update(budget=10)),
    ("services:budget-tight", "services", _service_update(budget=18)),
    ("services:budget-default", "services", lambda b: _first_service(b).pop("budget")),
    ("services:low-cap-default-budget", "services", lambda b: (_first_service(b).pop("budget"), _d(b, "needs").update(budget_runs=15))),
    ("services:playbook-blank", "services", _service_update(playbook="  ")),
    ("services:playbook-long", "services", _service_update(playbook="word " * 1001)),
    ("services:playbook-ok", "services", _service_update(playbook="## Steps\n1. Do it.")),
    ("services:locked-text", "services", _service_update(locked="yes")),
    ("services:not-a-list", "services", lambda b: b.update(services="weekly-brief")),
    ("services:not-a-mapping", "services", lambda b: b.update(services={"name": "x"})),
    ("services:item-not-a-mapping", "services", lambda b: b.update(services=["x"])),
    ("services:empty", "services", lambda b: b.update(services=[])),
    ("services:duplicate", "services", lambda b: cast("list[Bp]", b["services"]).append(service(description="Another"))),
    ("services:two", "services", lambda b: cast("list[Bp]", b["services"]).append(service(name="daily-digest"))),
    ("services:second-over-cap", "services", lambda b: cast("list[Bp]", b["services"]).append(service(name="daily-digest", budget=40))),
    ("services:request", "services", _request(service="weekly-brief", inputs={"topic": "solid-state batteries"}, title="Brief on batteries")),
    ("services:request-unknown-service", "services", _request(service="nope", inputs={"topic": "x"})),
    ("services:request-missing-input", "services", _request(service="weekly-brief", inputs={"week": "2026-W43"})),
    ("services:request-blank-input", "services", _request(service="weekly-brief", inputs={"topic": "  "})),
    ("services:request-unknown-input", "services", _request(service="weekly-brief", inputs={"topic": "x", "colour": "red"})),
    ("services:request-inputs-list", "services", _request(service="weekly-brief", inputs=["topic"])),
    ("services:request-to-worker", "services", _request(service="weekly-brief", inputs={"topic": "x"}, to="lead/writer")),
    ("services:request-plain-keys", "services", _request(service="weekly-brief", inputs={"topic": "x"}, goal="Do it", acceptance=["x"])),
    ("services:request-bad-inputs-spec", "services", lambda b: (_first_service(b).update(inputs="topic"), b.update(task={"service": "weekly-brief", "inputs": {"topic": "x"}}))),
    ("services:request-no-services", "services", lambda b: (b.pop("services"), b.update(task={"service": "weekly-brief"}))),
    ("services:code-no-test-criterion", "services", lambda b: (_d(b, "needs").update(kind="code", workspace="<TMP>/proj", code={"tests": "pytest"}), _first_service(b).update(description="One feature of the software, tested and committed.", acceptance=["The change is committed locally in the workspace.", "Nothing was pushed to any remote repository."]), _top(b).update(children=[{"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"}, {"name": "cr", "template": "code-reviewer"}]))),
    ("services:no-web-text", "services", lambda b: (_kids(b)[0].update(tools=[]), _kids(b)[1].update(tools=[]), _d(b, "needs").update(sources="the team's own knowledge"))),
]

# What the organization of an ``org:`` case holds: its settings (over the defaults), its top-level agents and the services of ``other``.
ORG_SPECS: dict[str, dict[str, object]] = {
    "org:top-agent-exists": {"agents": ["lead"]},
    "org:service-name-taken": {"agents": ["other"], "services": ["weekly-brief"]},
    "org:workspace-overlaps-org": {},
    "org:max-depth-one": {"config": {"max_depth": 1}},
    "org:small-playbook-cap": {"config": {"playbook_max_words": 5}},
    "org:effort-below-floor": {"config": {"effort": "medium"}},
    "org:default-model-below-floor": {"config": {"default_model": "claude-haiku-4.5"}},
    "org:widened-model-set": {"config": {"extra_allowed_models": ["claude-haiku-4.5", "claude-sonnet-4.6"]}},
}
ORG_CASES: dict[str, tuple[str, Mutation]] = {
    "org:top-agent-exists": ("research", lambda b: None),
    "org:service-name-taken": ("services", lambda b: None),
    "org:workspace-overlaps-org": ("code", lambda b: _d(b, "needs").update(workspace="<ORG>/inside")),
    "org:max-depth-one": ("code", lambda b: None),
    "org:small-playbook-cap": ("services", _service_update(playbook="one two three four five six")),
    "org:effort-below-floor": ("research", lambda b: None),
    "org:default-model-below-floor": ("research", lambda b: _d(b, "needs").pop("models")),
    "org:widened-model-set": ("research", _tier_mix),
}


def _fix(value: object, tmp: Path) -> object:
    """``<TMP>`` in a mutation stands for the temporary directory."""
    return json.loads(json.dumps(value).replace("<TMP>", str(tmp).replace("\\", "\\\\")))


def base_of(kind: str, tmp: Path) -> Bp:
    return {"research": research, "services": services_only, "code": code, "documents": documents}[kind](tmp)


def cases(tmp: Path) -> dict[str, Bp]:
    out: dict[str, Bp] = {}
    for name, kind, mutation in MUTATIONS:
        bp = copy.deepcopy(base_of(kind, tmp))
        mutation(bp)
        out[name] = cast(Bp, _fix(bp, tmp))
    return out


def org_cases(tmp: Path, org_root: Path) -> dict[str, Bp]:
    out: dict[str, Bp] = {}
    for name, (kind, mutation) in ORG_CASES.items():
        bp = copy.deepcopy(base_of(kind, tmp))
        mutation(bp)
        out[name] = cast(Bp, json.loads(json.dumps(_fix(bp, tmp)).replace("<ORG>", str(org_root))))
    return out


def shown(text: str, tmp: Path, org_root: Path | None = None) -> str:
    text = text.replace(str(tmp), "<TMP>")
    return text.replace(str(org_root), "<ORG>") if org_root is not None else text
