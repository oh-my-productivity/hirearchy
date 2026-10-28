"""The writer of ``AGENT.md``, of the directory skeleton of an agent (an empty ``MEMORY.md`` included) and of ``.retired/``."""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path

from ..kernel import BOXES, AtomicWriter, OrgLayout, join_frontmatter, norm
from .api import AgentRegistry


class FsAgentRegistry(AgentRegistry):
    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        self._paths = paths
        self._writer = writer

    def create(self, addr: str, meta: Mapping[str, object], charter_text: str) -> None:
        d = self._paths.agent_dir(addr)
        for sub in (*BOXES, "work", "runs"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        (d / "MEMORY.md").write_text("", encoding="utf-8")  # an empty file is a creation, not content: the agent writes the rest
        self._writer.write(d / "AGENT.md", join_frontmatter(dict(meta), charter_text))

    def rewrite_charter(self, addr: str, text: str) -> None:
        self._writer.write(self._paths.agent_dir(addr) / "AGENT.md", text)

    def archive(self, addr: str, stamp: str, record: Mapping[str, str] | None = None) -> str:
        a = norm(addr)
        name = f"{a.replace('/', '.')}-{stamp}"
        dest = self._paths.retired_dir() / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        moved = shutil.move(str(self._paths.agent_dir(a)), dest)  # where the tree is now: inside ``dest`` when that existed
        if record is not None:
            self._writer.write(Path(moved) / "RETIRED.md", join_frontmatter(dict(record), ""))
        return name
