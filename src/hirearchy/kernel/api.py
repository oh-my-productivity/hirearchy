"""The public surface of the kernel: the smallest shared vocabulary every feature may use.

Addresses, messages, errors, time, text and the primitive ports. The kernel imports nothing else from ``hirearchy``.
"""

from __future__ import annotations

from ._address import BOXES, NAME_RE, RESERVED, ROOT, RUNTIME, RUNTIME_NAMES, child_addr, depth, norm, parent
from ._errors import OrgError
from ._frontmatter import flow_text, join_frontmatter, split_frontmatter
from ._message import (
    MESSAGE_TYPES,
    RENDER_BODY_CHARS,
    RESULT_STATUSES,
    RUN_CREDIT_TITLE,
    SOURCES,
    Message,
    MessageView,
    credited_stems,
    is_run_credit,
    latest_results,
    link_ids,
    run_credit_title,
    verdict_tier,
)
from ._paths import OrgLayout, OrgPaths, inside, visible
from ._ports import AtomicWriter, Clock, Environment, EventSink, IdGenerator, JsonObject, LedgerStore, Provider, TokenSource, TraceTap
from ._text import TITLE_MAX, artifact_paths, client_questions, clip, clip_line, single, strip_markers, word_count
from ._timeutil import STAMP_FORMAT, aware, fmt_dur, fmt_duration, msg_time, parse_time, stamp_of

__all__ = [
    "AtomicWriter",
    "BOXES",
    "Clock",
    "Environment",
    "EventSink",
    "IdGenerator",
    "JsonObject",
    "LedgerStore",
    "MESSAGE_TYPES",
    "Message",
    "MessageView",
    "NAME_RE",
    "OrgError",
    "OrgLayout",
    "OrgPaths",
    "Provider",
    "RENDER_BODY_CHARS",
    "RESERVED",
    "RESULT_STATUSES",
    "ROOT",
    "RUNTIME",
    "RUNTIME_NAMES",
    "RUN_CREDIT_TITLE",
    "SOURCES",
    "STAMP_FORMAT",
    "TITLE_MAX",
    "TokenSource",
    "TraceTap",
    "artifact_paths",
    "aware",
    "child_addr",
    "client_questions",
    "clip",
    "clip_line",
    "credited_stems",
    "depth",
    "flow_text",
    "fmt_dur",
    "fmt_duration",
    "inside",
    "is_run_credit",
    "join_frontmatter",
    "latest_results",
    "link_ids",
    "msg_time",
    "norm",
    "parent",
    "parse_time",
    "run_credit_title",
    "single",
    "split_frontmatter",
    "stamp_of",
    "strip_markers",
    "verdict_tier",
    "visible",
    "word_count",
]
