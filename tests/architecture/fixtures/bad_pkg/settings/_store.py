from pathlib import Path

from .api import OrgDocuments


class FsOrgDocuments(OrgDocuments):
    """The legitimate, single writer of ORG.md: must NOT be flagged."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, text: str) -> None:
        (self.root / "ORG.md").write_text(text, encoding="utf-8")
