"""Tests of rederive_quality.py: the independent re-derivation of ``hirearchy quality --json`` from one stream's copied raw files.

Unit tests build small synthetic streams (E7's layout) in pytest's tmp_path and read the re-derived JSON through the public entry point. The E7
integration tests read E7's committed evidence read-only (E7EV) and write only to tmp_path. Nothing here imports hirearchy product code."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
sys.dont_write_bytecode = True

import rederive_quality as rq  # noqa: E402

E7EV = Path("/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence")
SCRIPT = HARNESS / "rederive_quality.py"
EXPECTED = HARNESS / "selfcheck" / "e7-expected-rederive.json"
PY = sys.executable
HAVE_E7 = (E7EV / "s1" / "msgs" / "sent").is_dir()
e7 = pytest.mark.skipif(not HAVE_E7, reason="E7 evidence not available")

FEEDBACK_HEADER = (
    "Client feedback for reflection only: it does not change this task's acceptance criteria or outcome; "
    "report `done` only if every criterion is met."
)
SVC = "svc"
DELIV = "/tmp/hirearchy-test/deliverables"


def run(*args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([PY, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=env)


# ------------------------------------------------------------------------------------------------ a synthetic stream (E7's layout)


def mid(clock: str, sender: str, tag: str) -> str:
    """A message id: ``clock`` is ``HHMMSS`` on 2026-10-25, micro 0; the sender's ``/`` becomes ``.`` as in the product."""
    return f"20261025T{clock}000000-{sender.replace('/', '.')}-{tag}"


def stem(clock: str, micro: str = "500000") -> str:
    return f"20261025T{clock}{micro}"


def _scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def front(meta: dict) -> str:
    out = ["---"]
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, list):
            out.append(f"{k}:")
            out += [f"- {_scalar(x)}" for x in v]
        elif isinstance(v, dict):
            out.append(f"{k}:")
            out += [f"  {kk}: {_scalar(vv)}" for kk, vv in v.items()]
        else:
            out.append(f"{k}: {_scalar(v)}")
    out.append("---")
    return "\n".join(out) + "\n"


class Stream:
    """Writes a stream evidence dir: msgs boxes, run logs, service and playbook versions, memos and their versions."""

    def __init__(self, root: Path):
        self.root = root
        (root / "msgs").mkdir(parents=True)
        (root / "run-logs").mkdir()
        (root / "service").mkdir()
        (root / "playbook").mkdir()
        (root / "memos" / "versions").mkdir(parents=True)
        (root / "org-files").mkdir()
        (root / "memos" / "versions" / "INDEX.txt").write_text("")
        self.index = []

    def _box(self, addr: str, box: str) -> Path:
        name = box if addr == "root" else f"{addr.replace('/', '-')}-{box}"
        d = self.root / "msgs" / name
        d.mkdir(exist_ok=True)
        return d

    def msg(self, id, frm, to, type, body="", title="t", recv_box="read", **meta):
        m = {"id": id, "from": frm, "to": to, "type": type, "title": title, "created": f"2026-10-25T{id[9:11]}:{id[11:13]}:{id[13:15]}+00:00"}
        m.update(meta)
        text = front(m) + "\n" + body + "\n"
        (self._box(frm, "sent") / f"{id}.md").write_text(text)
        (self._box(to, recv_box) / f"{id}.md").write_text(text)
        return id

    def task(self, id, frm, to, budget, **meta):
        return self.msg(id, frm, to, "task", budget=budget, **meta)

    def result(self, id, frm, to, reply_to, status, artifacts=(), budget=0, **meta):
        body = "## Summary\nok\n"
        if artifacts:
            body += "\n## Artifacts\n" + "".join(f"- {a} (10 words)\n" for a in artifacts)
        return self.msg(id, frm, to, "result", body=body, reply_to=reply_to, status=status, budget=budget, **meta)

    def verdict(self, id, reply_to, verdict, words="", source="human", **meta):
        body = FEEDBACK_HEADER + "\n\n" + (words or "accepted")
        return self.msg(id, "root", "lead", "note", body=body, reply_to=reply_to, feedback=verdict, source=source, wake=False, **meta)

    def link(self, id, reply_to, criterion, source="human"):
        return self.msg(id, "root", "lead", "note", body="link", reply_to=reply_to, criterion=criterion, source=source, wake=False)

    def runs(self, addr, *stems):
        d = self.root / "run-logs" / addr.replace("/", "-")
        d.mkdir(exist_ok=True)
        for s in stems:
            (d / f"{s}.log").write_text("log\n")

    def agent(self, addr, created="2026-10-25T06:00:00+00:00"):
        (self.root / "org-files" / f"{addr.replace('/', '-')}-AGENT.md").write_text(front({"name": addr, "created": created}) + "\nbody\n")

    def contract(self, version, acceptance, *, defined, budget=12, current=True, **meta):
        m = {
            "name": SVC, "acceptance": acceptance, "deliverable": {"path": DELIV}, "budget": budget, "version": version, "defined_by": "root",
            "defined": defined, "created": "2026-10-25T07:00:00.000000+00:00",
        }
        m.update(meta)
        text = front(m) + "\n"
        name = "current-SERVICE.md" if current else f"history--SERVICE.v{version}.md"
        (self.root / "service" / name).write_text(text)

    def playbook(self, version, body, *, revised, by, current=True, **meta):
        m = {"service": SVC, "version": version, "revised": revised, "by": by}
        m.update(meta)
        name = "current-PLAYBOOK.md" if current else f"history--PLAYBOOK.v{version}.md"
        (self.root / "playbook" / name).write_text(front(m) + body + "\n")

    def memo_version(self, path, n, sha, when, text):
        import hashlib

        name = Path(path).name
        f = self.root / "memos" / "versions" / f"{name[:-3]}.v{n}.{sha}.md"
        f.write_text(text)
        self.index.append(f"{path} v{n} {sha} {when} md5 {hashlib.md5(text.encode()).hexdigest()}")
        (self.root / "memos" / "versions" / "INDEX.txt").write_text("\n".join(self.index) + "\n")

    def deliverable(self, name, text, mtime: float):
        f = self.root / "memos" / name
        f.write_text(text)
        os.utime(f, (mtime, mtime))


