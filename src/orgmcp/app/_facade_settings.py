"""ORG.md: the org root lookup, the settings block and the rules text (settings, locator).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

import os
from pathlib import Path

from ..kernel import OrgError, split_frontmatter


DEFAULT_MODEL = "claude-sonnet-5.5"  # the model every agent runs on unless its charter or the org config names another


DEFAULT_CONFIG = {
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
    "max_message_chars": 20000,  # longest message body send/delegate/report accept; detail goes in a file
    "events": True,  # write the structured event log (.runtime/events/); false = no emission at all
    "events_keep_days": 30,  # the scheduler deletes event-log days older than this (at most once a day)
    "heartbeat_seconds": 60,  # the scheduler writes a heartbeat event this often
}


def _message_cap(config: dict) -> int:
    """``max_message_chars`` from ORG.md; a malformed value means the default."""
    try:
        cap = int(config["max_message_chars"])
    except (TypeError, ValueError):
        return int(DEFAULT_CONFIG["max_message_chars"])
    return cap if cap > 0 else int(DEFAULT_CONFIG["max_message_chars"])


def config_default_model(config: dict | None) -> str:
    """The default model of a config mapping (``null``, empty or missing = DEFAULT_MODEL)."""
    return str((config or {}).get("default_model") or "").strip() or DEFAULT_MODEL


class SettingsMixin:
    """ORG.md: the org root lookup, the settings block and the rules text (settings, locator)."""

    @staticmethod
    def find_root(start: str | Path | None = None) -> Path:
        env = os.environ.get("ORG_ROOT")
        if env:
            return Path(env).expanduser().resolve()
        here = Path(start or Path.cwd()).resolve()
        for d in (here, *here.parents):
            if (d / "ORG.md").is_file():
                return d
        if (here / "org" / "ORG.md").is_file():  # e.g. running from the orgmcp project dir
            return here / "org"
        raise OrgError("no organization found: set ORG_ROOT or run inside an org directory")

    @property
    def config(self) -> dict:
        meta, _ = split_frontmatter((self.root / "ORG.md").read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **meta}

    def rules(self) -> str:
        return split_frontmatter((self.root / "ORG.md").read_text(encoding="utf-8"))[1].strip()
