"""The changes of the bars (charters and models) from the organization's git history (design 7).

``reflection`` may not import ``snapshots``, so the composition root joins them: ``GitBarHistory`` asks ``OrgHistory`` which commits changed the
charters and ORG.md, reads each version once and compares consecutive versions of one file."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import Clock
from ..reflection import BarChanges, CharterMark, ModelMark
from ..reflection._ports import BarHistory
from ..settings import config_default_model, config_effort
from ..snapshots import Change, OrgHistory
from ._git_versions import COMMITS, ORG, TIME_BOUND, Version, read_version


class GitBarHistory(BarHistory):
    """``history.changes`` lists the commits; the text of each version is read once (it belongs to two pairs) and decoded strictly as UTF-8. A
    version that is above 64 KiB, cannot be read, is not UTF-8 or whose frontmatter does not parse gives no mark for either pair it belongs to
    and counts once in ``skipped``. The oldest listed version of a file has no predecessor in the list: no mark. Reading stops, with
    ``truncated``, once ``TIME_BOUND`` seconds of the clock have passed (read before each read)."""

    def __init__(self, history: OrgHistory, clock: Clock) -> None:
        self._history = history
        self._clock = clock

    def changes(self, addrs: Sequence[str]) -> BarChanges:
        paths = [f"{addr}/AGENT.md" for addr in addrs] + [ORG]
        found = self._history.changes(paths, COMMITS)
        if found is None:
            return BarChanges()
        started = self._clock.monotonic()
        marks: list[CharterMark | ModelMark] = []
        skipped = 0
        truncated = len({change.commit for change in found}) >= COMMITS  # the list was full: older changes may exist
        for path in paths:
            listed = [change for change in found if change.path == path]
            versions: dict[str, Version | None] = {}
            out_of_time = False
            for newer, older in zip(listed, listed[1:]):
                for change in (newer, older):
                    if change.commit in versions:
                        continue
                    if self._clock.monotonic() - started >= TIME_BOUND:
                        out_of_time = True
                        break
                    versions[change.commit] = read_version(self._history, change)
                    skipped += versions[change.commit] is None
                if out_of_time:
                    break
                after, before = versions[newer.commit], versions[older.commit]
                if after is not None and before is not None:
                    marks.extend(_compare(path, newer, before, after))
            truncated = truncated or out_of_time
        return BarChanges(known=True, marks=tuple(marks), truncated=truncated, skipped=skipped)


def _compare(path: str, newer: Change, before: Version, after: Version) -> list[CharterMark | ModelMark]:
    """The marks of one pair of consecutive versions: ``newer`` is the commit that holds ``after``."""
    if path == ORG:
        pairs = [("default_model", config_default_model(before.meta), config_default_model(after.meta)), ("effort", config_effort(before.meta), config_effort(after.meta))]
        return [ModelMark(ORG, key, old, new, newer.commit, newer.when) for key, old, new in pairs if old != new]
    addr = path.removesuffix("/AGENT.md")
    marks: list[CharterMark | ModelMark] = []
    if before.body != after.body:
        marks.append(CharterMark(addr, newer.commit, newer.when))
    old, new = _model(before), _model(after)
    if old != new:
        marks.append(ModelMark(addr, "model", old, new, newer.commit, newer.when))
    return marks


def _model(version: Version) -> str:
    return str(version.meta.get("model") or "").strip()


__all__ = ["GitBarHistory"]
