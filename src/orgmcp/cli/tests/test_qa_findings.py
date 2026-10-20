# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.cli_world import main


def test_qa10_resume_with_trailing_slash_clears_failures(org):
    org.pause("ceo", "failures")
    for _ in range(3):
        org.record_failure("ceo")
    main(["--root", str(org.root), "resume", "ceo/"])
    assert org.ledger("failures").get("ceo", 0) == 0
