# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT, OrgError, join_frontmatter, split_frontmatter


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def test_oversized_message_from_an_agent_is_refused_with_advice(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    cap = org.config["max_message_chars"]
    assert cap == 20000
    org.send("ceo", "root", "x" * cap)  # exactly at the cap is fine
    with pytest.raises(OrgError, match="write the detail to a file"):
        org.send("ceo", "root", "x" * (cap + 1))
    task = org.delegate("ceo", "ceo/eng", "t", "g", "a", budget=2)
    with pytest.raises(OrgError, match="max_message_chars"):
        org.report("ceo/eng", task.id, "done", "y" * (cap + 1))
    with pytest.raises(OrgError, match="max_message_chars"):
        org.delegate("ceo", "ceo/eng", "t2", "g" * (cap + 1), "a", budget=1)


def test_the_cap_is_configurable_and_a_bad_value_means_the_default(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    configure(org, max_message_chars=50)
    with pytest.raises(OrgError):
        org.send("ceo", "root", "x" * 51)
    configure(org, max_message_chars="lots")
    org.send("ceo", "root", "x" * 5000)
