# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.hirearchy.core import Org
from testkit.services_world import cli

from hirearchy.templates._documents import ORG_RULES
from hirearchy.templates.testing import static_document_templates

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


def test_org_rules_name_the_hirearchy_tools_unambiguously(tmp_path):
    rules = Org.init(tmp_path / "o", "m").rules()
    assert rules == document_templates.org_rules("m").strip()
    assert "kiro shows them as `@hirearchy/<tool>`, e.g. `@hirearchy/write`" in rules
    assert "built-in `write`/`read`/`shell`, those are different tools that reach the workspace only, never the org" in rules
    assert "with `@hirearchy/write`: artifacts go in `<you>/work/`" in rules and "with `@hirearchy/read`" in rules
    assert "(with `@hirearchy/write`, never the built-in `write`)" in rules


def test_rule_10_says_feedback_never_waives_a_criterion():
    rules = document_templates.org_rules("m")
    rule = rules[rules.index("10. Services"):]
    assert "client feedback never waives a criterion" in " ".join(rule.split())  # the phrase wraps across two lines
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


# ------------------------------------------------------- org growth phase 0a: rule 10 asks for the client's evidence
RULE_10 = (
    "10. Services: a service is a standing kind of task your parent defined for you (`<you>/services/<name>/`: the\n"
    "   contract SERVICE.md is your parent's; the playbook PLAYBOOK.md is yours). Each request is a task: follow the\n"
    "   playbook and the contract's criteria; report it with `lessons`. Improve the playbook with `revise_playbook` when the\n"
    "   client's evidence calls for it, and cite it (`evidence`: the client's rejections R<k> and criteria C<k>; lessons and\n"
    "   `source: relayed` messages, the assistant's own reading, are not evidence); never lower the bar (client feedback\n"
    "   never waives a criterion), and propose contract changes to your parent.\n"
)
RULES_1_TO_9_SHA256 = "87c831c3d8ed6c2992ae4578bf9609ff7e39308aa06d661ff069006f3f720312"


def test_rule_10_asks_for_the_clients_evidence_and_says_lessons_and_relayed_are_not():
    rules = document_templates.org_rules("m")
    assert rules[rules.index("10. Services"):] == RULE_10
    assert "from the evidence shown before a new request" not in rules
    assert "evidence shown before a new request" not in rules
    assert "{" not in RULE_10 and "}" not in RULE_10


def test_rules_1_to_9_are_unchanged():
    import hashlib

    before = ORG_RULES[: ORG_RULES.index("10. Services")]
    assert hashlib.sha256(before.encode()).hexdigest() == RULES_1_TO_9_SHA256