def base(tmp_path) -> Stream:
    """One service ``svc`` of ``lead`` (writer and reviewer below it), contract v1 (C1, C2) with budget 12."""
    s = Stream(tmp_path / "s")
    for a in ("lead", "lead/writer", "lead/reviewer"):
        s.agent(a)
    s.contract(1, ["Alpha criterion.", "Beta criterion."], defined="2026-10-25T07:00:00.000000+00:00")
    return s


def derive(s: Stream) -> dict:
    return rq.rederive(s.root)


def record(s: Stream) -> dict:
    data = derive(s)
    assert len(data["services"]) == 1, data["services"]
    return data["services"][0]


T1 = mid("070100", "root", "t001")


def one_case(s: Stream, *, reject_words="Always put Gamma first.", link=True, rework_budget=5):
    """Head T1 (budget 12) -> writer and reviewer -> blocked, then done (supersedes); human reject with a link naming C3; contract v2 answers it
    with C3; human rework T2 (budget ``rework_budget``) delivered and accepted."""
    s.task(T1, "root", "lead", 12, service=SVC, contract=1, playbook=1)
    s.runs("lead", stem("070101"))
    l1 = s.task(mid("070200", "lead", "l001"), "lead", "lead/writer", 3)
    s.runs("lead/writer", stem("070201"))
    s.result(mid("070300", "lead/writer", "w001"), "lead/writer", "lead", l1, "done", artifacts=["lead/writer/work/memo.md"])
    s.runs("lead", stem("070301"))
    l2 = s.task(mid("070400", "lead", "l002"), "lead", "lead/reviewer", 2)
    s.runs("lead/reviewer", stem("070401"))
    s.result(mid("070500", "lead/reviewer", "v001"), "lead/reviewer", "lead", l2, "done")
    s.runs("lead", stem("070501"))
    blocked = s.result(mid("070600", "lead", "b001"), "lead", "root", T1, "blocked", artifacts=["lead/writer/work/memo.md"])
    done = s.result(mid("070800", "lead", "d001"), "lead", "root", T1, "done", artifacts=["lead/writer/work/memo.md"], supersedes=blocked)
    n1 = s.verdict(mid("070900", "root", "n001"), T1, "reject", reject_words, criterion="C2")
    if link:
        s.link(mid("071000", "root", "k001"), n1, "C3")
        s.contract(1, ["Alpha criterion.", "Beta criterion."], defined="2026-10-25T07:00:00.000000+00:00", current=False)
        s.contract(2, ["Alpha criterion.", "Beta criterion.", "Gamma criterion."], defined="2026-10-25T07:10:30.000000+00:00", answers=n1, about="C2")
    t2 = s.task(mid("071100", "root", "t002"), "root", "lead", rework_budget, service=SVC, contract=2, revises=T1, source="human")
    s.runs("lead", stem("071101"), stem("071201"))
    r2 = s.result(mid("071300", "lead", "d002"), "lead", "root", t2, "done", artifacts=["lead/writer/work/memo.md"])
    a2 = s.verdict(mid("071400", "root", "n002"), t2, "accept")
    return dict(blocked=blocked, done=done, n1=n1, t2=t2, r2=r2, a2=a2)


# ------------------------------------------------------------------------------------------------ parsing


