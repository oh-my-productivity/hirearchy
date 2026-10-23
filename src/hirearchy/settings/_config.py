"""The settings block of ORG.md: its defaults and the pure rules for reading one value out of it."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import cast

from ..kernel import JsonObject, split_frontmatter

DEFAULT_MODEL = "claude-sonnet-5.5"  # the model every agent runs on unless its charter or the org config names another
DEFAULT_EFFORT = "high"  # the kiro effort of every org-agent run unless the org config names a higher one


DEFAULT_CONFIG: JsonObject = {
    "max_depth": 4,  # deepest allowed agent (ceo = 1)
    "max_hops": 40,  # longest message chain before sends are refused (loop guard)
    "max_parallel": 3,  # concurrent agent runs
    "max_failures": 3,  # consecutive failed runs before an agent is paused
    "run_timeout": 1800,  # seconds per run
    "stall_after": 600,  # seconds of silence on an open task before the next step of the stall ladder
    "review_every_runs": 25,  # org-wide runs between health reviews (or review_every_seconds, whichever first)
    "review_every_seconds": 86400,
    "poll_seconds": 2,
    "until_done_grace_seconds": 300,  # an until-done scheduler that finds nothing can progress without the user exits after this
    "default_budget": 10,  # runs given with a task when none is specified
    "memory_max_words": 800,  # cap on an agent's MEMORY.md; writes that exceed it are refused
    "playbook_max_words": 1000,  # cap on a service playbook (revise_playbook refuses longer ones)
    "default_model": DEFAULT_MODEL,  # kiro model for agents whose charter names none; null/missing = DEFAULT_MODEL
    "effort": DEFAULT_EFFORT,  # kiro effort of every org-agent run: high, xhigh or max; null/missing = high
    "max_message_chars": 20000,  # longest message body send/delegate/report accept; detail goes in a file
    "events": True,  # write the structured event log (.runtime/events/); false = no emission at all
    "events_keep_days": 30,  # the scheduler deletes event-log days older than this (at most once a day)
    "heartbeat_seconds": 60,  # the scheduler writes a heartbeat event this often
}


def finite_number(value: object) -> float | None:
    """``value`` as a finite int/float, or None. Numeric strings are accepted ("1800"); booleans are not."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
        value = int(number) if number.is_integer() else number
    if isinstance(value, (int, float)) and math.isfinite(value):
        return value
    return None


def config_default_model(config: Mapping[str, object] | None) -> str:
    """The default model of a config mapping (``null``, empty or missing = DEFAULT_MODEL)."""
    return str((config or {}).get("default_model") or "").strip() or DEFAULT_MODEL


def config_number(config: Mapping[str, object], key: str, kind: type[float] | type[int] = float) -> float:
    """A numeric setting of ORG.md as ``kind``; a missing or malformed value falls back to the default."""
    number = finite_number(config.get(key))
    return kind(number if number is not None else cast(float, DEFAULT_CONFIG[key]))


def config_message_cap(config: Mapping[str, object]) -> int:
    """``max_message_chars`` from ORG.md; a malformed value means the default."""
    try:
        cap = int(cast("int | str", config["max_message_chars"]))
    except (TypeError, ValueError):
        return int(cast(int, DEFAULT_CONFIG["max_message_chars"]))
    return cap if cap > 0 else int(cast(int, DEFAULT_CONFIG["max_message_chars"]))


def parse_config(text: str) -> JsonObject:
    """The settings of an ORG.md text: its frontmatter merged over the defaults (a new mapping every time)."""
    meta, _ = split_frontmatter(text)
    return {**DEFAULT_CONFIG, **meta}


def parse_rules(text: str) -> str:
    """The rules of an ORG.md text: its body, stripped."""
    return split_frontmatter(text)[1].strip()
