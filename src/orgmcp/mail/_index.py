"""The front matter of every message file, for the readers that need the whole history at once (``observe``): parsed once per change."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, SupportsInt, cast, runtime_checkable

from ..agents import AgentDirectory
from ..kernel import BOXES, ROOT, JsonObject, OrgLayout, split_frontmatter
from ._rules import is_message_name
from .api import MessageFile, MessageIndex, MetaRead


@runtime_checkable
class MetaReader(Protocol):
    def read(self, path: Path) -> MetaRead:
        """The front matter of a message file, why it cannot be used (None when it can), and the file's mtime."""
        ...


def describe(text: str) -> tuple[JsonObject | None, str | None]:
    """The front matter of the text of a message file and what is wrong with it (None when nothing is)."""
    try:
        meta, _ = split_frontmatter(text)
    except Exception as exc:  # noqa: BLE001 - yaml errors of any kind
        return None, f"frontmatter does not parse ({type(exc).__name__})"
    error = None
    if not meta:
        error = "no frontmatter"
    elif not all(meta.get(k) for k in ("from", "to", "type")):
        error = "frontmatter lacks from/to/type"
    else:
        try:
            int(cast("SupportsInt | str", meta.get("budget") or 0))
        except (TypeError, ValueError):
            error = f"budget is not a number: {meta.get('budget')!r}"
    return meta, error


class StampCachedMetaReader(MetaReader):
    """Reads the front matter of a message file once per ``(path, mtime_ns, size)``: the former ``observe._META_CACHE`` (a process
    resource, ARCHITECTURE.md 2.4). Past ``max_entries`` the whole cache goes and is filled again by the next scan."""

    def __init__(self, max_entries: int = 50_000) -> None:
        self.cache: dict[tuple[str, int, int], tuple[JsonObject | None, str | None]] = {}
        self._max_entries = max_entries

    @property
    def max_entries(self) -> int:
        """How many files are remembered before the cache is emptied."""
        return self._max_entries

    def _read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

    def read(self, path: Path) -> MetaRead:
        try:
            st = path.stat()
            key = (str(path), st.st_mtime_ns, st.st_size)
            hit = self.cache.get(key)
            if hit is not None:
                return hit[0], hit[1], st.st_mtime
            text = self._read_text(path)
        except (OSError, UnicodeDecodeError) as exc:
            return None, f"unreadable ({type(exc).__name__})", 0.0
        meta, error = describe(text)
        if len(self.cache) > self.max_entries:
            self.cache.clear()
        self.cache[key] = (meta, error)
        return meta, error, st.st_mtime

    def clear(self) -> None:
        """Forget every file (the dict object stays)."""
        self.cache.clear()


class FsMessageIndex(MessageIndex):
    """Walks the boxes of root and of the live agents and asks the meta reader for each file."""

    def __init__(self, layout: OrgLayout, agents: AgentDirectory, meta: MetaReader) -> None:
        self._layout = layout
        self._agents = agents
        self._meta = meta

    def scan(self) -> list[MessageFile]:
        out: list[MessageFile] = []
        for owner in (ROOT, *self._agents.agents()):
            for box in BOXES:
                d = self._layout.box(owner, box)
                try:
                    names = sorted(n for n in os.listdir(d) if is_message_name(n))
                except OSError:
                    continue
                for n in names:
                    p = d / n
                    meta, error, mtime = self._meta.read(p)
                    mid = str((meta or {}).get("id") or p.stem)
                    out.append(MessageFile(p, owner, box, meta, error, mid, mtime))
        return out

    def meta_of(self, path: Path) -> MetaRead:
        return self._meta.read(path)
