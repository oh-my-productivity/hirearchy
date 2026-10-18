"""Filesystem model of an agent organization.

Invariants (everything else is built on these):

* An agent is a directory containing AGENT.md. Its address is its path relative to the org
  root (e.g. ``ceo/cto``). The org root itself is ``root``: the human.
* Messages are immutable markdown files with YAML frontmatter. They are created atomically
  (temp file + rename) in the recipient's ``inbox/`` with a copy in the sender's ``sent/``.
* Received messages move ``inbox/ -> inflight/`` (current run) ``-> read/`` (processed).
* Single writer: an agent writes only inside its own directory. The one exception is a
  direct report's AGENT.md, which the parent owns.
* State is derived, never stored:
  - a task is open until its assignee has sent a result with ``reply_to`` = task id;
  - a task's outcome is its *latest* result: ``blocked`` may be superseded by a later result (``supersedes`` = the
    id of the one it replaces), ``done`` and ``failed`` are final;
  - budget = budget received - budget handed down - runs consumed (files in ``runs/``). Budget flows down with tasks
    and grants; it comes back up only as the ``budget`` of a final result (``done``/``failed`` of an agent with nothing
    else open) or of a note to the parent. Every transfer is one message, charged to the sender and credited to the
    recipient, so the total never changes.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from . import telemetry, templates  # noqa: F401 - core has always exposed these modules

# The facade is assembled in orgmcp.app (ARCHITECTURE.md 6.4); the module-level helpers that used to live here come from the mixin
# of their slice. Every name stays importable from orgmcp.core (permanent compatibility surface).
from .app.facade import (  # noqa: F401 - re-exports
    _EXACT_FILES,
    _FOLDED_RUNTIME_NAMES,
    DEFAULT_CONFIG,
    DEFAULT_MODEL,
    LESSONS_MAX_CHARS,
    Org,
    Retired,
    _case_twin,
    _fold,
    _message_cap,
    _short,
    charter_change_note,
    config_default_model,
)
from .app.wiring import process_resources

# The shared vocabulary lives in orgmcp.kernel; these names stay importable from here (`core.Message is kernel.Message`).
from .kernel import (  # noqa: F401 - re-exports
    BOXES,
    MESSAGE_TYPES,
    NAME_RE,
    RENDER_BODY_CHARS,
    RESERVED,
    RESULT_STATUSES,
    ROOT,
    RUNTIME,
    RUNTIME_NAMES,
    Message,
    OrgError,
    child_addr as _child_addr,
    depth as _depth,
    inside as _inside,
    join_frontmatter,
    latest_results,
    norm as _norm,
    parent as _parent,
    split_frontmatter,
    visible as _visible,
    word_count,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".tmp-{secrets.token_hex(4)}-{path.name}"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# The parse cache is a process resource (orgmcp.app, ARCHITECTURE.md 2.4): `_PARSED` is the very dict of the process parser (a
# `mail.CachingMessageParser`). The legacy classmethod `Message.load` is attached to the kernel's `Message` by orgmcp.app, not by this
# module. `_PARSED_MAX` is the limit the process parser is built with: kept as a name of the compatibility surface, but nothing reads it
# at call time any more (tests that need another limit or a counting splitter inject a parser through `open_runtime`, since A-mail).
_PARSED = process_resources().message_parser.cache
_PARSED_MAX = 50_000