def test_frontmatter_reads_quoted_wrapped_titles_lists_and_nested_maps():
    text = (
        "---\nid: 20261025T071714388062-root-6096\nfrom: root\ntitle: 'criterion link on \"Memo (client answers)\":\n  C9'\n"
        "created: '2026-10-25T07:17:14+00:00'\nhops: 0\nwake: false\nacceptance:\n- Plain item one.\n- 'The reviewer''s report, wrapped\n"
        "  onto a second line.'\ndeliverable:\n  description: One memo, named memo-<date>.md, for\n    example memo-2026-10-05.md.\n"
        "  path: /tmp/x/deliverables\ninputs:\n- name: notes_file\n  required: true\nevidence: []\n---\nThe body.\n"
    )
    meta, body = rq.split_frontmatter(text)
    assert meta["title"] == 'criterion link on "Memo (client answers)": C9'
    assert meta["hops"] == 0 and meta["wake"] is False
    assert meta["acceptance"] == ["Plain item one.", "The reviewer's report, wrapped onto a second line."]
    assert meta["deliverable"]["path"] == "/tmp/x/deliverables"
    assert meta["deliverable"]["description"] == "One memo, named memo-<date>.md, for example memo-2026-10-05.md."
    assert meta["inputs"] == [{"name": "notes_file", "required": True}]
    assert meta["evidence"] == []
    assert body.strip() == "The body."


