# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.orgmcp.core import ROOT


def test_a_huge_message_in_an_inbox_is_cut_in_the_prompt_with_the_path_to_read_it(org):
    org.send(ROOT, "ceo", "BEGIN " + "x" * 3_000_000 + " END")  # root (the human) is not capped
    batch = org.messages("ceo", "inbox")
    prompt = org.run_prompt("ceo", batch)
    assert len(prompt) < 40_000 and "BEGIN" in prompt and "END" not in prompt
    assert f'read(path="ceo/inbox/{batch[0].id}.md")' in prompt
    org.begin_run("ceo")  # the pointer stays right while the message is being handled
    assert f"ceo/inflight/{batch[0].id}.md" in org.run_prompt("ceo", org.messages("ceo", "inflight"))
    assert "cut" not in batch[0].render(limit=0) and batch[0].render(limit=0).endswith(" END\n")
