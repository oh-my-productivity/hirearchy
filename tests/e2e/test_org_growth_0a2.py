# mypy: ignore-errors
"""Phase 0a.2, end to end: E4's and E3's recorded sessions replayed against the new refusals, read from the raw evidence files.

No scheduler, no LLM, no network: each test builds its own organization in its own ``tmp_path`` with the stream's contract v1 and playbook v1 (the
deliverable path points into ``tmp_path``), then makes the calls the recorded assistant made, with the arguments it made them with, through root's and
the lead's in-process MCP servers (``testkit.e4_replay`` reads the evidence; the lead's reports are the recorded results, played by ``scripted_report``).
A missing evidence file, an absent call number or an unbound id FAILS the test (design 10, DR-42).

This module holds the replays of the answer path and the gate (plan commit 14): s1r T5, s1r v3/v4, s1r's playbook v2 and E3 T5; from plan commit 24,
s1r T8: the artifact path is withheld while the client's question is open, and the file the assistant edited is named (P3, partial); and, from plan
commit 28, the s2r chain and the s3 flow (P1, P2 and P4 together: the relayed rework changed what the user judged, so the human rework needs a base).
"""

import json
from dataclasses import dataclass, field

import pytest
from testkit.e2e_world import build_server
from testkit.e4_replay import EV, EV3, ReplayIds, delegation, evidence, lena_line, scripted_report, tool_call
from testkit.services_world import call, contract_meta, fails, playbook_meta

from hirearchy.core import ROOT, Org
from hirearchy.kernel import strip_markers
from hirearchy.services import changed_lines

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


def offered(w, v1_body: str, v2_body: str, evidence_ids: list[str], service: str = SERVICE) -> dict[str, str]:
    """E4's whole-text v2 as the items it would be offered as now (design 5.4): every line it adds or changes, without its list marker, as one
    ``add`` of a step citing ``evidence_ids``. Returns ``{the line: the refusal text}``; a line that is admitted fails the test (no E4 line is the
    criterion's own words)."""
    refusals: dict[str, str] = {}
    for line in changed_lines(v1_body, v2_body):
        words = strip_markers(line).strip()
        refusals[line] = fails(w.lead, "revise_playbook", service=service, op="add", kind="step", text=words, reason="E4's v2", evidence=evidence_ids)
    return refusals


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
    unrated = f"refused: 1 delivered request(s) of `{SERVICE}` have no verdict yet: {task}. Record a verdict on each with feedback first: "
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
    refusals = offered(w, v1[1], v2[1], cited)
    assert len(refusals) == 3  # the three lines of E4's v2 that P1 refused: none is left out
    for line in ("**C9 – Relative deadlines**:", "**C8 – Structure**:", "**Calendar arithmetic**:"):
        assert any(line in changed and strip_markers(changed).strip()[:150] in refused for changed, refused in refusals.items()), line
    # DR-42: R1 is about (C8, C9), so citing it brings C8 into the subjects; none of the three lines is either criterion's own words (PB-C-WORDS)
    for refused in refusals.values():
        assert "refused: C8, C9 are confirmed by the client, so an item citing them may be only their own words: this item is not." in refused
        assert 'to add C8.' in refused and 'to add C9.' in refused
    for c in (c for c in w.org.runtime.service_catalog.criteria("lead", SERVICE) if c.id in ("C8", "C9")):  # one sentence per id, in id order
        sentence = (
            f'Write it as a step with text "{c.text}" (or a rule with then "{c.text}" and no when) to add {c.id}.' if len(c.text) <= 300
            else f"Write it as a step whose text is {c.id}'s words exactly as `services` lists them (or a rule with those words as then and no when) to add {c.id}."
        )
        assert all(sentence in refused for refused in refusals.values()), c.id
    assert playbook_meta(w.org, "lead", SERVICE)[0]["version"] == 1
    c9 = next(c.text for c in w.org.runtime.service_catalog.criteria("lead", SERVICE) if c.id == "C9")
    none_yet = "none yet: add them from lessons and feedback"
    assert none_yet in v1[1]
    placeholder = next(i.id for i in w.org.runtime.service_catalog.read_playbook("lead", SERVICE).items or () if i.text.startswith(none_yet))
    reply = call(w.lead, "revise_playbook", service=SERVICE, op="edit", item=placeholder, text=c9, reason="C9 confirmed by the client", evidence=["C9"])
    assert "now v2" in reply  # the one line replaced by the criterion's own words
    meta, body = playbook_meta(w.org, "lead", SERVICE)
    assert meta["version"] == 2 and meta["admitted"] == "c" and f"[{placeholder}] {c9}" in body
    note = next(m.body for m in w.org.received(ROOT) if "admitted:" in m.body)
    assert "cites C9, which root added to the contract (v2) and the client confirmed" in note and c9[:40] not in note  # ids only for the human client (D12)


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


