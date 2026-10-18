from .api import Mailbox


class MemoryMailbox(Mailbox):
    def __init__(self) -> None:
        self.items: list[str] = []

    def put(self, text: str) -> None:
        self.items.append(text)
