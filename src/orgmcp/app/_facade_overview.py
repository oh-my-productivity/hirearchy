"""The organization tree with one state line per agent (overview).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from ..kernel import ROOT


class OverviewMixin:
    """The organization tree with one state line per agent (overview)."""

    def tree(self) -> str:
        lines = [f"root (human): unread {self.unread(ROOT)}, delegated {len(self.outstanding(ROOT))}"]
        for a in self.agents():
            meta, _ = self.charter(a)
            name = a.rsplit("/", 1)[-1]
            offered = self.service_names(a)
            lines.append(
                "  " * self.depth(a) + f"{name} [{meta.get('role', '?')}] {self.state(a)}  budget={self.budget(a)} "
                f"open={len(self.open_tasks(a))} delegated={len(self.outstanding(a))} unread={self.unread(a)}"
                + (f" services: {', '.join(offered)}" if offered else "")
            )
        return "\n".join(lines)
