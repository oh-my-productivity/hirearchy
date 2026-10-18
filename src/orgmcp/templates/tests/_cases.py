"""The fixed inputs of the GOLDEN-text tests and the names of the files that hold their expected output.

``expected/<case>.txt`` was captured from the module ``orgmcp/templates.py`` as it was before it became a package (step
A-templates), by calling the legacy function listed in ``LEGACY_NAME`` with these arguments, and is never regenerated: the
templates are the text the runtime writes into ORG.md, charters, messages and notices, so a changed byte is a changed behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

EXPECTED = Path(__file__).resolve().parent / "expected"

LONG_ARTIFACTS = ["ceo/eng/work/api.md", "ceo/eng/work/tests.md"]
FLAGS = ["stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle"]


@dataclass(frozen=True)
class Case:
    """One call of one template with fixed arguments."""

    name: str
    port: str  # "documents" (DocumentTemplates) or "notices" (Notices)
    method: str
    args: tuple[object, ...] = ()
    kwargs: dict[str, object] = field(default_factory=dict)


# the legacy function of orgmcp.templates that each method of the Protocols replaces (ARCHITECTURE.md 5.13)
LEGACY_NAME = {
    "org_rules": "org_rules",
    "charter_body": "charter_body",
    "task_body": "task_body",
    "result_body": "result_body",
    "budget": "notice_budget",
    "budget_returned": "notice_budget_returned",
    "failures": "notice_failures",
    "nudge": "notice_nudge",
    "stalled": "notice_stalled",
    "review_item": "review_item",
    "review_manager": "notice_review_manager",
    "review_root": "notice_review_root",
}

DOCUMENT_CASES = [
    Case("org_rules_mission", "documents", "org_rules", ("Build the best research desk.",)),
    Case("org_rules_padded_mission", "documents", "org_rules", ("  \n  Ship it.  \n\n",)),
    Case("org_rules_none", "documents", "org_rules", (None,)),
    Case("org_rules_empty", "documents", "org_rules", ("",)),
    Case("org_rules_blank", "documents", "org_rules", ("   \n",)),
    Case("charter_plain", "documents", "charter_body", ("Builder", "Build things.")),
    Case("charter_padded", "documents", "charter_body", ("Builder", "\n\n  Build things.  \n\n")),
    Case("charter_with_heading", "documents", "charter_body", ("Builder", "# Chief Builder\n\nBuild things.\n")),
    Case("charter_with_h2_only", "documents", "charter_body", ("Builder", "## Duties\n\nBuild things.")),
    Case("task_with_inputs", "documents", "task_body", ("Write the API.", "- 3 endpoints\n- under 200 words", ["ceo/spec.md", "ceo/notes.md"])),
    Case("task_without_inputs", "documents", "task_body", ("  Write the API.  ", "  - 3 endpoints  ", [])),
    Case("result_summary_only", "documents", "result_body", ("Done: 3 endpoints.", [])),
    Case("result_with_artifacts", "documents", "result_body", ("Done.", LONG_ARTIFACTS)),
    Case("result_with_lessons", "documents", "result_body", ("Done.", [], "Ask for the schema first.")),
    Case("result_with_everything", "documents", "result_body", ("  Done.  ", LONG_ARTIFACTS, "  Ask for the schema first.  ")),
    Case("result_blank_lessons", "documents", "result_body", ("Done.", ["ceo/eng/work/api.md"], "   ")),
]

NOTICE_CASES = [
    Case("budget", "notices", "budget", ("ceo/eng", 3)),
    Case("budget_returned", "notices", "budget_returned", ("ceo/eng", 4, "ceo", "finished early")),
    Case("failures_to_human", "notices", "failures", ("ceo/eng", 3, "ceo/eng/runs/20260115T090000000000.log")),
    Case("failures_to_parent", "notices", "failures", ("ceo/eng", 3, "ceo/eng/runs/20260115T090000000000.log"), {"to_human": False}),
    Case("nudge", "notices", "nudge", ("T-1", "Build the API")),
    Case("stalled_one", "notices", "stalled", ("ceo/eng", "T-1", "Build the API", ["ceo"])),
    Case("stalled_chain", "notices", "stalled", ("ceo/eng", "T-1", "Build the API", ["ceo/eng", "ceo", "root"])),
    *[Case(f"review_item_{flag}", "notices", "review_item", ("ceo/eng", flag, "no result for 2h")) for flag in FLAGS],
    *[Case(f"review_item_{flag}_no_act", "notices", "review_item", ("ceo/eng", flag, "no result for 2h"), {"act": False}) for flag in FLAGS],
    Case("review_item_branch", "notices", "review_item", ("ceo/eng/qa", "expensive", "9 runs"), {"branch": "ceo"}),
    Case("review_item_branch_no_act", "notices", "review_item", ("ceo/eng/qa", "idle", "nothing for 3 days"), {"act": False, "branch": "ceo"}),
    Case("review_manager_one", "notices", "review_manager", ("ceo", ["- `ceo/eng` idle: nothing for 3 days\n  -> retire `ceo/eng` if it is no longer needed"])),
    Case("review_manager_two", "notices", "review_manager", ("ceo", ["- `ceo/eng` idle: x", "- `ceo/qa` stuck: y"])),
    Case("review_root", "notices", "review_root", ("2 agents flagged", ["- `ceo/eng` idle: x", "- `ceo/qa` stuck: y"], {})),
    Case("review_root_skipped", "notices", "review_root", ("1 agent flagged", ["- `ceo/eng` idle: x"], {"ceo": "paused", "cto": "out of budget"})),
]

CASES = [*DOCUMENT_CASES, *NOTICE_CASES]

# kiro_profile stays in templates until step B-kiro moves it; its output is golden too (as indented JSON, keys in insertion order).
KIRO_PROFILE_ARGS: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {
    "kiro_profile_plain": (
        ("orgmcp-ceo", "agent ceo", ["@orgmcp"], {"command": "orgmcp", "args": ["mcp"], "env": {"ORG_ROOT": "/org", "ORG_AGENT": "ceo"}}), {},
    ),
    "kiro_profile_allowed": (
        ("orgmcp-ceo-eng", "agent ceo/eng", ["@orgmcp", "read", "write"], {"command": "orgmcp", "args": ["mcp"]}),
        {"allowed_tools": ["@orgmcp"], "tools_settings": {"write": {"allowedPaths": ["/ws"]}, "read": {"allowedPaths": ["/ws", "/org"]}}},
    ),
    "kiro_profile_empty_settings": (
        ("orgmcp-ceo", "agent ceo", ["@orgmcp"], {"command": "orgmcp"}), {"allowed_tools": [], "tools_settings": {}},
    ),
}
