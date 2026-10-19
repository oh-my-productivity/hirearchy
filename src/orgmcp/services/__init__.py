"""orgmcp.services: standing services, with their contract, playbook, requests and feedback (see :mod:`orgmcp.services.api`).

The module ``services.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function and
constant names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3
removes them. ``_legacy`` also holds, as a seam, the part that step C-reflection moves into ``reflection``: the cases, statistics, digest, listing
and prompt sections that are derived from the message files.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    CLIP_LESSON,
    CLIP_NOTE,
    DIGEST_CASES,
    DIGEST_CHARS,
    MAX_VERDICTS,
    TITLE_MAX,
    Case,
    Stats,
    Verdict,
    case_of,
    case_total,
    cases,
    define_service,
    feedback,
    feedback_text,
    lessons_of,
    owned_services,
    parse_input_spec,
    playbook_timeline,
    prompt_sections,
    read_contract,
    read_playbook,
    reflection_digest,
    report_hint,
    request,
    requestable_services,
    retire_service,
    revise_playbook,
    rework_fields,
    service_dir,
    services_text,
    stats_by_version,
    summarize,
    version_at,
)
from ._legacy import _case_line as _case_line
from ._legacy import _clip as _clip  # (private names the legacy callers and tests still use)
from ._legacy import _deliverable as _deliverable
from ._legacy import _inputs as _inputs
from ._legacy import _verdict_chain as _verdict_chain

__all__ = [
    *api.__all__,
    "CLIP_LESSON",
    "CLIP_NOTE",
    "DIGEST_CASES",
    "DIGEST_CHARS",
    "MAX_VERDICTS",
    "TITLE_MAX",
    "Case",
    "Stats",
    "Verdict",
    "case_of",
    "case_total",
    "cases",
    "define_service",
    "feedback",
    "feedback_text",
    "lessons_of",
    "owned_services",
    "parse_input_spec",
    "playbook_timeline",
    "prompt_sections",
    "read_contract",
    "read_playbook",
    "reflection_digest",
    "report_hint",
    "request",
    "requestable_services",
    "retire_service",
    "revise_playbook",
    "rework_fields",
    "service_dir",
    "services_text",
    "stats_by_version",
    "summarize",
    "version_at",
]
