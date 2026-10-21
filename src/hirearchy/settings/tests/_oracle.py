"""``LenientOrg.config`` of the dashboard, frozen verbatim from the class that was dissolved in C-dashdata (the settings read for the dashboard: ORG.md parsed once per
change, a broken one meaning the defaults, reported in ``bad``)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel import split_frontmatter
from hirearchy.settings import DEFAULT_CONFIG


class LenientConfig:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._cfg: tuple[tuple[int, int], dict[str, object]] | None = None
        self.bad: dict[str, str] = {}

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
            self.bad.pop("ORG.md", None)
            return cfg
        except Exception as exc:  # noqa: BLE001
            self.bad["ORG.md"] = type(exc).__name__
            return dict(DEFAULT_CONFIG)
