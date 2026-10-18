from typing import Protocol

__all__ = ["OrgDocuments"]


class OrgDocuments(Protocol):
    def write(self, text: str) -> None: ...
