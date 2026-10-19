"""The numbers and words the dashboard's data is made with."""

from __future__ import annotations

from datetime import timedelta

ERROR_WINDOW = timedelta(minutes=15)
ERROR_WINDOW_TEXT = "15m"
LOG_LINES = 2000  # lines of a run log that are shown (the tail)
LOG_BYTES = 1_000_000  # never read more than this from the end of a run log
FEED_KEEP = 5000  # events kept in memory
FEED_BACKFILL = "2h"  # how far back the first load of the event feed reaches
TEXT_CAP = 60_000  # characters of a memory file / message shown
SERVICES_TTL = 5.0
HEALTH_TTL = 8.0
REQUESTS_TTL = 5.0

STATE_KINDS = ("running", "queued", "working", "waiting", "idle", "paused", "budget", "you")
GLYPHS = {"running": "▶", "queued": "◔", "working": "◆", "waiting": "◇", "idle": "○", "paused": "‖",
          "budget": "!", "you": "★"}
