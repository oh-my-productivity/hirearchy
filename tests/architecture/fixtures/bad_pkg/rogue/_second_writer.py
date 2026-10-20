from pathlib import Path


def sneak(root: Path, ledgers) -> None:
    (root / "ORG.md").write_text("violation: ORG.md has exactly one writer, bad_pkg.settings")
    ledgers.read("failures")  # violation: the ledger "failures" belongs to eligibility
