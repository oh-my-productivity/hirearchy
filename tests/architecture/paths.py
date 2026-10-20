"""Where things are: the repository, the source tree under check, the seeded violations."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "orgmcp"
FIXTURES = Path(__file__).parent / "fixtures"
DOCUMENT = REPO / "ARCHITECTURE.md"
