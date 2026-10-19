"""orgmcp.reflection: the history of the requests for a service, with statistics, derived from the files (see :mod:`orgmcp.reflection.api`).

``api`` is the public surface. The module-level functions that took the ``Org`` first in ``services`` (``cases``, ``reflection_digest``, ``case_of``,
``case_total``, ``services_text``, ``prompt_sections``, ``playbook_timeline``) and the constants of the digest are still exported (``LEGACY_EXPORTS`` in
``tests/architecture/legacy_exports.py``) by the private ``_legacy`` module until step E3 removes them; ``services`` answers to the old names too.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import (
    CLIP_LESSON,
    CLIP_NOTE,
    DIGEST_CASES,
    DIGEST_CHARS,
    MAX_VERDICTS,
    case_of,
    case_total,
    cases,
    playbook_timeline,
    prompt_sections,
    reflection_digest,
    services_text,
)
from ._legacy import _case_line as _case_line  # (private names the dashboard and the tests still use)
from ._legacy import _verdict_chain as _verdict_chain

__all__ = [
    *api.__all__,
    "CLIP_LESSON",
    "CLIP_NOTE",
    "DIGEST_CASES",
    "DIGEST_CHARS",
    "MAX_VERDICTS",
    "case_of",
    "case_total",
    "cases",
    "playbook_timeline",
    "prompt_sections",
    "reflection_digest",
    "services_text",
]
