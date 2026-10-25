# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import re

from testkit.blueprint_world import ex as blueprint_examples

from testkit.blueprint_world import bpm as bp_mod


# --------------------------------------------------------------------------------------------- the plan block
def doc_bp(tmp_path, monkeypatch):
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
    (tmp_path / "<folder-with-your-files>").mkdir(exist_ok=True)
    return bp_mod.load_text(blueprint_examples.example("documents", tmp_path))


def goal_line(block: str) -> str:
    return next(x for x in block.splitlines() if x.startswith("Goal: "))


def test_failure_policy_line_under_the_budget(tmp_path, monkeypatch):
    block = bp_mod.plan_for_user(doc_bp(tmp_path, monkeypatch))
    lines = block.splitlines()
    i = next(n for n, x in enumerate(lines) if x.startswith("Budget:"))
    policy = next(x for x in lines[i:i + 4] if x.startswith("If the check still fails after one rework"))
    total, minimum = map(int, re.search(r"Budget: (\d+) runs planned.*minimum for one review and rework is (\d+)", lines[i]).groups())
    reserve = total - minimum
    assert reserve > 0
    assert policy == (f"If the check still fails after one rework, I'll come back to you with options before spending the "
                      f"reserve (about {reserve} runs); nothing beyond the {total} planned runs is spent without your OK.")
    assert len(lines) <= 42


