"""orgmcp.services: standing services, with their contract, playbook, requests and feedback (see :mod:`orgmcp.services.api`).

The module ``services.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old function and
constant names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3
removes them.

The cases, statistics, digest, listing and prompt sections that were derived from the message files moved to ``reflection`` (step C-reflection),
which sits above this package and may import it, not the other way round. Callers and tests that still say ``services.cases(...)`` get the
object of ``reflection`` when they ask for it (``__getattr__``, by name, at the first use): there is no import of ``reflection`` here, and the
bridge goes with the legacy names in E3.
"""

import importlib as _importlib

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    TITLE_MAX,
    define_service,
    feedback,
    feedback_text,
    owned_services,
    parse_input_spec,
    read_contract,
    read_playbook,
    report_hint,
    request,
    requestable_services,
    retire_service,
    revise_playbook,
    rework_fields,
    service_dir,
)
from ._legacy import _clip as _clip  # (private names the legacy callers and tests still use)
from ._legacy import _deliverable as _deliverable
from ._legacy import _inputs as _inputs

__all__ = [
    *api.__all__,
    "TITLE_MAX",
    "define_service",
    "feedback",
    "feedback_text",
    "owned_services",
    "parse_input_spec",
    "read_contract",
    "read_playbook",
    "report_hint",
    "request",
    "requestable_services",
    "retire_service",
    "revise_playbook",
    "rework_fields",
    "service_dir",
]

_MOVED_TO_REFLECTION = frozenset(
    {
        "CLIP_LESSON", "CLIP_NOTE", "DIGEST_CASES", "DIGEST_CHARS", "MAX_VERDICTS", "Case", "Stats", "Verdict", "case_of", "case_total", "cases",
        "lessons_of", "playbook_timeline", "prompt_sections", "reflection_digest", "services_text", "stats_by_version", "summarize", "version_at",
        "_case_line", "_verdict_chain",
    }
)


def __getattr__(name: str) -> object:
    """The names that moved to ``reflection``, looked up there when asked for (until E3)."""
    if name in _MOVED_TO_REFLECTION:
        return getattr(_importlib.import_module("orgmcp.reflection"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
