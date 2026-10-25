# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
import testkit

from testkit.blueprint_world import bpm

ROOT_DIR = testkit.REPO
SKILL = (ROOT_DIR / "skills" / "hirearchy" / "SKILL.md").read_text(encoding="utf-8")
README = (ROOT_DIR / "README.md").read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.lower().split())


def test_skill_asks_instead_of_overriding_a_passed_reading_doubt():
    text = flat(SKILL)
    for phrase in ("an omission or clear violation verified against the source: send it back with `revises`",
                   "if the reviewer evidenced a pass and your doubt is how to read a criterion",
                   "ask the user one short question first", "never send it back on your own reading",
                   'or say the reviewer "missed" what you read differently'):
        assert phrase in text, phrase


def test_skill_elicits_relative_values_and_adds_nothing_unasked_silently():
    text = flat(SKILL)
    for phrase in ("how to treat relative or vague values", "'before friday', 'next week': turn into a date, or leave none?",
                   "write both answers into the criteria from the first version",
                   "never add a criterion, section or rule they did not ask for without saying so in one line"):
        assert phrase in text, phrase


def test_skill_states_the_cost_of_a_case():
    text = flat(SKILL)
    for phrase in ("a service request plus its reworks is one case", "before a rework that would take the case past the approved "
                   "per-request budget, ask the user, with the number", "the case total", "19 runs of the 15 approved per request"):
        assert phrase in text, phrase


def test_skill_plan_step_matches_the_clean_block():
    text = flat(SKILL)
    assert "from the line `plan for you`" in text and "machine-marker line" in text
    assert "(show this to the user" not in text and "end of plan for you" not in text
    assert len(SKILL.splitlines()) <= 125


def test_plan_heading_is_bare_and_the_draft_heading_stays_distinct():
    assert bpm.PLAN_HEADING == "PLAN FOR YOU"
    assert "show" not in bpm.PLAN_HEADING.lower() and "PLAN FOR YOU" not in bpm.PLAN_DRAFT_HEADING
    assert "do not show this to the user" in bpm.PLAN_DRAFT_HEADING


EXAMPLE = ROOT_DIR / "examples" / "blueprint-research.yaml"


@pytest.fixture
def bp(tmp_path):
    (tmp_path / "deliverables").mkdir()
    text = EXAMPLE.read_text().replace("~/deliverables", str(tmp_path / "deliverables"))
    return bpm.load_text(text), tmp_path


def bad(bp_roots):
    b, root = bp_roots
    b = dict(b)
    b["agents"] = []  # an invalid blueprint: a draft
    return b, root


def test_the_block_has_no_instruction_and_no_end_marker_inside_it(bp):
    b, root = bp
    found = bpm.validate(b, allowed_roots=[root])
    assert not bpm.errors(found), [i.render() for i in found]
    block = bpm.plan_for_user(b, found, allowed_roots=[root])
    assert block.splitlines()[0] == "PLAN FOR YOU"
    low = block.lower()
    assert "exactly as written" not in low and "end of plan" not in low and bpm.PLAN_END not in block


def test_propose_text_puts_the_instruction_before_and_the_marker_after_the_block(bp):
    b, root = bp
    out = bpm.propose_text(b, allowed_roots=[root])
    i, j, k = out.index(bpm.PLAN_SHOW), out.index(bpm.PLAN_HEADING), out.index(bpm.PLAN_END)
    assert i < j < k < out.index("Details (the full plan")
    assert out.count(bpm.PLAN_HEADING + "\n") == 1 and out.splitlines().count(bpm.PLAN_END) == 1
    assert "plan_id: " in out


def test_a_draft_is_marked_and_never_offered_to_show(bp):
    b, root = bad(bp)
    out = bpm.propose_text(b, allowed_roots=[root])
    assert bpm.PLAN_DRAFT_HEADING in out and "PLAN FOR YOU" not in out and bpm.PLAN_SHOW not in out
    assert "plan_id: none" in out


def test_readme_documents_the_round_g_behaviours():
    section = flat(README.split("## Services and reflection")[1].split("\n## Health")[0])
    for phrase in ('`reject "<words>" -> accept "<words>"`', "accepts that came after a reject", "also appears when a reject arrives",
                   "decide then whether the playbook must change", "client's feedback outranks the owner's own lessons",
                   "case total against the per-request budget", "client-driven reworks no longer count against an agent's `low_quality` health",
                   "asks the user", "relative or vague values", "bare `plan for you` line"):
        assert phrase in section, phrase
    # phase 0a documents source, criterion ids, the regression list and the evidence gate (the cap was 90)
    assert len(README.split("## Services and reflection")[1].split("\n## Health")[0].splitlines()) < 98
    assert "end-of-block marker sit outside it" in flat(README)


def test_readme_quality_section_names_the_view_and_stays_short():
    """PC-12: `## Quality (phase 0b)` sits after the last `## Org growth: phase ...` section and before `## Security notes`, in fewer than 30 lines."""
    assert README.index("## Org growth: phase 0a.5") < README.index("\n## Quality (phase 0b)") < README.index("\n## Security notes")
    section = README.split("\n## Quality (phase 0b)")[1].split("\n## ")[0]
    text = flat(section)
    for needle in ("hirearchy quality", "--json", "n/a (0 of 0)", "never counted as accepted", "relayed", "root only", "one-off", "`quality:`", "no ledger"):
        assert needle in text, needle
    assert len(section.splitlines()) < 30


def test_readme_health_row_says_escapes_and_old_keys_are_unread():
    health = README.split("\n## Health")[1].split("\n## ")[0]
    row = flat(next(line for line in health.splitlines() if line.startswith("| `low_quality` |")))
    for phrase in ("escapes / judged deliveries above the ratio", "the human client gave a verdict after it",
                   "an *escape* when that verdict was a reject", "count only when the user judged them", "typed by rule",
                   "the agent's re-checks after a fail and the author rework runs they cost",
                   "`max_escape_ratio` (0.5)", "`min_judged_for_quality` (3)"):
        assert phrase in row, phrase
    assert "max_problem_ratio" not in row and "min_tasks_for_quality" not in row
    assert "no rule reads them" in flat(health) and "an `org.md` that still sets them is not an error" in flat(health)


@pytest.mark.parametrize("old", ["(show this to the user exactly as written)", "END OF PLAN FOR YOU"])
def test_old_markers_are_gone_from_the_product_text(old):
    assert old not in bpm.PLAN_HEADING and old not in bpm.PLAN_END and old not in SKILL
