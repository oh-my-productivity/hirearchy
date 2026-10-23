# mypy: ignore-errors
"""Phase 0a.2, end to end: E4's and E3's recorded sessions replayed against the new refusals, read from the raw evidence files.

No scheduler, no LLM, no network: each test builds its own organization in its own ``tmp_path`` with the stream's contract v1 and playbook v1 (the
deliverable path points into ``tmp_path``), then makes the calls the recorded assistant made, with the arguments it made them with, through root's and
the lead's in-process MCP servers (``testkit.e4_replay`` reads the evidence; the lead's reports are the recorded results, played by ``scripted_report``).
A missing evidence file, an absent call number or an unbound id FAILS the test (design 10, DR-42).

This module holds the replays of the answer path and the gate (plan commit 14): s1r T5, s1r v3/v4, s1r's playbook v2 and E3 T5.
"""

from dataclasses import dataclass, field

import pytest
from testkit.e2e_world import build_server
from testkit.e4_replay import EV, EV3, ReplayIds, evidence, lena_line, scripted_report, tool_call
from testkit.services_world import call, contract_meta, fails, playbook_meta

from hirearchy.core import ROOT, Org

S1R = EV / "s1r"
SERVICE = "weekly-memo"
E_ED94 = "20261022T182945409755-root-ed94"  # s1r: the first request (the 2026-10-05 memo)
E_3559 = "20261022T190015448581-root-3559"  # s1r: the user's rework of it
E_114D = "20261022T191407596413-root-114d"  # s1r: the second request (the 2026-10-12 memo)
RESULT_4F4D = "s1r/msgs/read/20261022T184536871337-lead-4f4d.md"  # delivered ed94
RESULT_F84E = "s1r/msgs/read/20261022T191112496455-lead-f84e.md"  # delivered 3559 as blocked
RESULT_FA63 = "s1r/msgs/read/20261022T192346320735-lead-fa63.md"  # delivered 114d
MEMO_1 = "lead/writer/work/memo-2026-10-05.md"
MEMO_2 = "lead/writer/work/memo-2026-10-12.md"
REVIEW_2 = "lead/checker/work/review-memo-2026-10-12.md"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


@dataclass
class World:
    org: Org
    root: object  # root's MCP server
    lead: object  # the lead's MCP server
    service: str
    ids: ReplayIds = field(default_factory=ReplayIds)

    def last_task(self) -> str:
        return max(m.id for m in self.org.sent(ROOT) if m.type == "task")

    def last_verdict(self) -> str:
        return max(m.id for m in self.org.sent(ROOT) if m.feedback)

    def request(self, bound_to: str, **args) -> str:
        """root's ``request`` as the evidence made it; the id the replay gives it is bound to the evidence's."""
        call(self.root, "request", **{"service": self.service, **args})
        task = self.last_task()
        self.ids.bind(bound_to, task)
        return task


def raw(path: str) -> str:
    """A file of the evidence, as it is (a saved version of a memo)."""
    return (EV / path).read_text(encoding="utf-8")


def build(tmp_path, contract: str, playbook: str | None, reports: tuple[str, ...]) -> World:
    """root -> lead (-> its reports), the service of the stream defined from its recorded v1 (and playbook v1)."""
    org = Org.init(tmp_path / "org", "Meeting memos")
    org.hire(ROOT, "lead", "Lead", "Lead the memo team.", can_hire=True, max_children=3)
    for kid in reports:
        org.hire("lead", kid, kid.capitalize(), f"Do the {kid}'s part of a memo.")
    meta, _ = evidence(contract)
    body = evidence(playbook)[1].strip() if playbook else None
    org.define_service(
        ROOT, "lead", meta["name"], description=meta["description"], inputs=meta["inputs"], acceptance=meta["acceptance"],
        deliverable={**meta["deliverable"], "path": str(tmp_path / "deliverables")}, budget=meta["budget"], playbook=body,
    )
    return World(org, build_server(org, ROOT), build_server(org, "lead"), meta["name"])


def s1r_world(tmp_path) -> World:
    return build(tmp_path, "s1r/service/history--SERVICE.v1.md", "s1r/playbook/PLAYBOOK.4435fd0.md", ("reader", "writer", "checker"))


def first_delivery(w: World) -> str:
    """s1r: the 2026-10-05 memo is requested and delivered (E4's result ``4f4d``); the user has not rated it."""
    task = w.request(E_ED94, inputs={"notes_file": "2026-10-05.md"}, title=evidence("s1r/msgs/sent/" + E_ED94 + ".md")[0]["title"])
    scripted_report(w.org, task, RESULT_4F4D, {MEMO_1: raw("s1r/memos/versions/memo-2026-10-05.v2.a358b76.md")})
    return task


