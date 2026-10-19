"""``FileAgentTexts``: the memory and the charter of an agent as text, read again only when the file changed."""

from __future__ import annotations

from pathlib import Path

from ..kernel import ROOT, OrgLayout
from ._const import TEXT_CAP
from ._ports import AgentTexts
from ._text import clean_text


class FileAgentTexts(AgentTexts):
    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout
        self._texts: dict[Path, tuple[tuple[int, int], str]] = {}

    def _read_cached(self, path: Path, cap: int = TEXT_CAP) -> str:
        try:
            st = path.stat()
        except OSError:
            return ""
        key = (st.st_mtime_ns, st.st_size)
        hit = self._texts.get(path)
        if hit and hit[0] == key:
            return hit[1]
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        text = clean_text(text)
        if len(text) > cap:
            text = f"[... {len(text) - cap} earlier characters not shown]\n" + text[-cap:]
        self._texts[path] = (key, text)
        return text

    def memory(self, addr: str) -> str:
        return self._read_cached(self._layout.agent_dir(addr) / "MEMORY.md") or "(no memory yet)"

    def charter(self, addr: str) -> str:
        if addr == ROOT:
            return "root is the human: no charter.\n\nORG.md rules:\n\n" + self._read_cached(self._layout.root / "ORG.md")
        return self._read_cached(self._layout.agent_dir(addr) / "AGENT.md") or "(no charter)"
