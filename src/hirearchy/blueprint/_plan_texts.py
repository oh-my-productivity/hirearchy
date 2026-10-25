"""The words and limits of the plan (package-private)."""

from __future__ import annotations

PLAN_HEADING = "PLAN FOR YOU"  # the first line of the block the user sees: no instruction inside the block
PLAN_DRAFT_HEADING = "DRAFT - NOT READY (it has errors: fix the blueprint and propose again; do not show this to the user)"
PLAN_END = "--- machine marker: the user block ends above; do not show this line or anything below it ---"
PLAN_SHOW = ("Show the block below to the user exactly as written, from its first line up to (not including) the marker line; "
             "one plain-words intro line before it is fine.")
TOOL_WORDS = {"read": "read files", "write": "write files", "shell": "run commands", "web_search": "search the web",
              "web_fetch": "read web pages"}
SHOWN_CRITERIA = 8  # the block stays compact (about 40 lines); the full lists are in the details
SHOWN_WARNINGS = 5
HIDDEN_WARNINGS = {"path-delivery", "path-parent", "needs-scope", "needs-approval", "needs-progress"}  # said elsewhere in the block
PLAN_ID_LENGTH = 12
SHOWN_SERVICE_CRITERIA = 5  # per service in the block; the details have them all
BUDGET_QUESTION = "Use {n} runs per request (covers one round of your questions or a rejection), or keep {m}?"  # D-E7-3: the block's last line
BUDGET_QUESTION_FOR = "Use {n} runs per request for {name} (covers one round of your questions or a rejection), or keep {m}?"  # one per service when several