# ------------------------------------------------------------------------------------------------------------------------ s1r T8


MEMO_2_V1 = "s1r/memos/versions/memo-2026-10-12.v1.dfce3a4.md"
FLAG = "1 question for the client: ask the user before you copy or deliver"
E3_3286 = "20261022T222238418574-root-3286"  # s3: the rework that came back blocked, with a question (result 96e9)


def memo_2_delivered(tmp_path):
    """s1r: memo 2 (``114d``) is requested and delivered as E4's result ``fa63``: done, with a question for the client; the user has not answered."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    w = s1r_world(tmp_path)
    task = w.request(E_114D, inputs={"notes_file": "2026-10-12.md"}, title=evidence("s1r/msgs/sent/" + E_114D + ".md")[0]["title"])
    scripted_report(w.org, task, RESULT_FA63, {MEMO_2: raw(MEMO_2_V1), REVIEW_2: raw("s1r/org-files/lead-checker-work-review-memo-2026-10-12.md")})
    return w, task


def assistant_edits_the_copy(tmp_path):
    """E4's call #40 (``deliverables-log.txt``): ``sed`` copies the memo to the deliverable folder with one word changed, the question still open."""
    text = raw(MEMO_2_V1)
    old, new = "and implemented a deploy freeze", "and decided on a deploy freeze"
    assert old in text
    (tmp_path / "deliverables").mkdir(exist_ok=True)
    (tmp_path / "deliverables" / "memo-2026-10-12.md").write_text(text.replace(old, new), encoding="utf-8")


def test_s1r_t8_the_artifact_path_is_withheld_while_the_question_is_open(tmp_path):
    """E4's calls #36 to #40. D-E7-2 C (DR-0a5-1): the assistant's own (relayed) accept settles neither the flag nor the withheld finding; the user's does."""
    w, task = memo_2_delivered(tmp_path)
    shown = call(w.root, "progress", task_id=task)  # E4's call #36: it flagged the question and still gave the path
    assert "artifacts withheld (ask first)" in shown and FLAG in shown and MEMO_2 not in shown
    assert MEMO_2 in call(w.root, "inbox")  # the path stays in the result body: the partial form adds no deliver tool
    assistant_edits_the_copy(tmp_path)  # call #40, with the question still open
    withheld = f'"memo-2026-10-12.md": differs from the team\'s checked version (task {task}; path withheld: ask first)'
    for tool, args in (("progress", {"task_id": task}), ("status", {}), ("whoami", {})):
        out = call(w.root, tool, **args)
        assert withheld in out and MEMO_2 not in out, tool  # root is told, in all three, and the path is in none of them
    listed = call(w.root, "progress", task_id=task)
    assert listed.index("Deliverable folder") > listed.index(f"(task {task})")  # the note follows the task line
    call(w.root, "feedback", task_id=task, verdict="accept")  # the assistant's own accept (relayed): since D-E7-2 C it settles nothing
    shown = call(w.root, "progress", task_id=task)
    assert "artifacts withheld (ask first)" in shown and FLAG in shown and MEMO_2 not in shown  # the flag stays ...
    assert withheld in shown  # ... and so does the withheld finding
    call(w.root, "feedback", task_id=task, verdict="accept", source="human")  # the user's own verdict settles both
    shown = call(w.root, "progress", task_id=task)
    assert f"artifacts: {MEMO_2}," in shown and "withheld" not in shown and FLAG not in shown
    for tool, args in (("progress", {"task_id": task}), ("status", {}), ("whoami", {})):
        assert "Deliverable" not in call(w.root, tool, **args), tool


