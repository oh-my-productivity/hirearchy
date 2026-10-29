"""``retro``: the retro brief for the user (design 4.7, 11.4): root only; derived from the files, costs no run, and records itself only when a verdict of the user arrived since the last brief."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio

from ..kernel import ROOT, OrgError, Provider
from ..retro import RetroBriefs, parse_since, render_brief
from ._ports import SetupMode, ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

NOT_ROOTS = "refused: retro is root's: it briefs the user. Nothing was read."


class RetroTools(ToolGroup):
    def __init__(self, setup: SetupMode, briefs: Provider[RetroBriefs]) -> None:
        self._setup = setup
        self._briefs = briefs

    def register(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        async def retro(since: str | None = None) -> str:
            """The retro brief: what the client said, what got past a check, whether past changes held, how the organization changed, the team's own proposals,
        and at most 3 yes/no items, each with its call. Call it when the user asks. Show the block from RETRO BRIEF to RETRO BRIEF END to the user exactly as
        written; for each item they answer yes, make the call its Details give, one at a time; never add an item of your own. Without since it is recorded
        when a verdict of the user arrived since the last brief (the last brief's items that were not taken then lapse with no change), and otherwise the
        last brief is shown again and nothing is recorded. since (a date, a datetime or a message id): a look-back over that window, recorded nowhere.
        Costs no run.
        """
            if self._setup.active():
                return self._setup.state()
            if me != ROOT:
                raise OrgError(NOT_ROOTS)
            when = parse_since(since) if since is not None and since.strip() else None
            briefs = self._briefs()
            return render_brief(await anyio.to_thread.run_sync(lambda: briefs.brief(since=when)))
