# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json

from testkit.cli_world import main


def failures(org):
    return json.loads((org.root / ".runtime/failures.json").read_text())


def test_resume_resets_the_failure_count(org):
    org.save_ledger("failures", {"ceo": 3, "ceo/eng": 1})
    org.pause("ceo", "failures")
    main(["--root", str(org.root), "resume", "ceo"])
    assert org.paused("ceo") is None and failures(org) == {"ceo/eng": 1}