def test_s1r_t8_a_human_rework_answers_the_question_and_the_path_returns(tmp_path):
    w, task = memo_2_delivered(tmp_path / "second")
    assistant_edits_the_copy(tmp_path / "second")
    assert "artifacts withheld (ask first)" in call(w.root, "progress", task_id=task)
    call(w.root, "request", service=SERVICE, inputs={"notes_file": "2026-10-12.md"}, revises=task, source="human")  # instead of a verdict
    shown = call(w.root, "progress", task_id=task)
    assert f"artifacts: {MEMO_2}," in shown and "withheld" not in shown and FLAG not in shown


def test_s3_a_blocked_result_with_a_question_is_flagged(tmp_path):
    (tmp_path / "three").mkdir()
    w = build(tmp_path / "three", "s3/service/history--SERVICE.v1.md", "s3/playbook/PLAYBOOK.f6d34a7.md", ("reviewer", "writer"))
    title = evidence("s3/msgs/sent/" + E3_3286 + ".md")[0]["title"]
    task = w.request(E3_3286, inputs={"notes_file": "2026-10-19.md"}, title=title)
    scripted_report(w.org, task, "s3/msgs/read/20261022T222916707473-lead-96e9.md", {"lead/writer/work/memo-2026-10-19.md": raw("s3/memos/versions/memo-2026-10-19.v2.5e4a099.md")})
    shown = call(w.root, "progress", task_id=task)
    assert ": blocked" in shown and FLAG in shown  # E4's s3 result 96e9: blocked on one ambiguous item, and progress used to say nothing of it
    assert "artifacts" not in shown


# ------------------------------------------------------------------------------------------------------------------------ s2r and s3: the base


def lead_delegates(w: World, bound_to: str, task_file: str, to: str = "lead/writer", **over) -> str:
    """The lead's ``delegate`` as the recorded lead made it (title, goal, acceptance, budget and the task it revises, in the ids of the replay); the id of
    the task is bound to the recorded one. ``over`` replaces arguments (``revises=None`` for a task that revised an earlier one the replay skips)."""
    args = {**delegation(task_file), **over}
    if args.get("revises"):
        args["revises"] = w.ids.of(args["revises"])
    w.org.begin_run("lead")
    call(w.lead, "delegate", to=to, **{k: v for k, v in args.items() if v is not None})
    w.org.end_run("lead", ok=True)
    task = max(m.id for m in w.org.sent("lead") if m.type == "task" and m.to == to)
    w.ids.bind(bound_to, task)
    return task


def writer_task(w: World, task: str):
    return w.org.find_received("lead/writer", task)


S2R = EV / "s2r"
S2R_SERVICE = "s2r/service/history--SERVICE.v1.md"
S2R_MEMO = "lead/writer/work/2026-10-05-memo.md"
S2R_V2, S2R_V3 = "s2r/memos/versions/2026-10-05-memo.v2.0aa3d3b.md", "s2r/memos/versions/2026-10-05-memo.v3.d8fd320.md"
S2R_SENT, S2R_READ, S2R_LEAD, S2R_WRITER = "s2r/msgs/sent/", "s2r/msgs/read/", "s2r/msgs/lead-sent/", "s2r/msgs/lead-writer-sent/"
E2 = {
    "f230": "20261022T205531258713-root-f230", "43b8": "20261022T211157827631-root-43b8", "a9fd": "20261022T212045243968-root-a9fd",
    "342a": "20261022T212050615269-root-342a", "7124": "20261022T210338775220-lead-7124", "608b": "20261022T211355821063-lead-608b",
    "0e90": "20261022T212415721677-lead-0e90",
}