def rejection_t5(w: World, task: str) -> tuple[str, str]:
    """call #22 as the assistant made it (it named C5 as its reading); returns the reply and the id of the rejection."""
    args = tool_call(S1R, 22)
    reply = call(w.root, "feedback", **{**args, "task_id": w.ids.of(args["task_id"])})
    return reply, w.last_verdict()


def state(w: World) -> tuple[int, int]:
    """What a refusal leaves as it was: the contract version and the number of messages root sent."""
    return contract_meta(w.org, "lead", w.service)[0]["version"], len(w.org.sent(ROOT))


def compliant_t5(w: World, task: str, n22: str) -> None:
    """The path the 0a.2 flow leaves: call #21 with the user's yes (Lena's answer, #23's note) as the answer to rejection #22."""
    c21, c23 = tool_call(S1R, 21), tool_call(S1R, 23)
    reply = call(w.root, "define_service", **c21, answers=n22, about="C5", words=c23["note"])
    assert "Recorded as the user's answer to R1" in reply and "C8, C9 are client-confirmed" in reply


# ------------------------------------------------------------------------------------------------------------------------ s1r T5


def test_s1r_t5_an_amendment_before_the_verdict_is_refused(tmp_path):
    w = s1r_world(tmp_path)
    task = first_delivery(w)
    t5, c21 = lena_line(S1R, 5), tool_call(S1R, 21)  # Lena's turn 5, and the amendment the assistant made 0.46 s before the rejection
    unrated = f"refused: 1 delivered request(s) of `{SERVICE}` have no verdict yet: {task}. Record the user's verdict on each with feedback first, "
    before = state(w)
    for given in ({}, {"words": t5}):  # the verdicts come first, with or without her words
        assert unrated in fails(w.root, "define_service", **c21, **given)
    assert state(w) == before
    reply, n22 = rejection_t5(w, task)  # #22: the rejection, with the assistant's reading C5
    assert 'ask the user exactly ONE yes/no question, in these words: "About C5: add "<the rule, in their words>" as a lasting rule? Yes or no."' in reply
    assert f'answers="{n22}", about="C5"' in reply
    before = state(w)
    assert f"refused: rejection R1 (message {n22}) on task {task} has no answer yet" in fails(w.root, "define_service", **c21, words=t5)
    assert "words (CLI: --words) repeats rejection R1's own note" in fails(w.root, "define_service", **c21, answers=n22, about="C5", words=t5)
    assert state(w) == before and contract_meta(w.org, "lead", SERVICE)[0]["version"] == 1  # still v1 after each
    compliant_t5(w, task, n22)  # the compliant path: the user's answer to the question, as #23 recorded it
    meta = contract_meta(w.org, "lead", SERVICE)[0]
    assert meta["version"] == 2 and meta["answers"] == n22 and meta["about"] == "C5"
    (link,) = [m for m in w.org.sent(ROOT) if m.reply_to == n22 and m.criterion]
    assert (link.criterion, link.source) == ("C8, C9", "human")
    listing = call(w.root, "services")
    assert "    C8: The memo's very first line" in listing and "    C9: Every Due value is an ISO date" in listing
    assert "(amendment, not confirmed)" not in listing  # neither C8 nor C9 is marked: the product wrote the user's yes


# ------------------------------------------------------------------------------------------------------------------------ s1r v3/v4


def test_s1r_v3_and_v4_without_a_verdict_are_refused(tmp_path):
    w = s1r_world(tmp_path)
    task = first_delivery(w)
    _, n22 = rejection_t5(w, task)
    compliant_t5(w, task, n22)
    args24 = tool_call(S1R, 24)  # the user's rework of memo 1 (call #24) ...
    rework = w.request(E_3559, **{**args24, "revises": w.ids.of(args24["revises"])})
    scripted_report(w.org, rework, RESULT_F84E, {MEMO_1: raw("s1r/memos/versions/memo-2026-10-05.v3.07427d8.md")})  # ... came back blocked: no delivery to rate
    memo_2 = w.request(E_114D, inputs={"notes_file": "2026-10-12.md"}, title=evidence("s1r/msgs/sent/" + E_114D + ".md")[0]["title"])
    scripted_report(w.org, memo_2, RESULT_FA63, {MEMO_2: raw("s1r/memos/versions/memo-2026-10-12.v1.dfce3a4.md"), REVIEW_2: "criteria met: 7 of 7\n"})
    c44, c45 = tool_call(S1R, 44), tool_call(S1R, 45)  # the amendments the assistant made with memo 2 delivered and unrated
    unrated = f"refused: 1 delivered request(s) of `{SERVICE}` have no verdict yet: {memo_2}. "  # only memo 2: the blocked case has no delivery
    before = state(w)
    assert unrated in fails(w.root, "define_service", **c44, words="Yes, add it.")
    assert unrated in fails(w.root, "define_service", **c45, answers=n22, about="C9", words="Yes, add it.")
    assert state(w) == before
    n9 = call(w.root, "feedback", task_id=memo_2, verdict="reject", note=lena_line(S1R, 9), source="human")  # Lena's turn 9: memo 2 rejected
    n9 = w.last_verdict()
    before = state(w)
    assert f"refused: rejection R1 (message {n22}) already has its answer (contract v2)" in fails(
        w.root, "define_service", **c45, answers=n22, about="C9", words="Yes, add it.",
    )
    assert f"refused: rejection R2 (message {n9}) on task {memo_2} has no answer yet" in fails(w.root, "define_service", **c44, words="Yes, add it.")
    assert state(w) == before and contract_meta(w.org, "lead", SERVICE)[0]["version"] == 2  # v2 stays, with C9 current
    assert [c.text[:30] for c in w.org.runtime.service_catalog.criteria("lead", SERVICE) if c.id == "C9" and c.current] == ["Every Due value is an ISO date"]


