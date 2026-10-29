"""The retired copies of services, for the retro brief (design 4.5, L22).

No public port of ``services`` lists the copies in ``<owner>/services/.retired/<name>-<stamp>/``, so ``retro`` names the port it needs (``ServiceRetirements``) and the
composition root implements it: every agent's ``.retired`` directory is listed through the layout, and each copy's ``RETIRED.md`` is read for its record."""

from __future__ import annotations

import re
from pathlib import Path

from ..agents import AgentDirectory
from ..kernel import OrgLayout, parse_time, split_frontmatter
from ..retro._ports import ServiceRetirements
from ..retro._views import ServiceRetired

_COPY = re.compile(r"^(?P<name>.+)-\d{8}T\d{6}(?:\d{6})?$")  # ``<name>-<stamp>`` (``%Y%m%dT%H%M%S%f``, the seconds alone in an older copy): a copy's directory
_RECORD = "RETIRED.md"


class FsServiceRetirements(ServiceRetirements):
    """``retired`` lists the copies of every agent (the agents in the directory's order, the copies by directory name). A directory whose name has no stamp, a copy with no
    ``RETIRED.md`` and a record that is not text or not YAML are left out; it never raises."""

    def __init__(self, directory: AgentDirectory, layout: OrgLayout) -> None:
        self._directory = directory
        self._layout = layout

    def retired(self) -> tuple[ServiceRetired, ...]:
        found: list[ServiceRetired] = []
        try:
            owners = sorted(self._directory.agents())
        except OSError:
            return ()
        for owner in owners:
            found += self._of(owner)
        return tuple(found)

    def _of(self, owner: str) -> list[ServiceRetired]:
        base = self._layout.agent_dir(owner) / "services" / ".retired"
        try:
            names = sorted(p.name for p in base.iterdir() if p.is_dir())
        except OSError:
            return []
        read = (self._read(owner, name, base / name) for name in names if _COPY.match(name))
        return [r for r in read if r is not None]

    @staticmethod
    def _read(owner: str, directory: str, path: Path) -> ServiceRetired | None:
        match = _COPY.match(directory)
        if match is None:
            return None
        try:
            meta = split_frontmatter((path / _RECORD).read_text(encoding="utf-8"))[0]
        except Exception:  # noqa: BLE001 - no record, not text, or YAML that does not parse: the copy has no record
            return None
        if not meta:
            return None
        return ServiceRetired(owner, match["name"], parse_time(meta.get("retired")), str(meta.get("by") or ""), str(meta.get("reason") or ""), str(meta.get("approved_in") or ""))