def test_latest_result_with_supersedes_decides_the_case_state(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    b = s.result(mid("070600", "lead", "b001"), "lead", "root", T1, "blocked")
    s.result(mid("070800", "lead", "d001"), "lead", "root", T1, "done", supersedes=b)
    case = record(s)["cases"][0]
    assert case["state"] == "done" and case["tasks"] == 1


# ------------------------------------------------------------------------------------------------ runs, window, cut, credits, top-ups


def test_runs_window_spend_and_user_approved_raised_by_an_explicit_rework(tmp_path):
    s = base(tmp_path)
    one_case(s)
    case = record(s)["cases"][0]
    assert case["runs"] == 7 and case["credited"] == 0 and case["relayed_runs"] == 0
    assert case["spend"] == 7 and case["user_cost"] == 7
    # at T2: 5 runs used, 12 handed down, nothing came back -> committed 12; + 5 -> ceiling 17
    assert case["user_approved"] == 17 and case["budget"] == 12
    assert case["ratio"] == "0.41"
    assert case["top_ups"] == [{"id": mid("071100", "root", "t002"), "source": "human", "amount": 5}]
    assert case["cut"] is False and case["runs_unknown"] == ""


def test_a_later_request_cuts_the_window_and_its_runs_go_to_the_later_case(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.result(mid("070200", "lead", "b001"), "lead", "root", T1, "blocked")
    t9 = s.task(mid("070300", "root", "t009"), "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070301"), stem("070401"))
    s.result(mid("070500", "lead", "d009"), "lead", "root", t9, "done")
    cases = record(s)["cases"]
    assert [c["cut"] for c in cases] == [True, False]
    assert cases[0]["runs"] == 1 and cases[1]["runs"] == 2
    assert cases[0]["state"] == "blocked"


def test_a_run_credit_is_counted_apart_and_not_charged(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"), stem("070201"))
    s.msg(mid("070202", "runtime", "c001"), "runtime", "lead", "note", title=f"run credit lead@{stem('070101')}", budget=1, wake=False)
    s.result(mid("070500", "lead", "d001"), "lead", "root", T1, "done")
    case = record(s)["cases"][0]
    assert case["runs"] == 1 and case["credited"] == 1


def test_relayed_runs_lie_in_the_interval_of_the_relayed_rework(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.result(mid("070200", "lead", "d001"), "lead", "root", T1, "done")
    t2 = s.task(mid("070300", "root", "t002"), "root", "lead", 6, service=SVC, contract=1, revises=T1, source="relayed")
    s.runs("lead", stem("070301"), stem("070302"))
    s.result(mid("070400", "lead", "d002"), "lead", "root", t2, "done")
    t3 = s.task(mid("070500", "root", "t003"), "root", "lead", 5, service=SVC, contract=1, revises=t2, source="human")
    s.runs("lead", stem("070501"))
    s.result(mid("070600", "lead", "d003"), "lead", "root", t3, "done")
    case = record(s)["cases"][0]
    assert case["runs"] == 4 and case["relayed_runs"] == 2 and case["spend"] == 4 and case["user_cost"] == 2
    assert [t["source"] for t in case["top_ups"]] == ["relayed", "human"]


def test_the_default_one_run_rework_with_nothing_left_approves_nothing_and_a_later_grant_does(tmp_path):
    """0a.5 A2 (E7 s2 memo 1): 9 used + 3 held = the 12 handed down, so the 1-run human rework is no approval; root's grant of 1 after it
    finds 9 used, 3 held and the unapproved run set aside: 9 + 3 + 1 = 13."""
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", *(stem(f"0701{k:02d}") for k in range(9)))
    s.result(mid("070200", "lead", "b001"), "lead", "root", T1, "blocked")
    t2 = s.task(mid("070300", "root", "t002"), "root", "lead", 1, service=SVC, contract=1, revises=T1, source="human")
    s.msg(mid("070400", "root", "g001"), "root", "lead", "note", title="grant", budget=1, wake=False)
    s.result(mid("070500", "lead", "d002"), "lead", "root", t2, "done")
    case = record(s)["cases"][0]
    assert case["user_approved"] == 13
    assert {"id": mid("070400", "root", "g001"), "source": "granted", "amount": 1} in case["top_ups"]


# ------------------------------------------------------------------------------------------------ deliveries, verdicts, escapes


def test_deliveries_verdicts_escape_signer_and_first_delivery(tmp_path):
    s = base(tmp_path)
    ids = one_case(s)
    r = record(s)
    assert r["deliveries"]["total"] == 2 and r["deliveries"]["judged"] == 2
    assert r["deliveries"]["unjudged_cases"] == [] and r["deliveries"]["not_on_a_delivery"] == []
    assert r["first_deliveries"] == {"accepted": 0, "rejected": 1, "no_verdict": 0, "superseded": 0, "neither": 0, "never_delivered": 0}
    assert r["cases"][0]["first"] == {"task": T1, "outcome": "rejected", "superseded_by": None, "superseded_source": None}
    (esc,) = r["escapes"]
    assert esc["assertion"] == "R1" and esc["case"] == T1 and esc["task"] == T1 and esc["verdict"] == ids["n1"]
    assert esc["signer"] == "lead/reviewer"
    assert esc["cause"] == "contract-gap" and esc["rule"] == "answer" and esc["rules"] == ["answer", "words"]
    assert esc["detail"] == [mid("071000", "root", "k001"), "C3"] and esc["also"] == [] and esc["before_verdict"] == ""
    assert esc["attribution"] == "not its" and esc["class"] is None
    (ver,) = r["verifiers"]
    assert ver["addr"] == "lead/reviewer" and ver["judged"] == 1  # T2 was signed off by the owner alone: no report's result after it
    assert ver["escapes"] == {"counted": {}, "not_its": {"contract-gap": 1}} and ver["pass_precision"] == [1, 1]
    assert ver["rechecks"] == 0 and ver["rework_runs"] == 0 and ver["fails_error"] == ""


def test_a_reject_then_an_accept_on_one_delivery_stays_an_escape_and_the_reject_decides(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.result(mid("070200", "lead", "d001"), "lead", "root", T1, "done")
    n1 = s.verdict(mid("070300", "root", "n001"), T1, "reject", "Not right.")
    s.verdict(mid("070400", "root", "n002"), T1, "accept", "OK, I'll take it as it is.")
    r = record(s)
    (esc,) = r["escapes"]
    assert esc["verdict"] == n1 and esc["cause"] == "untyped" and esc["rule"] == "none" and esc["attribution"] == "counted"
    assert r["cases"][0]["first"]["outcome"] == "rejected"
    assert r["verifiers"] == []  # the owner signed it alone


def test_a_verdict_on_a_blocked_result_is_not_on_a_delivery(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.result(mid("070200", "lead", "b001"), "lead", "root", T1, "blocked")
    n1 = s.verdict(mid("070300", "root", "n001"), T1, "accept")
    r = record(s)
    assert r["deliveries"]["total"] == 0 and r["deliveries"]["not_on_a_delivery"] == [n1]
    assert r["cases"][0]["first"] is None and r["first_deliveries"]["never_delivered"] == 1


def test_a_delivery_without_a_human_verdict_is_superseded_by_the_next_task_and_relayed_only_is_counted(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.result(mid("070200", "lead", "d001"), "lead", "root", T1, "done")
    t2 = s.task(mid("070300", "root", "t002"), "root", "lead", 6, service=SVC, contract=1, revises=T1, source="relayed")
    s.runs("lead", stem("070301"))
    s.result(mid("070400", "lead", "d002"), "lead", "root", t2, "done")
    s.verdict(mid("070500", "root", "n001"), t2, "reject", "my own reading", source="relayed")
    r = record(s)
    assert r["cases"][0]["first"] == {"task": T1, "outcome": "none", "superseded_by": t2, "superseded_source": "relayed"}
    assert r["first_deliveries"]["superseded"] == 1 and r["first_deliveries"]["no_verdict"] == 1
    assert r["deliveries"]["unjudged_cases"] == [T1] and r["deliveries"]["relayed_only"] == [T1]
    assert r["escapes"] == []


def test_rule_1_types_a_rejected_relayed_rework_as_relayed_error(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.result(mid("070200", "lead", "d001"), "lead", "root", T1, "done")
    t2 = s.task(mid("070300", "root", "t002"), "root", "lead", 6, service=SVC, contract=1, revises=T1, source="relayed")
    s.runs("lead", stem("070301"))
    s.result(mid("070400", "lead", "d002"), "lead", "root", t2, "done")
    s.verdict(mid("070500", "root", "n001"), t2, "reject", "Never like this.")
    (esc,) = record(s)["escapes"]
    assert esc["cause"] == "relayed-error" and esc["rule"] == "relayed task" and esc["detail"] == [t2]
    assert esc["rules"] == ["relayed task", "words"] and esc["also"] == ["contract-gap"]


def test_rule_3_a_link_naming_a_carried_kept_criterion_is_a_reviewer_miss(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.result(mid("070200", "lead", "d001"), "lead", "root", T1, "done")
    n1 = s.verdict(mid("070300", "root", "n001"), T1, "reject", "Not right.")
    k = s.link(mid("070400", "root", "k001"), n1, "C2")
    (esc,) = record(s)["escapes"]
    assert esc["cause"] == "reviewer-miss" and esc["rule"] == "link" and esc["detail"] == [k, "C2"] and esc["class"] == "off_spec"


# ------------------------------------------------------------------------------------------------ alarms and timeline


def _judged_cases(s: Stream, n: int, *, reject_links=()):
    """``n`` one-task cases, each delivered; case k gets a human reject linked to ``reject_links[k]`` when given, else an accept."""
    for k in range(n):
        t = s.task(mid(f"07{k + 1:02d}00", "root", f"t{k:03d}"), "root", "lead", 12, service=SVC, contract=1)
        s.runs("lead", stem(f"07{k + 1:02d}01"))
        s.result(mid(f"07{k + 1:02d}10", "lead", f"d{k:03d}"), "lead", "root", t, "done")
        if k < len(reject_links) and reject_links[k]:
            n1 = s.verdict(mid(f"07{k + 1:02d}20", "root", f"n{k:03d}"), t, "reject", "no")
            s.link(mid(f"07{k + 1:02d}30", "root", f"k{k:03d}"), n1, reject_links[k])
        else:
            s.verdict(mid(f"07{k + 1:02d}20", "root", f"n{k:03d}"), t, "accept")


def test_repeat_alarm_fires_on_a_criterion_named_in_two_of_the_last_three_judged_cases(tmp_path):
    s = base(tmp_path)
    _judged_cases(s, 3, reject_links=("C1", "", "C1"))
    rep = record(s)["alarms"]["repeat"]
    assert rep["state"] == "fires" and rep["judged"] == 3 and rep["fired"] == ["C1"]
    assert rep["subjects"] == {"R1": 1, "R2": 1, "C1": 2} and rep["not_counted"] == {}
    assert len(rep["window"]) == 3


def test_alarms_are_n_a_below_min_judged_and_cost_compares_user_cost_with_user_approved(tmp_path):
    s = base(tmp_path)
    _judged_cases(s, 2)
    al = record(s)["alarms"]
    assert al["repeat"]["state"] == "n/a" and al["repeat"]["window"] == []
    assert al["cost"] == {"state": "n/a", "judged": 2, "compared": 2, "cases": [], "skipped": []}


def test_cost_alarm_fires_above_1_25_times_the_approved_runs(tmp_path):
    s = base(tmp_path)
    s.contract(1, ["Alpha criterion.", "Beta criterion."], defined="2026-10-25T07:00:00.000000+00:00", budget=2)
    _judged_cases(s, 3)
    t = mid("071000", "root", "tbig")
    s.task(t, "root", "lead", 2, service=SVC, contract=1)
    s.runs("lead", stem("071001"), stem("071002"), stem("071003"))
    s.result(mid("071100", "lead", "dbig"), "lead", "root", t, "done")
    cost = record(s)["alarms"]["cost"]
    assert cost["state"] == "fires" and cost["compared"] == 4
    assert cost["cases"] == [{"case": t, "user_cost": 3, "user_approved": 2, "ratio": "1.50", "relayed_runs": 0, "total": 3}]


def test_timeline_contract_playbook_and_top_up_marks(tmp_path):
    s = base(tmp_path)
    ids = one_case(s)
    s.playbook(1, "## Steps\n1. Do it.", revised="2026-10-25T07:00:00.000000+00:00", by="root", current=False)
    s.playbook(2, "## Steps\n1. Do it.\n- C3: Gamma criterion.", revised="2026-10-25T07:10:40.000000+00:00", by="lead",
               evidence=["C3", "R1", mid("071000", "root", "k001")], admitted="c")
    r = record(s)
    assert r["contract"] == 2 and r["playbook"] == 2
    kinds = [(m["kind"], m.get("version")) for m in r["timeline"]]
    assert kinds == [("contract", 1), ("playbook", 1), ("contract", 2), ("playbook", 2), ("top-up", None)]
    c2 = r["timeline"][2]
    assert c2["adds"] == ["C3"] and c2["removes"] == [] and c2["basis"] == "answers" and c2["answers"] == "R1"
    assert c2["confirmed"] == [{"id": "C3", "link": mid("071000", "root", "k001")}] and c2["not_confirmed"] == []
    assert c2["when"] == "2026-10-25T07:10:30Z"
    p1, p2 = r["timeline"][1], r["timeline"][3]
    assert p1["basis"] == "client" and p1["changed"] == 2
    assert p2["basis"] == "c" and p2["changed"] == 1 and p2["own_words"] == 1 and p2["beyond"] == 0 and p2["removed"] == 0
    assert p2["evidence"] == ["C3", "R1", mid("071000", "root", "k001")] and p2["cited"] == [{"id": "C3", "text": "Gamma criterion."}]
    top = r["timeline"][4]
    assert top == {"kind": "top-up", "when": "2026-10-25T07:11:00Z", "case": T1, "id": ids["t2"], "source": "human", "amount": 5}


# ------------------------------------------------------------------------------------------------ held tasks, files not as delivered


def test_a_blocked_task_the_sender_moved_past_without_a_verdict_is_left_blocked_with_the_held_budget(tmp_path):
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    a = s.task(mid("070200", "lead", "a001"), "lead", "lead/writer", 3)
    s.runs("lead/writer", stem("070201"))
    s.result(mid("070300", "lead/writer", "w001"), "lead/writer", "lead", a, "blocked")
    s.task(mid("070400", "lead", "a002"), "lead", "lead/writer", 2)
    moved = derive(s)["moved_past"]
    assert moved == [{
        "addr": "lead/writer", "held": 4, "held_error": "", "error": "",
        "tasks": [{"id": a, "sender": "lead", "title": None, "blocked": "2026-10-25T07:03:00Z", "left_blocked": True, "sent_since": 1}],
    }]


def test_a_blocked_task_released_by_a_revision_is_not_held(tmp_path):
    s = base(tmp_path)
    a = s.task(mid("070200", "lead", "a001"), "lead", "lead/writer", 3)
    s.result(mid("070300", "lead/writer", "w001"), "lead/writer", "lead", a, "blocked")
    s.task(mid("070400", "lead", "a002"), "lead", "lead/writer", 2, revises=a)
    assert derive(s)["moved_past"] == []


def _two_deliveries_of_one_file(s: Stream):
    """Head T1 delivered memo v1; a relayed rework T2 delivered memo v2."""
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.memo_version("lead/writer/work/memo.md", 1, "aaa1111", "2026-10-25T07:01:30Z", "version one\n")
    s.result(mid("070200", "lead", "d001"), "lead", "root", T1, "done", artifacts=["lead/writer/work/memo.md"])
    t2 = s.task(mid("070300", "root", "t002"), "root", "lead", 6, service=SVC, contract=1, revises=T1, source="relayed")
    s.runs("lead", stem("070301"))
    s.memo_version("lead/writer/work/memo.md", 2, "bbb2222", "2026-10-25T07:03:30Z", "version two\n")
    s.result(mid("070400", "lead", "d002"), "lead", "root", t2, "done", artifacts=["lead/writer/work/memo.md"])
    return t2


def test_a_file_equal_to_an_earlier_delivery_that_relayed_reworks_changed_is_relayed_and_names_the_given_delivery(tmp_path):
    s = base(tmp_path)
    t2 = _two_deliveries_of_one_file(s)
    s.verdict(mid("070500", "root", "n001"), T1, "accept")
    s.deliverable("memo.md", "version one\n", 1792911960.0)
    d = record(s)["deliveries"]
    assert d["not_as_delivered"] == [] and d["unjudged_cases"] == [] and d["relayed_only"] == []
    assert d["unseen_relayed"] == [T1]
    assert t2  # the relayed rework is the later delivery the user was not given


def test_a_file_equal_to_no_checked_version_is_not_as_delivered_and_voids_later_verdicts(tmp_path):
    s = base(tmp_path)
    t2 = _two_deliveries_of_one_file(s)
    # the file was written at 07:04:30 (after both deliveries); the user's accept at 07:05:00 comes after the change: voided
    s.verdict(mid("070500", "root", "n001"), t2, "accept")
    s.deliverable("memo.md", "hand edited\n", 1792911870.0)  # 2026-10-25T07:04:30Z
    r = record(s)
    assert r["deliveries"]["not_as_delivered"] == [{"case": T1, "task": t2}]
    assert r["deliveries"]["neither"] == [{"case": T1, "task": t2}] and r["deliveries"]["judged"] == 0


def git_log(s: Stream, commits):
    """Write ``org-git-log.txt`` (``git log --stat --date=iso``, newest first): ``commits`` = [(short sha, 'YYYY-MM-DD HH:MM:SS', [paths])], oldest
    first; each full sha is the short sha padded with zeros."""
    out = []
    for short, when, paths in reversed(commits):
        out += [f"commit {short.ljust(40, '0')}", "Author: hirearchy <hirearchy@localhost>", f"Date:   {when} +0000", "", "    run ok", ""]
        out += [f" {p} | 1 +" for p in paths] + [f" {len(paths)} files changed", ""]
    (s.root / "org-git-log.txt").write_text("\n".join(out) + "\n")


def test_the_checked_version_is_the_file_at_the_first_commit_that_holds_the_results_sent_copy(tmp_path):
    """Design 0a.2 (P3's checked version, ``at_result``): the blob of the artifact at the first org-git commit that holds the result's sent
    copy. The run that sends the result commits the file it wrote with it, so a version committed seconds after the result's time is its."""
    s = base(tmp_path)
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    s.memo_version("lead/writer/work/memo.md", 1, "aaa1111", "2026-10-25T07:01:30Z", "version one\n")
    r1 = s.result(mid("070200", "lead", "d001"), "lead", "root", T1, "done", artifacts=["lead/writer/work/memo.md"])
    s.memo_version("lead/writer/work/memo.md", 2, "bbb2222", "2026-10-25T07:02:05Z", "version two\n")
    git_log(s, [("aaa1111", "2026-10-25 07:01:30", ["lead/writer/work/memo.md"]),
                ("bbb2222", "2026-10-25 07:02:05", [f"lead/sent/{r1}.md", f"inbox/{r1}.md", "lead/writer/work/memo.md"])])
    s.verdict(mid("070300", "root", "n001"), T1, "accept")
    s.deliverable("memo.md", "version two\n", 1792911750.0)  # 2026-10-25T07:02:30Z
    d = record(s)["deliveries"]
    assert d["not_as_delivered"] == [] and d["judged"] == 1  # the INDEX-time rule would give v1 and a `differs` finding


def _late_head_result_and_a_relayed_rework(s: Stream, *, verdicts_on_rework=True):
    """E7 s2's shape: head T1 blocked, human rework T2 delivered memo v2; T1's late done result names the same v2 two seconds later; a relayed
    rework T3 then delivered v3; the user's file is v2; the user's reject and accept are on T2."""
    s.task(T1, "root", "lead", 12, service=SVC, contract=1)
    s.runs("lead", stem("070101"))
    b1 = s.result(mid("070200", "lead", "b001"), "lead", "root", T1, "blocked", artifacts=["lead/writer/work/memo.md"])
    t2 = s.task(mid("070300", "root", "t002"), "root", "lead", 1, service=SVC, contract=1, revises=T1, source="human")
    s.runs("lead", stem("070301"))
    s.memo_version("lead/writer/work/memo.md", 1, "aaa1111", "2026-10-25T07:03:30Z", "version two\n")
    r2 = s.result(mid("070400", "lead", "d002"), "lead", "root", t2, "done", artifacts=["lead/writer/work/memo.md"])
    r1 = s.result(mid("070402", "lead", "d001"), "lead", "root", T1, "done", artifacts=["lead/writer/work/memo.md"], supersedes=b1)
    s.deliverable("memo.md", "version two\n", 1792911850.0)  # 2026-10-25T07:04:10Z
    t3 = s.task(mid("070500", "root", "t003"), "root", "lead", 6, service=SVC, contract=1, revises=t2, source="relayed")
    s.runs("lead", stem("070501"))
    s.memo_version("lead/writer/work/memo.md", 2, "bbb2222", "2026-10-25T07:05:30Z", "version three\n")
    s.result(mid("070600", "lead", "d003"), "lead", "root", t3, "done", artifacts=["lead/writer/work/memo.md"])
    if verdicts_on_rework:
        s.verdict(mid("070700", "root", "n001"), t2, "reject", "Always put Gamma first.")
        s.verdict(mid("070800", "root", "n002"), t2, "accept", "OK, I'll take it as it is.")
    return t2, t3, r1, r2


def test_given_delivery_prefers_the_equal_delivery_with_a_human_verdict_and_reports_the_p3_choice_as_f_g0_1(tmp_path):
    """OQ-2 as the manager ruled it (manager-decision-selfcheck.md item 2): the given delivery is the delivery whose checked artifact equals the
    file; of several, the one with a human-tier verdict; with none, the latest (the one P3's relayed finding names). P3's newest-first pair
    (the late head result) is reported apart as F-G0-1."""
    s = base(tmp_path)
    t2, t3, r1, r2 = _late_head_result_and_a_relayed_rework(s)
    data = derive(s)
    d = data["services"][0]["deliveries"]
    assert d["unjudged_cases"] == [] and d["relayed_only"] == [] and d["not_as_delivered"] == []
    assert d["unseen_relayed"] == [T1]
    (g,) = data["given_deliveries"]
    assert (g["case"], g["file"], g["given"], g["by"], g["p3_names"], g["differs"]) == (T1, "memo.md", t2, "human verdict", T1, True)
    assert set(g["candidates"]) == {T1, t2} and set(g["results"]) == {r1, r2}


def test_given_delivery_without_a_human_verdict_is_the_one_p3_names(tmp_path):
    s = base(tmp_path)
    _late_head_result_and_a_relayed_rework(s, verdicts_on_rework=False)
    data = derive(s)
    (g,) = data["given_deliveries"]
    assert (g["given"], g["by"], g["p3_names"], g["differs"]) == (T1, "P3's relayed finding", T1, False)
    assert data["services"][0]["deliveries"]["unjudged_cases"] == [T1]


def test_compare_names_f_g0_1_where_the_given_delivery_differs_from_p3s_pair(tmp_path):
    s = base(tmp_path)
    t2, _, r1, r2 = _late_head_result_and_a_relayed_rework(s)
    mine = derive(s)
    product = json.loads(json.dumps({k: v for k, v in mine.items() if k not in ("given_deliveries",)}))
    product["services"][0]["deliveries"]["unjudged_cases"] = [T1]  # what the product's newest-first pair gives
    lines = rq.compare(product, mine)
    assert any(ln.startswith("MISMATCH services.0.deliveries.unjudged_cases") for ln in lines)
    f = [ln for ln in lines if ln.startswith("F-G0-1 ")]
    assert len(f) == 1 and T1 in f[0] and t2 in f[0] and r1 in f[0] and r2 in f[0] and "memos/versions/INDEX.txt" in f[0]
    assert not any("given_deliveries" in ln for ln in lines if ln.startswith("MISMATCH"))


# ------------------------------------------------------------------------------------------------ CLI


def test_cli_writes_rederived_json_with_source_files_and_script(tmp_path):
    s = base(tmp_path)
    one_case(s)
    out = tmp_path / "out"
    p = run(s.root, "--out", out)
    assert p.returncode == 0, p.stderr
    data = json.loads((out / "rederived.json").read_text())
    assert data["schema"] == 1 and data["script"]["name"] == "rederive_quality.py" and len(data["script"]["md5"]) == 32
    assert "msgs/sent/" + T1 + ".md" in data["source_files"]
    assert data["one_off"] is None and data["nested"] == []


def test_compare_lists_mismatches_and_not_derived_keys_and_exits_0(tmp_path):
    s = base(tmp_path)
    one_case(s)
    s.task(mid("072000", "root", "t900"), "root", "lead", 12, service=SVC, contract=2)  # an open case: its ``stalled`` is not derived
    product = rq.rederive(s.root)
    for k in ("source_files", "script", "not_derived"):
        product.pop(k, None)
    product["services"][0]["cases"][0]["runs"] = 99
    product["services"][0]["cases"][1]["stalled"] = True
    qj = tmp_path / "quality.json"
    qj.write_text(json.dumps(product))
    out = tmp_path / "out"
    p = run(s.root, "--out", out, "--compare", qj)
    assert p.returncode == 0, p.stderr
    lines = (out / "mismatches.txt").read_text().splitlines()
    assert "MISMATCH services.0.cases.0.runs: product=99 rederived=7" in lines
    assert "NOT DERIVED services.0.cases.1.stalled" in lines
    assert lines[-1].startswith("compared ") and lines[-1].endswith(" 1 mismatches")


def test_an_unreadable_input_exits_2(tmp_path):
    p = run(tmp_path / "missing", "--out", tmp_path / "out")
    assert p.returncode == 2
    s = base(tmp_path)
    p = run(s.root, "--out", tmp_path / "out", "--compare", tmp_path / "nope.json")
    assert p.returncode == 2


# ------------------------------------------------------------------------------------------------ E7 (the self-check)


def test_selector_keys_pick_one_list_element_by_fields_and_hash_is_the_length():
    data = {"a": [{"kind": "x", "id": "20261025T070000000000-lead.writer-1"}, {"kind": "y", "id": "2"}]}
    assert rq.get_path(data, "a.[kind=x&id=20261025T070000000000-lead.writer-1].kind") == "x"
    assert rq.get_path(data, "a.#") == 2
    with pytest.raises(KeyError):
        rq.get_path(data, "a.[kind=z].id")


@e7
def test_expected_file_is_a_transcription_list_with_sources():
    entries = json.loads(EXPECTED.read_text())
    optional = {"published", "declared_product_deviation"}  # an amended entry keeps its published value; F-G0-1 names the product's value
    assert entries and all({"stream", "key", "expected", "source"} <= set(e) <= {"stream", "key", "expected", "source"} | optional for e in entries)
    assert {e["stream"] for e in entries} == {"s1", "s2", "s3"}
    assert all(e["source"] for e in entries)
    assert all("manager-decision-selfcheck.md" in e["source"] for e in entries if "published" in e or "declared_product_deviation" in e)


@e7
@pytest.mark.parametrize("label", ["s1", "s2", "s3"])
def test_e7_stream_rederives_without_error(label):
    data = rq.rederive(E7EV / label)
    (svc,) = data["services"]
    assert svc["service"] == "weekly-meeting-memo" and svc["owner"] == "lead" and svc["error"] == ""
    assert len(svc["cases"]) == 3


@e7
def test_e7_selfcheck_passes_and_declares_f_g0_1_in_s2_only(tmp_path):
    """The self-check compares every transcribed value (amended by manager-decision-selfcheck.md where the published value was the replay kit's
    or contradicted the design's rule on the history path). No MISMATCH remains; the one declared product deviation is F-G0-1 in s2's memo 1:
    the design's given delivery c671 against P3's newest-first pair, the head 3ca4."""
    p = run("--selfcheck", E7EV, "--out", tmp_path)
    lines = p.stdout.splitlines()
    assert lines[-1].startswith("selfcheck rederive: ")
    assert [ln for ln in lines if ln.startswith("MISMATCH")] == [] and p.returncode == 0
    declared = [ln for ln in lines if ln.startswith("DECLARED")]
    assert len(declared) == 1 and declared[0].startswith("DECLARED s2: F-G0-1 case 20261025T074451197103-root-3ca4")
    assert "20261025T075038845671-root-c671 (human verdict)" in declared[0]
    for label in ("s1", "s2", "s3"):
        assert (tmp_path / f"e7-{label}" / "rederived.json").exists()
        assert (tmp_path / f"e7-{label}" / "rederive-selfcheck.txt").exists()
