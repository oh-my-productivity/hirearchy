"""The public surface of the kernel: the smallest shared vocabulary every feature may use.

Addresses, messages, errors, time, text and the primitive ports. The kernel imports nothing else from ``orgmcp``.
"""

from __future__ import annotations

from ._address import BOXES, NAME_RE, RESERVED, ROOT, RUNTIME, RUNTIME_NAMES, child_addr, depth, norm, parent
from ._errors import OrgError
from ._frontmatter import flow_text, join_frontmatter, split_frontmatter
from ._message import (
    MESSAGE_TYPES,
    RENDER_BODY_CHARS,
    RESULT_STATUSES,
    Message,
    MessageView,
    latest_results,
)
from ._paths import OrgLayout, OrgPaths, inside, visible
from ._ports import AtomicWriter, Clock, Environment, EventSink, IdGenerator, JsonObject, LedgerStore, Provider, TraceTap
from ._text import TITLE_MAX, clip, clip_line, single, word_count
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
    "STAMP_FORMAT",
    "TITLE_MAX",
    "TraceTap",
    "aware",
    "child_addr",
    "clip",
    "clip_line",
    "depth",
    "flow_text",
    "fmt_dur",
    "fmt_duration",
    "inside",
    "join_frontmatter",
    "latest_results",
    "msg_time",
    "norm",
    "parent",
    "parse_time",
    "single",
    "split_frontmatter",
    "stamp_of",
    "visible",
    "word_count",
]
