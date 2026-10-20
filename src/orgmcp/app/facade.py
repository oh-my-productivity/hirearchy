"""The ``Org`` facade (ARCHITECTURE.md 6.4): the class everything outside the refactor still calls.

``Org`` is the composition of 20 mixins, one per package that ``core.Org`` is being split into. Each mixin holds exactly the methods
that ARCHITECTURE.md 5.3 maps to its package (code moved verbatim from the former 98-def class in step M2), so that every feature
step edits one small file of its own (``_facade_<pkg>.py``) and turns its bodies into calls to the interfaces of ``self.runtime``.

Method resolution order (the mixins define disjoint names and every method is a pure delegation, checked by
``tests/architecture/test_facade_contract.py``; no subclass of ``Org`` overrides a method, so the order is documentation)::

    Org
     CoreMixin          __init__ norm parent depth child_addr dir new_id ledger save_ledger
     SettingsMixin      find_root config rules
     SnapshotsMixin     commit
     BootstrapMixin     init
     AgentsMixin        exists require children agents subtree charter memory
     RunsMixin          runs_used start_run_log
     MailMixin          messages received sent find_received unread open_tasks outstanding begin_run end_run recover ...
     TelemetryMixin     emit
     AccessMixin        default_model model_for workspace_of inputs_of readable_roots unconfined_read tool_names ...
     TracesMixin        trace_of open_task_traces context_trace stamp_trace
     DeliveryMixin      deliver notify
     FilesMixin         resolve_read read resolve_write write write_noted
     StraysMixin        stray_notice
     BudgetMixin        budget delegable grant_hint reclaim ...
     EligibilityMixin   paused pause resume record_failure clear_failures state
     HierarchyMixin     hire retire retire_team
     DispatchMixin      can_message send delegate report ...
     ServicesMixin      service_names define_service retire_service request revise_playbook feedback
     OverviewMixin      tree
     PromptsMixin       state_summary whoami run_prompt ...
     object

``orgmcp.core`` re-exports ``Org`` and the module-level helpers listed below from here.
"""

from __future__ import annotations

from ._facade_access import AccessMixin
from ._facade_agents import AgentsMixin
from ._facade_bootstrap import BootstrapMixin
from ._facade_budget import BudgetMixin
from ._facade_core import CoreMixin
from ._facade_delivery import DeliveryMixin
from ._facade_dispatch import LESSONS_MAX_CHARS, DispatchMixin
from ._facade_eligibility import EligibilityMixin
from ._facade_files import (
    _EXACT_FILES,
    _FOLDED_RUNTIME_NAMES,
    FilesMixin,
    _case_twin,
    _fold,
    _short,
    charter_change_note,
)
from ._facade_hierarchy import HierarchyMixin, Retired
from ._facade_mail import MailMixin
from ._facade_overview import OverviewMixin
from ._facade_prompts import PromptsMixin
from ._facade_runs import RunsMixin
from ._facade_services import ServicesMixin
from ._facade_settings import DEFAULT_CONFIG, DEFAULT_MODEL, SettingsMixin, _message_cap, config_default_model
from ._facade_snapshots import SnapshotsMixin
from ._facade_strays import StraysMixin
from ._facade_telemetry import TelemetryMixin
from ._facade_traces import TracesMixin

__all__ = [
    "DEFAULT_CONFIG",
    "DEFAULT_MODEL",
    "LESSONS_MAX_CHARS",
    "Org",
    "Retired",
    "_EXACT_FILES",
    "_FOLDED_RUNTIME_NAMES",
    "_case_twin",
    "_fold",
    "_message_cap",
    "_short",
    "charter_change_note",
    "config_default_model",
]


class Org(
    CoreMixin,
    SettingsMixin,
    SnapshotsMixin,
    BootstrapMixin,
    AgentsMixin,
    RunsMixin,
    MailMixin,
    TelemetryMixin,
    AccessMixin,
    TracesMixin,
    DeliveryMixin,
    FilesMixin,
    StraysMixin,
    BudgetMixin,
    EligibilityMixin,
    HierarchyMixin,
    DispatchMixin,
    ServicesMixin,
    OverviewMixin,
    PromptsMixin,
):
    """The organization at ``root``: see the module docstring for the mixins and their order (the MRO)."""
