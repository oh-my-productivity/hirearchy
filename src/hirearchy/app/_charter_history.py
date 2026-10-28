"""The committed versions of the charters and ORG.md as pairs, for the retro brief (design 4.1, 4.5).

``retro`` may not import ``snapshots``, so the composition root joins them: ``GitCharterHistory`` asks ``OrgHistory`` which commits changed the charters
and ORG.md, reads each version once (``_git_versions``, the reader ``GitBarHistory`` shares) and describes each pair of consecutive versions by what the
files hold: the frontmatter keys that differ, the lines of the added section before and after, whether the body outside it differs, and for ORG.md the
``max_depth`` before and after. The labels are read from this content, never from a commit message, because a commit can hold another process's edit."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime

from ..blueprint._added import added_section
from ..kernel import Clock
from ..retro._ports import CHARTER, ORG, CharterHistory, CharterPair, CharterVersions, KeyChange
from ..settings import config_number
from ..snapshots import Change, OrgHistory
from ._git_versions import COMMITS, TIME_BOUND, Version, read_version

ORG_COMMITS = 1000  # the newest commits that changed ORG.md among which the one that added it is looked for


def _text(value: object) -> str:
    """A frontmatter value as text (``KeyChange``): booleans as ``true``/``false``, a list or mapping as sorted JSON."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    return str(value)


def _keys(before: Mapping[str, object], after: Mapping[str, object]) -> tuple[KeyChange, ...]:
    """The keys whose value differs between two frontmatters, by key."""
    absent = object()
    changed = [k for k in sorted({*before, *after}) if before.get(k, absent) != after.get(k, absent)]
    return tuple(KeyChange(k, _text(before[k]) if k in before else None, _text(after[k]) if k in after else None) for k in changed)


def _split(body: str) -> tuple[tuple[str, ...], str]:
    """The lines of the added section (stripped, blanks left out) and the body without that section."""
    found = added_section(body)
    if found is None:
        return (), body.strip()
    lines = body.splitlines()
    inside = tuple(line.strip() for line in lines[found[0] : found[1]] if line.strip())
    return inside, "\n".join([*lines[: found[0] - 1], *lines[found[1] :]]).strip()


class GitCharterHistory(CharterHistory):
    """``versions`` lists the commits that changed the files (the newest 40) and reads each version once, stopping with ``truncated`` after 5 s of the
    clock. A version above 64 KiB, unreadable, not UTF-8 or whose frontmatter does not parse is not compared, for either pair it belongs to, and counts
    once in ``skipped``. The oldest listed version of a file has no predecessor in the list: no pair. A file that is absent in one of two consecutive
    commits is a pair of kind ``created`` or ``deleted``, never an edit. The pairs are in the history's order, the newest commit first."""

    def __init__(self, history: OrgHistory, clock: Clock) -> None:
        self._history = history
        self._clock = clock

    def versions(self, addrs: Sequence[str]) -> CharterVersions:
        paths = [f"{addr}/{CHARTER}" for addr in addrs] + [ORG]
        found = self._history.changes(paths, COMMITS)
        if found is None:
            return CharterVersions(known=False)
        started = self._clock.monotonic()
        pairs: list[CharterPair] = []
        skipped = 0
        truncated = len({change.commit for change in found}) >= COMMITS  # the list was full: older changes may exist
        for path in paths:
            listed = [change for change in found if change.path == path]
            versions: dict[str, Version | None] = {}
            out_of_time = False
            for newer, older in zip(listed, listed[1:]):
                present = (self._history.blob(newer.commit, path) is not None, self._history.blob(older.commit, path) is not None)
                if present == (True, False):
                    pairs.append(CharterPair(path, newer.commit, newer.when, kind="created"))
                    continue
                if present == (False, True):
                    pairs.append(CharterPair(path, newer.commit, newer.when, kind="deleted"))
                    continue
                if present == (False, False):
                    continue
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
                    pair = _pair(path, newer, before, after)
                    if pair is not None:
                        pairs.append(pair)
            truncated = truncated or out_of_time
        order = {(change.commit, change.path): n for n, change in enumerate(found)}  # the history's order: the newest commit first
        pairs.sort(key=lambda pair: order[(pair.commit, pair.path)])
        return CharterVersions(True, tuple(pairs), truncated, skipped)

    def subject(self, commit: str) -> str | None:
        return self._history.subject(commit)

    def org_started(self) -> datetime | None:
        first = self._history.first_commit_with(ORG)
        if first is None:
            return None
        listed = self._history.changes([ORG], ORG_COMMITS) or []
        return next((change.when for change in listed if change.commit == first), None)


def _pair(path: str, newer: Change, before: Version, after: Version) -> CharterPair | None:
    """The pair of two consecutive versions; None for an ORG.md whose ``max_depth`` did not change."""
    if path == ORG:
        old, new = config_number(before.meta, "max_depth", int), config_number(after.meta, "max_depth", int)
        return CharterPair(path, newer.commit, newer.when, depth=(str(old), str(new))) if old != new else None
    added_before, outside_before = _split(before.body)
    added_after, outside_after = _split(after.body)
    return CharterPair(
        path, newer.commit, newer.when, keys=_keys(before.meta, after.meta), added_before=added_before, added_after=added_after,
        body_differs=outside_before != outside_after,
    )


__all__ = ["GitCharterHistory"]
