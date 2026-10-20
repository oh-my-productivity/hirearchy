"""Which method of the old ``core.Org`` lives in which mixin: sections 5.3 and 6.4 of ARCHITECTURE.md as data."""

from __future__ import annotations

# (module suffix, class, methods) in the order of the bases of Org (6.4); the methods are those of section 5.3 / 6.4
MIXINS: list[tuple[str, str, str]] = [
    ("core", "CoreMixin", "__init__ norm parent depth child_addr dir new_id ledger save_ledger"),
    ("settings", "SettingsMixin", "find_root config rules"),
    ("snapshots", "SnapshotsMixin", "commit"),
    ("bootstrap", "BootstrapMixin", "init"),
    ("agents", "AgentsMixin", "exists require children agents subtree charter memory"),
    ("runs", "RunsMixin", "runs_used start_run_log"),
    ("mail", "MailMixin", "messages received sent find_received unread _wakes open_tasks outstanding _blocked_tasks begin_run end_run "
                          "recover redeliver_orphans running"),
    ("telemetry", "TelemetryMixin", "emit"),
    ("access", "AccessMixin", "default_model model_for _check_authority _check_inputs workspace_of inputs_of readable_roots "
                              "unconfined_read tool_names"),
    ("traces", "TracesMixin", "trace_of open_task_traces context_trace stamp_trace"),
    ("delivery", "DeliveryMixin", "deliver notify"),
    ("files", "FilesMixin", "resolve_read read resolve_write write write_noted"),
    ("strays", "StraysMixin", "stray_notice"),
    ("budget", "BudgetMixin", "budget delegable grant_hint _check_allocation _default_budget _budget_to_return reclaim"),
    ("eligibility", "EligibilityMixin", "paused pause resume record_failure clear_failures state"),
    ("hierarchy", "HierarchyMixin", "hire retire retire_team"),
    ("dispatch", "DispatchMixin", "can_message _next_hops send delegate report _normalize_artifact _check_lessons"),
    ("services", "ServicesMixin", "service_names define_service retire_service request revise_playbook feedback"),
    ("overview", "OverviewMixin", "tree"),
    ("prompts", "PromptsMixin", "_agent_line state_summary _indent _quote _render_in_context _upstream _files_lines whoami run_prompt"),
]
