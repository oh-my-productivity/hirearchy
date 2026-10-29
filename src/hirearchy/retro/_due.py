"""``FileRetroDue``: the trigger line of a due retro (design 4.6, D17, Q17).

When the verdicts of the user since the last brief reach ``after_verdicts``, a line for a reply or a listing tells root to OFFER the retro and to call ``retro()`` only after the
user's yes. The line is text: it sends no message, wakes nobody and is never in an agent's prompt. An unreadable source gives no line, so the trigger never breaks the reply it is
appended to."""

from __future__ import annotations

from ..kernel import OrgError
from ..settings import OrgSettings
from ._ports import BriefSources
from ._texts import DUE_LISTING, DUE_REPLY, NONE_YET, day
from .api import RetroDue, RetroRecords, retro_thresholds


class FileRetroDue(RetroDue):
    def __init__(self, sources: BriefSources, records: RetroRecords, settings: OrgSettings) -> None:
        self._sources = sources
        self._records = records
        self._settings = settings

    def due(self, *, listing: bool = False) -> str:
        try:
            last = self._records.last()
            after = last.at if last is not None else None
            th, _ = retro_thresholds(self._settings.config())
            count = self._sources.new_verdicts(after)
        except (OrgError, OSError):
            return ""
        if count < th.after_verdicts:
            return ""
        return (DUE_LISTING if listing else DUE_REPLY).format(k=count, date=day(after) if after is not None else NONE_YET)
