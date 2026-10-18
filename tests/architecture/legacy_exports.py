"""The legacy-exports ledger (ARCHITECTURE.md 6.5).

During the strangler phase each legacy module is converted in place to a package that exports its ``api`` plus the old names
(``LEGACY_EXPORTS``); until a module is converted, its old public names are simply the names it defines. This ledger lists, per
legacy module, every public name that may still be exported and the step that removes it. It only shrinks:

* a public name that the module defines or exports and that is NOT listed fails ``check`` (nobody adds a legacy export);
* a listed name that the module no longer defines fails ``check`` too (delete the entry in the step that removed it: the ledger
  and the code move together). A step that converts a module deletes the entries it removes, in its own table (disjoint hunks).

Removal step ``"E3"`` = the final step that deletes the legacy layer; ``"permanent"`` = the compatibility surface that stays
(manager decision 10.3): ``orgmcp.core`` (all of its names: README documents ``DEFAULT_MODEL`` and ``Org``), ``orgmcp.progress.progress``,
the console script / ``python -m orgmcp`` (``orgmcp.main``, which is imported, not defined, in ``orgmcp/__init__.py``).
"""

from __future__ import annotations

import ast
from pathlib import Path

from . import legacy_symbols
from .paths import SRC


def _e3(names: str) -> dict[str, str]:
    return {name: "E3" for name in names.split()}


PERMANENT_MODULES = {"core"}  # every name of these modules stays: the ledger holds the wildcard "*"

LEGACY_EXPORTS: dict[str, dict[str, str]] = {
    "core": {"*": "permanent"},
    "scheduler": _e3(
        "Runner PROJECT_DIR KIRO_AGENTS_DIR mcp_server_command kiro_profile_name FILE_TOOLS file_confinement "
        "ensure_kiro_profile kiro_runner Run judge_orphan kill_group ignore_runtime_files EXIT_FILE FINISHED "
        "SchedulerState scheduler_command scheduler_state describe_scheduler Waiting waiting_on_user start_scheduler "
        "stop_scheduler run_id_of Scheduler nothing_to_do"
    ),
    "server": _e3(
        "INSTRUCTIONS ROOT_INSTRUCTIONS DS_STORE OrgBinding instrument_tools root_instructions build_server "
        "register_service_tools register_client_tools register_owner_tools setup_state register_root_tools "
        "resolve_binding serve"
    ),
    "cli": _e3(
        "cmd_init cmd_hire cmd_task cmd_services cmd_define_service cmd_request cmd_feedback cmd_retire_service "
        "cmd_plan cmd_apply cmd_send cmd_status cmd_health cmd_progress cmd_upgrade_rules cmd_install_skill "
        "cmd_review cmd_inbox cmd_resume cmd_run cmd_dash cmd_mcp cmd_kiro_profile main"
    ),
    "cli_obs": _e3(
        "cmd_now cmd_trace cmd_metrics cmd_events cmd_check register_obs"
    ),
    "services": _e3(
        "INPUT_RE VERDICTS DESCRIPTION_MAX REASON_MAX FEEDBACK_MAX TITLE_MAX DELIVERABLE_KEYS DIGEST_CASES "
        "DIGEST_CHARS FEEDBACK_HEADER CLIP_LESSON CLIP_NOTE MAX_VERDICTS Contract Playbook service_dir read_contract "
        "read_playbook owned_services requestable_services parse_input_spec define_service retire_service "
        "revise_playbook report_hint request rework_fields feedback_text feedback Case Verdict Stats "
        "playbook_timeline version_at lessons_of cases summarize stats_by_version reflection_digest case_of "
        "case_total services_text prompt_sections"
    ),
    "telemetry": _e3(
        "SCHEMA_VERSION LINE_MAX EVENTS_REL RETRY_AFTER TITLE_MAX ERROR_MAX DAY_RE ENVELOPE PROCS clip set_process "
        "process dropped reset traces_seen note_trace single ensure_ignored emit summarize_args prune"
    ),
    "observe": _e3(
        "EVENTS_DIR ERROR_WINDOW COPY_GRACE INFLIGHT_GRACE RECV_BOXES ENVELOPE READ_ONLY_TOOLS VIEWS fmt_dur fmt_rel "
        "percentile parse_when event_files timed_events iter_events is_error events_view events Follower "
        "follow_events format_event render_events FileRec scan_messages Msg build_messages Traces RunRec run_events "
        "collect_runs run_window trace render_trace normalize_refusal metrics render_metrics now_view render_now "
        "check render_check observe_text register_observe_tool"
    ),
    "progress": {
        **_e3(
        "RECENT SHORT WAIT_MAX POLL FINAL progress describe_progress work_in_flight"
        ),
        "progress": "permanent",  # orgmcp.progress.progress(org, task_id=None) is documented in the README
    },
    "health": _e3(
        "HEALTH_DEFAULTS FLAGS AgentHealth BranchHealth OrgHealth thresholds agent_health org_health "
        "render_text"
    ),
    "review": _e3(
        "LEDGER Note Review read_ledger total_runs review_if_due review"
    ),
    "blueprint": _e3(
        "ROLES_DIR WEB_TOOLS WRITE_TOOLS SLACK TIGHT REWORK_RUNS KINDS BlueprintError Issue errors Role role_names "
        "get_role load load_text Agent NEEDS_KEYS AGENT_KEYS SERVICE_KEYS TASK_KEYS REQUEST_KEYS service_budget "
        "declared_inputs review_roots estimate planned_total budget_split edits_others_files validate "
        "default_playbook org_files_readable access_facts render_plan PLAN_HEADING PLAN_DRAFT_HEADING PLAN_END "
        "PLAN_SHOW TOOL_WORDS SHOWN_CRITERIA SHOWN_WARNINGS HIDDEN_WARNINGS PLAN_ID_LENGTH SHOWN_SERVICE_CRITERIA "
        "plan_id CLIP GOAL_CLIP plan_for_user propose_text propose Summary apply"
    ),
    "blueprint_examples": _e3(
        "KINDS SCHEMA RESEARCH DOCUMENTS CODE ANALYSIS TEMPLATES SERVICE_SCHEMA SERVICE_HEAD SERVICE_TAIL "
        "SERVICE_BODIES SERVICE_BUDGETS example"
    ),
    "templates": _e3(
        "ORG_RULES DEFAULT_MISSION org_rules charter_body task_body result_body notice_budget notice_budget_returned "
        "notice_failures notice_nudge notice_stalled REVIEW_ACTIONS review_item notice_review_manager "
        "notice_review_root kiro_profile"
    ),
    "upgrade": _e3(
        "MISSION_HEADING RULES_HEADING Upgrade extract_mission upgrade_rules"
    ),
    "skill": _e3(
        "SKILL_NAME skill_source install_skill"
    ),
    "dashboard_events": _e3(
        "WHO_WIDTH BATCH_SHOWN Lookup EventLine clock who describe humanize event_lines"
    ),
    "dashboard_data": _e3(
        "ERROR_WINDOW ERROR_WINDOW_TEXT LOG_LINES LOG_BYTES FEED_KEEP FEED_BACKFILL TEXT_CAP CACHE_TRUST SERVICES_TTL "
        "HEALTH_TTL REQUESTS_TTL STATE_KINDS GLYPHS clean_text LenientOrg AgentState pause_text classify Section "
        "doc_text AgentRow SchedulerView Snapshot MsgRow RunLog AgentDetail RequestRow ServiceRow HealthView "
        "EventFeed DashData render_once"
    ),
    "dashboard": _e3(
        "VIEWS VIEW_NAMES TABS TAB_NAMES KIND_STYLE HELP doc_renderable event_text TextPane NavTable AgentTree "
        "ContextFooter StatusBar TextScreen Ctx Tick SCREENS TAB_KEYS DashApp run_dashboard"
    ),
}


