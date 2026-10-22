# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import re

import pytest
import testkit

from testkit.blueprint_world import bpm

ROOT_DIR = testkit.REPO
SKILL = (ROOT_DIR / "skills" / "hirearchy" / "SKILL.md").read_text(encoding="utf-8")
README = (ROOT_DIR / "README.md").read_text(encoding="utf-8")


def role(name: str) -> str:
    return " ".join(bpm.get_role(name).body.lower().split())


def flat(text: str) -> str:
    return " ".join(text.lower().split())


@pytest.mark.parametrize("name", ["reviewer", "fact-checker", "data-checker", "code-reviewer"])
def test_verifiers_enumerate_independently_before_comparing(name):
    text = role(name)
    assert "enumerate independently" in text
    assert "item by item" in text
    assert "`ambiguous`" in text and "never exclude it silently" in text


def test_reviewer_lists_decisions_and_informal_commitments_and_checks_against_its_own_list():
    text = role("reviewer")
    for phrase in ("build your own list", "every decision and every commitment", "informal or unlabelled ones buried in prose",
                   "x said she'd", "we agreed y would", "write that list into your review",
                   "never against the author's selection", "one row for every action item"):
        assert phrase in text, phrase
    assert bpm.edits_others_files(bpm.get_role("reviewer").body) is None


def test_manager_says_feedback_never_waives_a_criterion_and_the_lead_does_not_rewrite():
    text = role("manager")
    for phrase in ("client feedback (a note with `feedback:`) is input for reflection",
                   "never waives an acceptance criterion",
                   "never a reason to report `done` with a criterion unmet",
                   "you never rewrite the author's deliverable yourself", "for a service request as for any task",
                   "go back to the author with `revises`"):
        assert phrase in text, phrase
    assert len(bpm.get_role("manager").body.splitlines()) <= 50


def test_manager_asks_before_delivery_and_forwards_two_readings():
    body = bpm.get_role("manager").body
    text = role("manager")
    assert "so they are asked before delivery" in text
    assert "any note of a verifier that a criterion can be read two ways (even one it calls non-blocking)" in text
    assert "before the delivery is accepted" not in text
    assert len(body.splitlines()) <= 50


def test_reviewer_marks_items_that_miss_a_criterions_purpose_ambiguous():
    text = role("reviewer")
    assert "fits a criterion's words but not its evident purpose" in text
    assert "list it, never decide it" in text
    assert "(nothing for anyone to do, a restatement, a status)" in text
    assert text.index("never exclude it silently") < text.index("fits a criterion's words") < text.index("if you cannot open the source")
    assert bpm.edits_others_files(bpm.get_role("reviewer").body) is None


def test_skill_asks_whether_informal_items_count_and_writes_it_into_the_first_criteria():
    text = flat(SKILL)
    for phrase in ('"what was decided, who does what", "list the risks"', "ask whether informal or unlabelled items count",
                   "from the first version", '"every commitment, including informal ones in prose"'):
        assert phrase in text, phrase


def test_skill_records_feedback_only_on_the_users_own_judgement():
    text = flat(SKILL)
    for phrase in ("only on the user's own judgement of the delivered result", '"keep it" / "what\'s wrong"',
                   '"deliver as is" or "i\'ll read it myself" is not an accept', "ask, or record nothing yet",
                   "a known unmet criterion stays unmet: say so", "feedback never waives it"):
        assert phrase in text, phrase


def test_skill_sizes_service_budgets_and_reads_the_send_reply():
    text = flat(SKILL)
    for phrase in ("per-request budget is the plan's estimate + 25%", "about 2 runs per delegation + 1",
                   "say in one line what that risks", "a rework needs about 2 runs per delegation it requires + 1",
                   "the `send(budget=n)` reply says what the recipient can hand down", "grant enough in one go",
                   "ask the user once, with that number"):
        assert phrase in text, phrase


def test_skill_stays_within_its_line_limit():
    assert len(SKILL.splitlines()) <= 125


def section() -> str:
    start = README.index("## Services and reflection")
    return flat(README[start:README.index("\n## ", start + 5)])


def test_readme_documents_the_round_f_behaviours():
    text = section()
    expectations = {
        "a keeps frontmatter": ("keeps every frontmatter key the new text does not set", "lists the kept and changed keys"),
        "b feedback is for reflection": ("for reflection only and never waives an acceptance criterion", "rule 10"),
        "c lessons on blocked": ("`lessons` are required for `done`, `failed` and `blocked` service reports",),
        "d latest lessons first": ("shows each case's latest lessons first",),
        "e send reply": ("`send(budget=n)` replies with what the recipient can now hand down", "estimate + 25%"),
        "f built-in read reads the org": ("built-in `read` can also read the organization's files", "read-only",
                                           "allowedpaths", "`work/` file directly"),
    }
    for label, phrases in expectations.items():
        for p in phrases:
            assert p in text, (label, p)
    assert re.search(r"required for `done`, `failed` and `blocked`", flat(README))
