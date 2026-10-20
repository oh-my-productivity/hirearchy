# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.legacy.orgmcp.core import Org
from testkit.services_world import cli

from orgmcp.templates._documents import ORG_RULES
from orgmcp.templates.testing import static_document_templates

document_templates = static_document_templates()


# ------------------------------------------------------------------------------- the rules
def test_new_organizations_get_the_budget_and_review_rules(org):
    rules = org.rules()
    assert 'your remaining budget returns with the result' in rules and "`budget=N`" in rules
    assert "9. Reviews and fact-checks: a reviewer never edits another agent's file" in rules
    assert "Never write acceptance criteria" in rules and "revises=<task id>" in rules
    assert "{" not in rules  # the template was filled in completely


# ----------------------------------------------------------------- the rules
def test_rules_carry_the_contract_protocol(org):
    rules = org.rules()
    assert "verbatim" in rules and "never paraphrase" in rules.lower().replace("; ", " ")
    assert "verifiably met" in rules and "33 words means 33" in rules
    assert "`blocked` or `failed`" in rules and "cannot afford" in rules
    assert "`revises`" in rules or "revises=" in rules  # old rule 3 guidance survives
    assert "MEMORY.md" in rules and "condense" in rules  # old rule 6 guidance survives


def test_rules_numbering_is_contiguous():
    import re

    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", ORG_RULES, re.M)]
    assert numbers == list(range(1, len(numbers) + 1))


def test_org_rules_name_the_orgmcp_tools_unambiguously(tmp_path):
    rules = Org.init(tmp_path / "o", "m").rules()
    assert rules == document_templates.org_rules("m").strip()
    assert "kiro shows them as `@orgmcp/<tool>`, e.g. `@orgmcp/write`" in rules
    assert "built-in `write`/`read`/`shell`, those are different tools that reach the workspace only, never the org" in rules
    assert "with `@orgmcp/write`: artifacts go in `<you>/work/`" in rules and "with `@orgmcp/read`" in rules
    assert "(with `@orgmcp/write`, never the built-in `write`)" in rules


def test_rule_10_says_feedback_never_waives_a_criterion():
    rules = document_templates.org_rules("m")
    rule = rules[rules.index("10. Services"):]
    assert "client feedback never waives a criterion" in rule
    assert len(rule.splitlines()) <= 6


def test_new_organizations_carry_rule_10_and_upgrade_rules_propagates_it(org):
    assert "10. Services: a service is a standing kind of task your parent defined for you" in org.rules()
    assert "report it with `lessons`" in org.rules() and "revise_playbook" in org.rules()
    path = org.root / "ORG.md"
    text = path.read_text()
    path.write_text(text.split("10. Services:")[0].rstrip() + "\n")  # an organization created before services
    assert "10. Services" not in org.rules()
    cli(org, "upgrade-rules")
    assert "10. Services: a service is a standing kind of task" in org.rules()
    assert path.read_text() == text  # back to exactly the current template, settings and mission untouched
