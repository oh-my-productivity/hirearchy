"""RED skeleton (step A-agents)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import OrgLayout
from .api import RetiredArchive, RetiredTree


@runtime_checkable
class ArchiveFiles(Protocol):
    def walk(self, top: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
        raise NotImplementedError

    def listdir(self, path: Path) -> list[str]:
        raise NotImplementedError

    def is_dir(self, path: Path) -> bool:
        raise NotImplementedError

    def read_text(self, path: Path) -> str:
        raise NotImplementedError


class OsArchiveFiles(ArchiveFiles):
    def walk(self, top: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
        raise NotImplementedError("red: A-agents")

    def listdir(self, path: Path) -> list[str]:
        raise NotImplementedError("red: A-agents")

    def is_dir(self, path: Path) -> bool:
        raise NotImplementedError("red: A-agents")

    def read_text(self, path: Path) -> str:
        raise NotImplementedError("red: A-agents")


class FsRetiredArchive(RetiredArchive):
    def __init__(self, paths: OrgLayout, files: ArchiveFiles) -> None:
        raise NotImplementedError("red: A-agents")

    def trees(self) -> list[RetiredTree]:
        raise NotImplementedError("red: A-agents")

    def run_count(self) -> int:
        raise NotImplementedError("red: A-agents")

    def unspent_budget(self, tree: RetiredTree) -> int:
        raise NotImplementedError("red: A-agents")
