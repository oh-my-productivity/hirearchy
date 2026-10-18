"""Process-scope resources: what the module globals were, created once per process (ARCHITECTURE.md 2.4)."""

from __future__ import annotations

from ..mail._index import StampCachedMetaReader
from ..mail._parser import CachingMessageParser


class ProcessResources:
    """The objects that exist once per process and are shared by every organization runtime in it."""

    def __init__(self, message_parser: CachingMessageParser, meta_cache: StampCachedMetaReader | None = None) -> None:
        self.message_parser = message_parser  # the 50 000-entry parse cache (the former ``core._PARSED``)
        self.meta_cache = meta_cache or StampCachedMetaReader()  # the 50 000-entry front-matter cache (the former ``observe._META_CACHE``)

    def reset(self) -> None:
        """Empty every resource (tests start from a clean process); the objects themselves stay."""
        self.message_parser.clear()
        self.meta_cache.clear()
