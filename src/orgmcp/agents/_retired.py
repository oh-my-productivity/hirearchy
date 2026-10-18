"""The retired trees: ``.retired/<address with . for />-<stamp>`` directories, read through the file tree they live in."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import BOXES, OrgLayout
from ._budget import message_budget
from .api import RetiredArchive, RetiredTree

RECV_BOXES = ("inbox", "inflight", "read")
_STAMP_SUFFIX = re.compile(r"-\d{8}T\d{6}$")


@runtime_checkable
class ArchiveFiles(Protocol):
    """The file tree under ``.retired``, as ``os.walk`` and ``os.listdir`` show it."""

    def walk(self, top: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
        """Like ``os.walk(top)``, top down: the caller may prune by changing the list of directories in place; nothing for what is no directory."""
        ...

    def listdir(self, path: Path) -> list[str]:
        """The names in a directory; ``OSError`` when there is no such directory."""
        ...

    def is_dir(self, path: Path) -> bool:
        ...

    def read_text(self, path: Path) -> str:
        """The text of a file, UTF-8; ``OSError`` or ``UnicodeDecodeError`` when it cannot be read."""
        ...


class OsArchiveFiles(ArchiveFiles):
    def walk(self, top: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
        for here, dirs, files in os.walk(top):
            yield Path(here), dirs, files

    def listdir(self, path: Path) -> list[str]:
        return os.listdir(path)

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")


class FsRetiredArchive(RetiredArchive):
    def __init__(self, paths: OrgLayout, files: ArchiveFiles) -> None:
        self._paths = paths
        self._files = files

    def trees(self) -> list[RetiredTree]:
        base = self._paths.retired_dir()
        try:
            names = sorted(self._files.listdir(base))
        except OSError:
            return []
        return [RetiredTree(n, "." not in _STAMP_SUFFIX.sub("", n), base / n) for n in names if self._files.is_dir(base / n)]

    def run_count(self) -> int:
        base = self._paths.retired_dir()
        try:
            names = sorted(self._files.listdir(base))
        except OSError:
            return 0
        count = 0
        for name in names:
            for here, dirs, files in self._files.walk(base / name):
                if here.name == "runs":
                    count += sum(1 for f in files if f.endswith(".log") and not f.startswith("."))
                    dirs.clear()
                else:  # only sub-agent directories can hold more run logs
                    dirs[:] = [d for d in dirs if d not in {*BOXES, "work"}]
        return count

    def unspent_budget(self, tree: RetiredTree) -> int:
        total = 0
        for here, dirs, files in self._files.walk(tree.path):
            if here.name in (*BOXES, "runs", "work", "services") or here.name.startswith("."):
                dirs.clear()
                continue
            if "AGENT.md" in files:
                total += sum(self._box_budget(here / b) for b in RECV_BOXES) - self._box_budget(here / "sent")
                runs = here / "runs"
                logs = self._files.listdir(runs) if self._files.is_dir(runs) else []
                total -= sum(1 for n in logs if n.endswith(".log") and not n.startswith("."))
        return total

    def _box_budget(self, box: Path) -> int:
        """The budget of the messages in one mailbox directory (0 for a directory that cannot be listed)."""
        try:
            names = self._files.listdir(box)
        except OSError:
            return 0
        total = 0
        for n in names:
            if n.endswith(".md") and not n.startswith("."):
                try:
                    text = self._files.read_text(box / n)
                except (OSError, UnicodeDecodeError):
                    continue
                total += message_budget(text)
        return total
