"""The text of an argument: literal, or ``@path/to/file``."""

from __future__ import annotations

from pathlib import Path

from ._ports import TextSource


class AtFileText(TextSource):
    """``value`` as it is, or the text of the file named after an ``@``."""

    def read(self, value: str) -> str:
        raise NotImplementedError
