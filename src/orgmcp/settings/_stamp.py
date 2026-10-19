"""The change stamp of ORG.md: what the caching decorators compare to know whether to read the file again."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import OrgLayout


@runtime_checkable
class OrgDocumentStamp(Protocol):
    def stamp(self) -> tuple[int, int]:
        """``(mtime_ns, size)`` of ORG.md; raises ``OSError`` when it cannot be looked at (missing)."""
        ...


class FsOrgDocumentStamp(OrgDocumentStamp):
    def __init__(self, paths: OrgLayout) -> None:
        self._document = paths.root / "ORG.md"  # joined once: ``stamp`` runs on every emitted event

    def stamp(self) -> tuple[int, int]:
        st = self._document.stat()
        return (st.st_mtime_ns, st.st_size)