# ------------------------------------------------------------------------------------------------------------------------ s1r playbook v2


def test_s1r_playbook_v2_of_e4_is_refused_line_by_line(tmp_path):
    w = s1r_world(tmp_path)
    task = first_delivery(w)
    _, n22 = rejection_t5(w, task)
    compliant_t5(w, task, n22)  # the end state of the first replay: C8 and C9 are the user's, confirmed by the product's link
    v2, v1 = evidence("s1r/playbook/PLAYBOOK.e9bd92f.md"), evidence("s1r/playbook/PLAYBOOK.4435fd0.md")
    cited = w.ids.map(v2[0]["evidence"])  # [C9, R1, the case ed94] in the ids of the replay
    refused = fails(w.lead, "revise_playbook", service=SERVICE, content=v2[1], reason=v2[0]["reason"], evidence=cited)
    assert "refused: every line a revision adds or changes must rest on the evidence it cites, and 3 line(s) do not:" in refused
    for line in ("**C9 – Relative deadlines**:", "**C8 – Structure**:", "**Calendar arithmetic**:"):
        assert f'- "- {line}' in refused or f'- "{line}' in refused
    assert "- and " not in refused  # three lines: none is left out
    # DR-42: R1 is about (C8, C9), so citing it brings C8 into the subjects; none of the three lines is either criterion's own words
    assert "these lines are not C8's or C9's words" in refused
    assert 'Write it as "- C8: The memo\'s very first line' in refused and 'Write it as "- C9: Every Due value is an ISO date' in refused
    assert playbook_meta(w.org, "lead", SERVICE)[0]["version"] == 1
    c9 = next(c.text for c in w.org.runtime.service_catalog.criteria("lead", SERVICE) if c.id == "C9")
    none_yet = "none yet: add them from lessons and feedback"
    assert none_yet in v1[1]
    admitted = v1[1].replace(none_yet, f"- C9: {c9}").strip()  # v1 with the one line replaced by the criterion's own words
    assert "now v2" in call(w.lead, "revise_playbook", service=SERVICE, content=admitted, reason="C9 confirmed by the client", evidence=["C9"])
    meta, body = playbook_meta(w.org, "lead", SERVICE)
    assert meta["version"] == 2 and meta["admitted"] == "c" and f"- C9: {c9}" in body
    note = next(m.body for m in w.org.received(ROOT) if "admitted:" in m.body)
    assert f"[C9] - C9: {c9[:40]}" in note


# ------------------------------------------------------------------------------------------------------------------------ E3 T5


def test_e3_turn_5_an_amendment_in_the_reject_turn_is_refused(tmp_path):
    w = build(tmp_path, "service/SERVICE.v1.md", None, ("writer", "reviewer"))
    first = w.request("20261021T152347923195-root-dd87", inputs={"notes_file": "2026-10-05.md"}, title="Memo for the meeting of 2026-10-05")
    scripted_report(w.org, first, "msgs/read/20261021T152601669347-lead-be1b.md", {MEMO_1: "Decisions\nAction items\nNext meeting\n"})
    t5, c24, c25 = lena_line(EV3, 5), tool_call(EV3, 24), tool_call(EV3, 25)  # Lena's turn 5; the rejection with criterion [C6, C3]; the amendment 2 s later
    reply = call(w.root, "feedback", **{**c24, "task_id": w.ids.of(c24["task_id"])})
    n24 = w.last_verdict()
    assert 'in these words: "About C6: add "<the rule, in their words>" as a lasting rule? Yes or no."' in reply  # root's reading is the first id of its criterion
    before = state(w)
    assert "records the user's words" in fails(w.root, "define_service", **c25)  # P2-NEEDS-WORDS
    assert f"refused: rejection R1 (message {n24}) on task {first} has no answer yet" in fails(w.root, "define_service", **c25, words=t5)
    assert "words (CLI: --words) repeats rejection R1's own note" in fails(w.root, "define_service", **c25, answers=n24, about="C6", words=t5)
    assert state(w) == before and contract_meta(w.org, "lead", "weekly-meeting-memo")[0]["version"] == 1
