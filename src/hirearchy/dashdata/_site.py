"""The organization as a place on disk, and the files the dashboard had to skip."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..kernel import BOXES, ROOT, OrgLayout
from ._ports import OrgSite, UnreadableSource
from .api import DashboardState


class Problems(UnreadableSource):
    """Problems the lenient readers note in a dictionary as they go (a charter that does not parse, an ORG.md that is damaged)."""

    def __init__(self, problems: Mapping[str, str]) -> None:
        self._problems = problems

    @property
    def bad(self) -> Mapping[str, str]:
        return self._problems


@dataclass(frozen=True)
class Unreadable:
    """Where a dashboard finds out which files it had to skip (none: a plain runtime reads strictly and skips nothing)."""

    sources: tuple[UnreadableSource, ...] = ()


class FsOrgSite(OrgSite):
    def __init__(self, layout: OrgLayout, state: DashboardState, sources: Sequence[UnreadableSource]) -> None:
        self._layout = layout
        self._state = state
        self._sources = sources

    def name(self) -> str:
        return self._layout.root.name

    def root(self) -> str:
        return str(self._layout.root)

    def retired(self) -> int:
        try:
            return sum(1 for p in self._layout.retired_dir().iterdir() if p.is_dir())
        except OSError:
            return 0

    def signature(self, agents: Sequence[str]) -> tuple[object, ...]:
        try:
            org_md = (self._layout.root / "ORG.md").stat().st_mtime_ns
        except OSError:
            org_md = 0
        parts: list[object] = [org_md]
        for a in (ROOT, *agents):
            parts.append(tuple(self._state.mtime(a, b) for b in (*BOXES, "runs", ".paused")))
        return tuple(parts)

    def unreadable(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for source in self._sources:
            out.update(source.bad)
        return out
