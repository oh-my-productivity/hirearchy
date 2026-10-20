class Registry:
    def __init__(self) -> None:
        self.items: dict[str, int] = {}

    def add(self, key: str) -> None:
        self.items[key] = 1


REGISTRY = Registry()  # violation: module-level singleton
CACHE = {}  # violation: module-level mutable state
