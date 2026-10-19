"""The dashboard's ``LenientOrg`` as it was before it was dissolved: an ``Org`` that skips what it cannot read and caches what it has read.

Production no longer has it: the dashboard's runtime (``wire_dashdata.dashboard_runtime``) puts the decorators of the read ports (``agents``,
``mail``, ``settings``, ``runs``, ``eligibility``) in the place of the strict ones. This copy stays for the tests that characterize those
decorators against the original (``runs.CachingRunLogReader`` and ``settings.CachingOrgSettings`` against ``runs_used`` and ``config``, as they
were written here) and for the tests that hand a lenient ``Org`` to the legacy functions of the other packages. It goes with them (step E3).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from ...kernel import ROOT, split_frontmatter
from .. import wire_agents, wire_budget, wire_eligibility, wire_mail
from ..facade import DEFAULT_CONFIG, Org

CACHE_TRUST = 2.0  # a directory modified less than this many seconds before it was listed is listed again next time


class LenientOrg(Org):
    """An Org that keeps going: unreadable messages and charters are skipped (listed in :attr:`bad`), parsed mailboxes
    are cached per directory mtime (a box that did not change is not read again), ORG.md is parsed once per change."""

    def __init__(self, root: str | Path):
        super().__init__(root)
        self._cfg: tuple[tuple[int, int], dict[str, object]] | None = None
        self._bad_misc: dict[str, str] = {}
        self._runs_cache: dict[str, tuple[int, bool, int]] = {}
        self._stat_memo: dict[tuple[str, str], int] = {}
        self._root_s = str(self.root)
        # the caching of the agent tree and the reading of charters (reported in ``bad``) are the decorators of the agents package,
        # the caching of the mailboxes (their unreadable files reported in ``bad`` too) the one of the mail package
        self.runtime = wire_agents.lenient(self.runtime, self, self._bad_misc)
        self.runtime, self._mailbox = wire_mail.lenient(self.runtime, self)
        # the budget is derived from those boxes and agents, and its run count is the cached ``runs_used`` of this class
        self.runtime = wire_budget.lenient(self.runtime, self.runs_used)
        # the pause flags are read per change of their file (the decorator of the eligibility package, asking this class for the mtime), and
        # the state words and what may run are derived from the boxes, the budgets and those flags
        self.runtime = wire_eligibility.lenient(self.runtime, self)

    @property
    def bad(self) -> dict[str, str]:
        """Files that could not be read: path (relative to the org) -> why."""
        out = dict(self._bad_misc)
        out.update(self._mailbox.bad)
        return out

    # -- one stat per directory per tick
    def tick(self) -> None:
        """Start a new refresh: directory mtimes are looked at again (within one refresh each is stat'ed once)."""
        self._stat_memo.clear()

    def mtime(self, addr: str, name: str) -> int:
        """mtime_ns of ``<addr>/<name>`` (-1: missing), stat'ed at most once per tick. ``name`` "" is the agent dir."""
        a = self.norm(addr)
        key = (a, name)
        v = self._stat_memo.get(key)
        if v is None:
            path = self._root_s if a == ROOT else os.path.join(self._root_s, a)
            try:
                v = os.stat(os.path.join(path, name) if name else path).st_mtime_ns
            except OSError:
                v = -1
            self._stat_memo[key] = v
        return v

    def _trusted(self, listed_at: int, mtime: int) -> bool:
        """A listing is reused only if the directory had been quiet for a while when it was made (coarse-mtime safe)."""
        return (listed_at - mtime) > CACHE_TRUST * 1e9

    def runs_used(self, addr: str) -> int:
        mtime = self.mtime(addr, "runs")
        if mtime < 0:
            return 0
        key = self.norm(addr)
        hit = self._runs_cache.get(key)
        if hit is not None and hit[0] == mtime and hit[1]:
            return hit[2]
        listed_at = time.time_ns()
        n = super().runs_used(addr)
        self._runs_cache[key] = (mtime, self._trusted(listed_at, mtime), n)
        return n

    def _rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return str(p)

    # -- config
    @property
    def config(self) -> dict[str, object]:
        p = self.root / "ORG.md"
        try:
            st = p.stat()
            stamp = (st.st_mtime_ns, st.st_size)
            if self._cfg is not None and self._cfg[0] == stamp:
                return self._cfg[1]
            meta, _ = split_frontmatter(p.read_text(encoding="utf-8"))
            cfg = {**DEFAULT_CONFIG, **(meta if isinstance(meta, dict) else {})}
            self._cfg = (stamp, cfg)
            self._bad_misc.pop("ORG.md", None)
            return cfg
        except Exception as exc:  # noqa: BLE001
            self._bad_misc["ORG.md"] = type(exc).__name__
            return dict(DEFAULT_CONFIG)