def public_names(path: Path) -> list[str]:
    """Public names a legacy module defines at module level (functions, classes, constants), in file order."""
    names: list[str] = []
    for stmt in legacy_symbols._toplevel(ast.parse(path.read_text(encoding="utf-8")).body):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(stmt.name)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            names.extend(sub.id for target in targets for sub in ast.walk(target) if isinstance(sub, ast.Name))
    return [n for n in dict.fromkeys(names) if not n.startswith("_")]


def _bound_names(path: Path) -> set[str]:
    """Names bound at module level of an ``__init__.py`` (imports, definitions, assignments)."""
    bound: set[str] = set()
    for stmt in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(stmt, ast.ImportFrom):
            bound.update((a.asname or a.name) for a in stmt.names)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(stmt.name)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            bound.update(sub.id for target in targets for sub in ast.walk(target) if isinstance(sub, ast.Name))
    return bound


def check(src: Path = SRC) -> list[str]:
    """Problems between the ledger and the code under ``src`` (empty when they agree)."""
    problems = []
    for module, entries in LEGACY_EXPORTS.items():
        flat, package = src / f"{module}.py", src / module / "__init__.py"
        if "*" in entries:
            continue
        if flat.is_file():
            defined = public_names(flat)
            problems += [f"{module}.{n} is public but not in the legacy-exports ledger (tests/architecture/legacy_exports.py): "
                         "a legacy module may not gain exports" for n in defined if n not in entries]
            problems += [f"{module}.{n} is in the ledger but the module no longer defines it: delete the entry"
                         for n in entries if n not in defined]
        elif package.is_file():
            bound = _bound_names(package)
            problems += [f"{module}.{n} is in the ledger but the package no longer exports it: delete the entry"
                         for n in entries if n not in bound]
        else:
            problems.append(f"{module}: the legacy module no longer exists: delete its table in the ledger")
    return problems


def exported_names_by_package(src: Path | None = None) -> dict[str, set[str]]:
    """{package: legacy names it may still export besides its api}: the ledger tables of the modules that became packages."""
    root = src or SRC
    return {module: set(entries) for module, entries in LEGACY_EXPORTS.items()
            if "*" not in entries and (root / module / "__init__.py").is_file()}