def s2r_judged(tmp_path):
    """s2r up to the delivery the user judged: the request ``f230`` is delivered as E4's result ``5314`` (the memo with Marta's ``2026-10-14``); the user has
    not rated it. Returns the world, the request and the judged result."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    w = build(tmp_path, S2R_SERVICE, "s2r/playbook/PLAYBOOK.2b6438a.md", ("writer", "reviewer"))
    f230 = w.request(E2["f230"], inputs={"notes_file": "2026-10-05.md"}, title="Memo for 2026-10-05 meeting")
    t7124 = lead_delegates(w, E2["7124"], S2R_LEAD + "20261022T210338775220-lead-7124.md", revises=None)
    scripted_report(w.org, t7124, S2R_WRITER + "20261022T210453926371-lead.writer-646c.md", {S2R_MEMO: raw(S2R_V2)})
    judged = scripted_report(w.org, f230, S2R_READ + "20261022T210839231571-lead-5314.md", {})
    return w, f230, judged


def s2r_relayed_rework(w: World) -> str:
    """The injected rework ``43b8`` (relayed: root's own reading), worked as the recorded lead worked it: the memo now has Marta's ``none`` (E4's ``c3dd``)."""
    injected = json.loads((S2R / "injection" / "request-args.json").read_text(encoding="utf-8"))
    injected["revises"] = w.ids.of(injected["revises"])
    t43b8 = w.request(E2["43b8"], **injected)
    t608b = lead_delegates(w, E2["608b"], S2R_LEAD + "20261022T211355821063-lead-608b.md")
    assert writer_task(w, t608b).source == "relayed"  # (1) the writer's rework of a relayed rework is relayed
    scripted_report(w.org, t608b, S2R_WRITER + "20261022T211525485549-lead.writer-d9ba.md", {S2R_MEMO: raw(S2R_V3)})
    scripted_report(w.org, t43b8, S2R_READ + "20261022T211944433751-lead-c3dd.md", {})
    return t43b8


def test_s2r_the_wrong_rule_is_refused_and_the_human_rework_needs_a_base(tmp_path):
    w, f230, judged = s2r_judged(tmp_path / "judged")
    t43b8 = s2r_relayed_rework(w)
    reject = tool_call(S2R, 27)  # the user's rejection of the judged delivery, as call #27 recorded it ...
    reply = call(w.root, "feedback", **{**reject, "task_id": w.ids.of(reject["task_id"]), "criterion": ["C3"]})  # ... with the reading 0a.2 asks for (2a)
    a9fd = w.last_verdict()
    w.ids.bind(E2["a9fd"], a9fd)
    assert 'in these words: "About C3: add "<the rule, in their words>" as a lasting rule? Yes or no."' in reply
    assert f'answers="{a9fd}", about="C3"' in reply
    plain, plain_f230, _ = s2r_judged(tmp_path / "without-a-reading")
    unread = call(plain.root, "feedback", **{**reject, "task_id": plain_f230})  # E4's assistant passed no reading: the reply still gives the question's id
    assert "About " in unread and ": add" in unread and "Next time, pass your reading as criterion on the rejection" in unread
    assert "is one of" not in unread and "C1, C2, C3" in unread  # it lists the current ids and names no C<k> as the reading
    # (3) the rework the user asked for, as call #28 made it: the relayed rework changed the memo after the delivery they judged
    asked = {**tool_call(S2R, 28), "revises": w.ids.of(E2["f230"])}
    sent = len(w.org.sent(ROOT))
    refusal = fails(w.root, "request", **asked)
    assert f"refused: since the delivery the client judged (task {f230}, result {judged.id}), relayed rework {t43b8} " in refusal
    assert f"changed {S2R_MEMO}. Say which version the user's corrections apply to" in refusal and "Nothing was sent." in refusal
    assert 'base="delivered"' in refusal and len(w.org.sent(ROOT)) == sent
    # (4) base="delivered": the task carries the version the user judged
    reply = call(w.root, "request", **asked, base="delivered")
    t342a = w.last_task()
    w.ids.bind(E2["342a"], t342a)
    assert "base delivered: the lead starts from the version the user judged." in reply
    body = w.org.find_received("lead", t342a).body
    commit = w.org.runtime.org_history.first_commit_with(f"lead/sent/{judged.id}.md")
    assert commit and f"org-git commit {commit[:12]}" in body and "## Base: the version the client judged" in body
    judged_text = body[body.index("### " + S2R_MEMO):]
    assert "| Marta |" in judged_text and "| 2026-10-14 |" in judged_text and "Open questions" not in judged_text  # Marta's date survives
    assert w.org.find_received("lead", t342a).source == "human" and body.rstrip().endswith("```")
    t0e90 = lead_delegates(w, E2["0e90"], S2R_LEAD + "20261022T212415721677-lead-0e90.md")
    assert writer_task(w, t0e90).source == "human"  # the writer's rework for it is the user's
    # (2) what the scheduler puts in the lead's prompt for the batch [a9fd, 342a]: the lesson of the relayed rework is marked
    batch = [w.org.find_received("lead", a9fd), w.org.find_received("lead", t342a)]
    assert all(batch)
    sections = w.org.runtime.service_prompt_sections.prompt_sections("lead", batch)
    assert 'owner\'s view (from a relayed rework, not the client\'s): "Rework needed' in sections
    # (5) the user's yes, recorded with the answer
    c31 = tool_call(S2R, 31)
    assert "Recorded as the user's answer to R1" in call(w.root, "define_service", **c31, answers=a9fd, about="C3", words="Yes, add it.")
    (link,) = [m for m in w.org.sent(ROOT) if m.reply_to == a9fd and m.criterion]
    assert (link.criterion, link.source) == ("C9", "human") and contract_meta(w.org, "lead", w.service)[0]["version"] == 2
    # (6) E4's playbook v2 rested on the wrong rule: it is refused line by line
    v2, v1 = evidence("s2r/playbook/PLAYBOOK.6b06123.md"), evidence("s2r/playbook/PLAYBOOK.2b6438a.md")
    refusals = offered(w, v1[1], v2[1], ["R1", "C9"], service=w.service)
    assert refusals and all("so an item citing it may be only its own words: this item is not." in r for r in refusals.values())  # PB-C-WORDS
    for words in ("Flag any vague deadline as `none`", "Vague deadlines:"):
        assert any(words in line and strip_markers(line).strip()[:150] in refused for line, refused in refusals.items()), words  # the wrong rule is refused
    assert playbook_meta(w.org, "lead", w.service)[0]["version"] == 1
    # (7) the criterion's own words, as one line with its id, are admitted
    c9 = next(c.text for c in w.org.runtime.service_catalog.criteria("lead", w.service) if c.id == "C9")
    none_yet = "none yet: add them from lessons and feedback"
    placeholder = next(i.id for i in w.org.runtime.service_catalog.read_playbook("lead", w.service).items or () if i.text.startswith(none_yet))
    assert "now v2" in call(w.lead, "revise_playbook", service=w.service, op="edit", item=placeholder, text=c9, reason="C9 confirmed", evidence=["C9"])
    meta, _ = playbook_meta(w.org, "lead", w.service)
    assert meta["version"] == 2 and meta["admitted"] == "c"
    note = next(m.body for m in w.org.received(ROOT) if "admitted:" in m.body)
    assert "cites C9, which root added to the contract" in note and c9[:40] not in note


S3 = EV / "s3"
S3_MEMO = "lead/writer/work/memo-2026-10-05.md"
S3_LEAD, S3_WRITER, S3_READ = "s3/msgs/lead-sent/", "s3/msgs/lead-writer-sent/", "s3/msgs/read/"
E3 = {
    "88b2": "20261022T214057425390-root-88b2", "4510": "20261022T214612649634-root-4510", "fe20": "20261022T215128895860-root-fe20",
    "ac19": "20261022T215730383010-root-ac19", "ff36": "20261022T215730424416-root-ff36", "da7e": "20261022T214139482031-lead-da7e",
    "0ebf": "20261022T214714927747-lead-0ebf", "5559": "20261022T215309118322-lead-5559", "1fb7": "20261022T215837117856-root-1fb7",
}


def test_s3_the_answered_amendment_is_admitted_and_only_its_words_enter_the_playbook(tmp_path):
    w = build(tmp_path, "s3/service/history--SERVICE.v1.md", "s3/playbook/PLAYBOOK.f6d34a7.md", ("reviewer", "writer"))
    r88b2 = w.request(E3["88b2"], inputs={"notes_file": "2026-10-05.md"}, title="Memo for 2026-10-05 meeting")
    tda7e = lead_delegates(w, E3["da7e"], S3_LEAD + "20261022T214139482031-lead-da7e.md")
    scripted_report(w.org, tda7e, S3_WRITER + "20261022T214218308119-lead.writer-5d79.md", {S3_MEMO: raw("s3/memos/versions/memo-2026-10-05.v1.4884355.md")})
    scripted_report(w.org, r88b2, S3_READ + "20261022T214508787095-lead-de22.md", {})
    c23 = tool_call(S3, 23)  # the user's rework (call #23): the dates he wants
    t4510 = w.request(E3["4510"], **{**c23, "revises": w.ids.of(c23["revises"])})
    t0ebf = lead_delegates(w, E3["0ebf"], S3_LEAD + "20261022T214714927747-lead-0ebf.md")
    assert writer_task(w, t0ebf).source == "human"
    scripted_report(w.org, t0ebf, S3_WRITER + "20261022T214743679928-lead.writer-2ac3.md", {S3_MEMO: raw("s3/memos/versions/memo-2026-10-05.v2.a526bb3.md")})
    judged = scripted_report(w.org, t4510, S3_READ + "20261022T214955106608-lead-ffba.md", {})
    injected = json.loads((S3 / "injection" / "request-args.json").read_text(encoding="utf-8"))  # E4's relayed rework (fe20)
    injected["revises"] = w.ids.of(injected["revises"])
    tfe20 = w.request(E3["fe20"], **injected)
    t5559 = lead_delegates(w, E3["5559"], S3_LEAD + "20261022T215309118322-lead-5559.md")
    assert writer_task(w, t5559).source == "relayed"
    scripted_report(w.org, t5559, S3_WRITER + "20261022T215346200018-lead.writer-7d10.md", {S3_MEMO: raw("s3/memos/versions/memo-2026-10-05.v3.b7f83c8.md")})
    scripted_report(w.org, tfe20, S3_READ + "20261022T215618947365-lead-40d8.md", {})
    c30 = tool_call(S3, 30)  # the rejection (call #30), with the reading E4's assistant did not give
    reply = call(w.root, "feedback", **{**c30, "task_id": w.ids.of(c30["task_id"]), "criterion": ["C3"]})
    ac19 = w.last_verdict()
    w.ids.bind(E3["ac19"], ac19)
    assert "About C3: add" in reply
    c31 = {**tool_call(S3, 31), "revises": w.ids.of(tool_call(S3, 31)["revises"])}  # the human rework after the injected one changed the memo
    refusal = fails(w.root, "request", **c31)
    assert f"relayed rework {tfe20} " in refusal and f"changed {S3_MEMO}." in refusal and f"(task {t4510}, result {judged.id})" in refusal
    assert "Nothing was sent." in refusal
    call(w.root, "request", **c31, base="delivered")
    w.ids.bind(E3["ff36"], w.last_task())
    assert "## Base: the version the client judged" in w.org.find_received("lead", w.last_task()).body
    c37, c38 = tool_call(S3, 37), tool_call(S3, 38)
    assert "Recorded as the user's answer to R1" in call(w.root, "define_service", **c37, answers=ac19, about="C3", words=c38["note"])
    (link,) = [m for m in w.org.sent(ROOT) if m.reply_to == ac19 and m.criterion]
    assert (link.criterion, link.source) == ("C8", "human")
    # the lead's attempt 1: the link note's id is evidence (F-E4-7), and what it rests on is the criterion's own words, nothing else
    v2, v1 = evidence("s3/playbook/PLAYBOOK.dd2d1da.md"), evidence("s3/playbook/PLAYBOOK.f6d34a7.md")
    refusals = offered(w, v1[1], v2[1], ["C8", link.id, r88b2], service=w.service)
    assert refusals and all("unknown evidence" not in r and "so an item citing it may be only its own words: this item is not." in r for r in refusals.values())
    for rider in ("(d) a 'Next meeting' footer", "No other sections", "(C1\u2013C8) and the regression list verbatim", "<checker's task id>"):
        assert any(rider in line for line in refusals), rider  # the line that carries each rider was offered and refused
    assert playbook_meta(w.org, "lead", w.service)[0]["version"] == 1
    c8 = next(c.text for c in w.org.runtime.service_catalog.criteria("lead", w.service) if c.id == "C8")
    none_yet = "none yet: add them from lessons and feedback"
    placeholder = next(i.id for i in w.org.runtime.service_catalog.read_playbook("lead", w.service).items or () if i.text.startswith(none_yet))
    assert "now v2" in call(w.lead, "revise_playbook", service=w.service, op="edit", item=placeholder, text=c8, reason="C8 confirmed", evidence=[link.id])
    meta, _ = playbook_meta(w.org, "lead", w.service)
    assert meta["version"] == 2 and meta["admitted"] == "c"
