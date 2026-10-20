# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.orgmcp.core import ROOT

ENG = "ceo/eng"


def drain(org, addr, ok=True):
    org.begin_run(addr)
    org.end_run(addr, ok=ok)


# ---------------------------------------------------------------------- prompts
def test_qa17_prompt_shows_acceptance_criteria_of_open_tasks(org):
    task = org.delegate(ROOT, "ceo", "Strict blurb", "the goal", "ACCEPT: exactly 33 words", budget=10)
    drain(org, "ceo")  # the task was handled in an earlier run and now sits in read/
    sub = org.delegate("ceo", ENG, "draft", "g", "a", budget=2)
    result = org.report(ENG, sub.id, "done", "35 words")  # the next run is woken by this result only
    prompt = org.run_prompt("ceo", [org.find_received("ceo", result.id)])
    assert "exactly 33 words" in prompt, f"prompt for the run closing task {task.id} lacks its acceptance criteria"
