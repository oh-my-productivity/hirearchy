"""The retired trees: ``.retired/<address with . for />-<stamp>`` directories, read through the file tree they live in."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import BOXES, Message, OrgLayout, norm, split_frontmatter
from ._budget import credit_budget, message_budget
from .api import RetiredArchive, RetiredTree

RECV_BOXES = ("inbox", "inflight", "read")


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
        named = [RetiredTree(n, False, base / n) for n in names if self._files.is_dir(base / n)]
        return [replace(t, top_level="/" not in t.addr) for t in named]  # the one rule that names a tree says whether it is a direct report of root

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

    def credited(self) -> int:
        total = 0
        base = self._paths.retired_dir()
        try:
            names = sorted(self._files.listdir(base))
        except OSError:
            return 0
        for name in names:
            for here, dirs, files in self._files.walk(base / name):
                if here.name in (*BOXES, "runs", "work", "services") or here.name.startswith("."):
                    dirs.clear()
                    continue
                if "AGENT.md" in files:
                    total += sum(self._box_budget(here / b, credit_budget) for b in RECV_BOXES)
        return total

    def record(self, tree: RetiredTree) -> Mapping[str, str]:
        try:
            meta = split_frontmatter(self._files.read_text(tree.path / "RETIRED.md"))[0]
        except OSError:
            return {}
        except Exception:  # noqa: BLE001 - a record that is not text or not YAML is no record
            return {}
        return {str(k): str(v) for k, v in meta.items()}

    def memory(self, tree: RetiredTree, addr: str) -> str:
        directory = self._agent_dir(tree, addr)
        if directory is None or "MEMORY.md" not in self._names(directory):
            return ""
        return self._text(directory / "MEMORY.md")

    def results(self, tree: RetiredTree, addr: str) -> list[Message]:
        directory = self._agent_dir(tree, addr)
        if directory is None:
            return []
        sent = directory / "sent"
        found: list[Message] = []
        for name in self._names(sent):
            if name.endswith(".md") and not name.startswith("."):
                message = Message.parse(self._text(sent / name), sent / name)
                if message.type == "result":
                    found.append(message)
        return sorted(found, key=lambda m: m.id)

    def _agent_dir(self, tree: RetiredTree, addr: str) -> Path | None:
        """The archived directory of agent ``addr`` of the tree: the tree itself for its top agent, below it for a nested one; None for an address
        that is not in the tree."""
        top, here = tree.addr, norm(addr)
        if here == top:
            return tree.path
        if not here.startswith(top + "/"):
            return None
        return tree.path.joinpath(*here[len(top) + 1 :].split("/"))

    def _names(self, directory: Path) -> list[str]:
        try:
            return self._files.listdir(directory)
        except OSError:
            return []

    def _text(self, path: Path) -> str:
        """The text of a file, or ``OSError``: a file that is no text counts as unreadable."""
        try:
            return self._files.read_text(path)
        except UnicodeDecodeError as error:
            raise OSError(f"{path} is not valid UTF-8 ({error})") from error

    def _box_budget(self, box: Path, budget: Callable[[str], int] = message_budget) -> int:
        """The budget of the messages in one mailbox directory (0 for a directory that cannot be listed); ``budget`` reads one file's text."""
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
                total += budget(text)
        return total
