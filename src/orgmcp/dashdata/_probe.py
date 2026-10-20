"""``DirMtimeProbe``: one ``stat`` per directory per refresh."""

from __future__ import annotations

import os

from ..kernel import ROOT, OrgLayout, norm
from ._ports import MtimeProbe


class DirMtimeProbe(MtimeProbe):
    """The modification time of the directories of an organization, looked at once per refresh (``tick`` starts the next one).

    It is what the caches of the dashboard ask when they must know whether a directory changed: the mailboxes, the agent tree, the run logs,
    the pause flags. A directory the memo has seen this refresh costs a dictionary lookup, not a ``stat``."""

    def __init__(self, layout: OrgLayout) -> None:
        self._root = str(layout.root)
        self._memo: dict[tuple[str, str], int] = {}

    def tick(self) -> None:
        self._memo.clear()

    def mtime(self, addr: str, name: str) -> int:
        a = norm(addr)
        key = (a, name)
        v = self._memo.get(key)
        if v is None:
            path = self._root if a == ROOT else os.path.join(self._root, a)
            try:
                v = os.stat(os.path.join(path, name) if name else path).st_mtime_ns
            except OSError:
                v = -1
            self._memo[key] = v
        return v
