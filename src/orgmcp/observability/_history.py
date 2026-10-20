"""The history of the messages, from the front matter that the message index read."""

from __future__ import annotations

from ..mail import MessageIndex
from ._messages import Msg, build_messages
from ._ports import MessageHistory


class IndexedMessageHistory(MessageHistory):
    """Every message once, from the index of the mail package (which parses each file once per change)."""

    def __init__(self, index: MessageIndex) -> None:
        self._index = index

    def messages(self) -> dict[str, Msg]:
        return build_messages(self._index.scan())
