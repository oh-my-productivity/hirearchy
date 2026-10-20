# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import re

from testkit.blueprint_world import ex as blueprint_examples

from testkit.blueprint_world import bpm as bp_mod


# --------------------------------------------------------------------------------------------- the plan block
def doc_bp(tmp_path, monkeypatch):
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))
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