def test_failure_policy_without_a_reserve(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    minimum = int(re.search(r"minimum for one review and rework is (\d+)", bp_mod.plan_for_user(bp)).group(1))
    bp["task"]["budget"] = minimum
    block = bp_mod.plan_for_user(bp)
    assert (f"If the check still fails after one rework, I'll come back to you with options; the plan has no reserve "
            f"beyond that rework, and nothing beyond the {minimum} planned runs is spent without your OK.") in block


def test_a_long_mission_is_shown_whole_in_the_goal_line(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    mission = ("Research the competitive landscape of the three products and summarise pricing, positioning and recent "
               "releases for a leadership audience, citing a source for every claim. Highlight the top three risks "
               "for the next quarter and say how sure we are about each of them. " * 2).strip()
    assert 220 < len(mission) < 800
    bp["mission"] = mission
    assert goal_line(bp_mod.plan_for_user(bp)) == f"Goal: {mission}"


def test_a_very_long_mission_is_cut_at_a_sentence_boundary(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    sentences = [f"Sentence number {i} says something rather long about the work to do, " + "x" * 280 + "." for i in range(1, 5)]
    bp["mission"] = " ".join(sentences)
    goal = goal_line(bp_mod.plan_for_user(bp))
    assert goal == f"Goal: {sentences[0]} {sentences[1]} (the rest is in the details)"
    assert "..." not in goal and "…" not in goal


def test_a_single_long_sentence_is_never_cut(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    one = "Do the whole thing " + "and then some more " * 80 + "properly."
    bp["mission"] = one
    assert goal_line(bp_mod.plan_for_user(bp)) == f"Goal: {one}"


def test_clip_helper_and_other_lines_do_not_cut_mid_sentence(tmp_path, monkeypatch):
    assert bp_mod._clip("Short.") == "Short."
    text = "First one. " + "Second sentence here. " * 30 + "Last."
    out = bp_mod._clip(text, 100)
    assert out.endswith(" (the rest is in the details)") and out.removesuffix(" (the rest is in the details)").endswith(".")
    bp = doc_bp(tmp_path, monkeypatch)
    long_criterion = "The report lists every competitor by name, with a price for each plan, and says where the price was found " * 4 + "end."
    bp["task"]["acceptance"] = [long_criterion, "Second criterion."]
    bp["needs"]["scope"] = "Scope part one is short. " + "More scope detail that goes on and on. " * 20
    block = bp_mod.plan_for_user(bp)
    assert f"  1. {long_criterion}" in block  # the contract is shown in full
    scope = next(x for x in block.splitlines() if x.startswith("- Scope: "))
    assert scope.endswith(" (the rest is in the details)") and "..." not in scope


def test_a_services_plan_names_the_client_round_in_the_budget_line_and_the_details_header(tmp_path):
    """D-E5-2: E5's numbers (cap 12, estimate 11, a round of 5) show the number that covers one round of the user's questions."""
    from .test_services import e5_blueprint

    bp = e5_blueprint(tmp_path)
    block = bp_mod.plan_for_user(bp, allowed_roots=[tmp_path])
    assert ("Budget: up to 12 runs per request (one run = one working session of one agent), your cap per request is 12; the minimum for one review "
            "and rework is 11, and a round of your questions or a rejection takes about 5 more (16 in all). Unspent runs come back to you.") in block
    details = bp_mod.render_plan(bp, allowed_roots=[tmp_path])
    assert ("Budget per request (your cap: 12), estimate 11 for one pass + one review/rework cycle, "
            "16 with one round of your questions or a rejection:") in details


def test_a_plain_task_plan_has_no_client_round(tmp_path, monkeypatch):
    bp = doc_bp(tmp_path, monkeypatch)
    assert "round of your questions" not in bp_mod.plan_for_user(bp) and "round of your questions" not in bp_mod.render_plan(bp)


# ------------------------------------------------------------------------------- the plan's budget question (D-E7-3)
ASK = "Use 16 runs per request (covers one round of your questions or a rejection), or keep 12?"
ASK_FOR = "Use 16 runs per request for {name} (covers one round of your questions or a rejection), or keep 12?"
APPROVE = "Nothing is created or started until you approve. Reply 'approve', or tell me what to change."


def two_services(tmp_path, second_budget=12):
    """E5's blueprint with a second service, ``weekly-brief``, after ``weekly-meeting-memo``; the cap is 20 so a budget of 16 is allowed."""
    from .test_services import e5_blueprint, service

    bp = e5_blueprint(tmp_path)
    bp["needs"]["budget_runs"] = 20
    bp["services"].append(service(name="weekly-brief", budget=second_budget, acceptance=["At most 600 words as counted by read."],
                                  deliverable={"description": "One markdown file", "format": "markdown", "max_words": 600, "path": str(tmp_path / "deliverables" / "briefs")}))
    assert not bp_mod.errors(bp_mod.validate(bp, allowed_roots=[tmp_path]))
    return bp


def test_the_block_of_a_budget_below_one_client_round_ends_with_the_question(tmp_path):
    """D-E7-3: E5's numbers (estimate 11, a round of 5, budget 12) end the block with the plan's number, right after the approve line."""
    from .test_services import e5_blueprint

    block = bp_mod.plan_for_user(e5_blueprint(tmp_path), allowed_roots=[tmp_path])
    assert block.splitlines()[-2:] == [APPROVE, ASK]


def test_a_budget_that_covers_a_client_round_has_no_question(tmp_path):
    from .test_services import e5_blueprint

    bp = e5_blueprint(tmp_path, budget=16)
    bp["needs"]["budget_runs"] = 20
    assert bp_mod.plan_for_user(bp, allowed_roots=[tmp_path]).splitlines()[-1] == APPROVE


def test_a_plan_with_an_error_has_no_question(tmp_path):
    from .test_services import e5_blueprint

    bp = e5_blueprint(tmp_path)
    bp["services"][0]["acceptance"] = []
    block = bp_mod.plan_for_user(bp, allowed_roots=[tmp_path])
    assert block.splitlines()[-1] == "Cannot apply yet." and "Use 16 runs" not in block


def test_a_plain_task_has_no_question(tmp_path, monkeypatch):
    block = bp_mod.plan_for_user(doc_bp(tmp_path, monkeypatch), allowed_roots=[tmp_path])
    assert "Use " not in block.splitlines()[-1] and "runs per request" not in block.splitlines()[-1]


def test_every_service_below_a_client_round_gets_its_own_named_line_in_blueprint_order(tmp_path):
    """DR-0a5-4: with more than one service the unnamed line could not tell the user which service the number is for."""
    block = bp_mod.plan_for_user(two_services(tmp_path), allowed_roots=[tmp_path])
    assert block.splitlines()[-3:] == [APPROVE, ASK_FOR.format(name="weekly-meeting-memo"), ASK_FOR.format(name="weekly-brief")]


def test_a_single_offer_among_several_services_is_still_named(tmp_path):
    """DR-0a5-4: one service at 12 and one at 16: one line, for the first, in the named form."""
    block = bp_mod.plan_for_user(two_services(tmp_path, second_budget=16), allowed_roots=[tmp_path])
    assert block.splitlines()[-2:] == [APPROVE, ASK_FOR.format(name="weekly-meeting-memo")]
    assert block.count("Use 16 runs") == 1


def test_the_question_needs_a_budget_tight_warning_among_the_issues_it_is_rendered_with(tmp_path):
    """DR-0a5-5: the line is emitted only with the warning, so a caller that passes its own issues sees none without one."""
    from .test_services import e5_blueprint

    bp = e5_blueprint(tmp_path)
    assert bp_mod.plan_for_user(bp, [], allowed_roots=[tmp_path]).splitlines()[-1] == APPROVE
    other = [bp_mod.Issue("warning", "x", "some other warning", "deliverable-format")]
    assert bp_mod.plan_for_user(bp, other, allowed_roots=[tmp_path]).splitlines()[-1] == APPROVE
    tight = bp_mod.Issue("warning", "needs.budget_runs", "tight", "budget-tight")
    assert bp_mod.plan_for_user(bp, [tight], allowed_roots=[tmp_path]).splitlines()[-1] == ASK


def test_the_question_stays_when_the_warnings_are_cut_from_the_block(tmp_path):
    """The block shows SHOWN_WARNINGS warnings at most; the question does not depend on the warning being among them."""
    from .test_services import e5_blueprint

    many = [bp_mod.Issue("warning", f"x{i}", f"warning number {i}", "deliverable-format") for i in range(6)]
    tight = bp_mod.Issue("warning", "needs.budget_runs", "tight", "budget-tight")
    block = bp_mod.plan_for_user(e5_blueprint(tmp_path), [*many, tight], allowed_roots=[tmp_path])
    assert "... and 2 more (see the details)" in block and "tight" not in block
    assert block.splitlines()[-1] == ASK
