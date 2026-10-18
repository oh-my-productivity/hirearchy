from typing import Protocol

__all__ = ["Thing"]


class Thing(Protocol):
    def go(self) -> None: ...
