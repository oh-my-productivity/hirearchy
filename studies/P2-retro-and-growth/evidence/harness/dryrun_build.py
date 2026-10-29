#!/usr/bin/env python3
"""P2 self-check: build a throwaway organization with P1-sized reworks, through the product's own calls (no scheduler, no LLM, no network).

Run INSIDE the arm's product (arm R: `uv --directory /Volumes/workspace/hirearchy run python dryrun_build.py ...`; arm C:
`uv --directory /Volumes/workspace/hirearchy/.worktrees/p2-arm-c run python dryrun_build.py ...`), so every product call is that arm's.
It never opens a product source file: it calls the public `hirearchy.core.Org` facade (its signatures are read at run time) and the arm's
`hirearchy` CLI. The organization lives under the study's sandbox (`/tmp/hirearchy-p2/...`), never under /Users/aminalizadeh/organization.

    python dryrun_build.py --arm R|C --org <S>/org --repo <arm dir> --phase setup      the team and the memo service (arm R: a sourced
                                                                                        full blueprint applied at the terminal; arm C:
                                                                                        string criteria), then memos 1-4 with P1-sized
                                                                                        reworks, the relayed rework (A-R) and 3 one-off
                                                                                        action lists of one shape, each judged
    python dryrun_build.py --arm R --org <S>/org --repo <arm dir> --phase after --service <name>
                                                                                        memo 5 (accepted), one request of the extracted
                                                                                        service (accepted), one hand edit of the writer's
                                                                                        charter body, committed (an `outside the tools`
                                                                                        change: the count must read 1)
Writes <S>/dryrun-facts.json: the ids it made (cases, rejections, the scripted repeats), for the readers' checks.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = "root"
LIST_TITLE = "Action list for the ops team ({date})"
LIST_GOAL = "Make a one-page action list from the notes of {date} for the ops team."
LIST_CRITERIA = "Each action with its owner and due date; at most one page."
H2_WORDS = ("Thanks! The file name each time is fine. Format: a markdown memo, at most 400 words, with the action items as a table with "
            "columns Owner | Action | Due (ISO dates, 'none' if there's no date). The rest of your defaults are fine, the deliverables "
            "folder too. Please keep it cheap, but I need it right - about 12 runs per memo. No separate reviewer: the lead checks. "
            "Use the words from the notes.")
OWNERS_Q = "Owners: initials or full names?"


def cli(repo, org, *args, check=True):
    p = subprocess.run(["uv", "--directory", repo, "run", "hirearchy", "--root", str(org), *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"CLI FAILED {' '.join(args)}: exit {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


def blueprint(arm, sandbox):
    crit_r = [
        {"text": "One memo per notes file, at most 400 words.", "default": True},
        {"text": "The memo lists every decision and every commitment in the notes, informal ones included.", "default": True},
        {"text": "The action items are a table Owner | Action | Due, with ISO dates and 'none' if there's no date.",
         "from": "with the action items as a table with columns Owner | Action | Due (ISO dates, 'none' if there's no date)"},
        {"text": "Decisions and actions use the notes' own words.", "from": "Use the words from the notes.", "asked": OWNERS_Q},
    ]
    crit = crit_r if arm == "R" else [c["text"] for c in crit_r]
    bp = {
        "mission": "Every week, turn the user's meeting notes into a short memo of decisions and action items.",
        "needs": {"kind": "writing", "inputs": [str(sandbox / "notes")], "budget_runs": 12, "review": False},
        "agents": [{"name": "lead", "template": "manager", "children": [{"name": "writer", "template": "writer"}]}],
        "services": [{
            "name": "weekly-memo", "owner": "lead", "description": "One memo of decisions and action items from one meeting's notes file.",
            "inputs": [{"name": "notes_file", "description": "the notes file name, e.g. 2026-10-05.md", "required": True}],
            "acceptance": crit,
            "deliverable": {"description": "one markdown memo", "format": "markdown", "path": str(sandbox / "deliverables")},
            "budget": 12,
        }],
    }
    if arm == "R":
        bp["needs"]["elicitation"] = H2_WORDS
    return bp


def run(org, addr, fn=None):
    """One run of `addr` (a run log, as the scheduler's runs leave one), doing `fn` inside it."""
    org.begin_run(addr)
    org.start_run_log(addr)
    out = fn() if fn else None
    org.end_run(addr, ok=True)
    return out


def deliver(org, task, lead="lead", writer="lead/writer", summary="Delivered."):
    """A P1-sized delivery: the lead delegates, the writer reports, the lead reports done (3 runs)."""
    sub = run(org, lead, lambda: org.delegate(lead, writer, "Draft", "Write the draft.", "As the request says.", budget=2))
    run(org, writer, lambda: org.report(writer, sub.id, "done", "Draft written."))
    aar = "Expected: none. Happened: delivered. Caught at: none. Cause: none. Prevent: none. Near miss: none."
    run(org, lead, lambda: org.report(lead, task.id, "done", summary, lessons=aar))


def memo(org, date, revises=None, source="human"):
    kw = {"revises": revises, "source": source} if revises else {}
    return org.request(ROOT, "weekly-memo", {"notes_file": f"{date}.md"}, **kw)


def reject_and_answer(org, task, words, answer, facts, about=None, same_as=None, rule=None):
    """The user's rejection (human tier) and its answer: a new criterion (define_service answers=) or a 'same as R<j>' link."""
    no = org.feedback(ROOT, task.id, "reject", words, source="human")
    facts["rejections"].append(no.id)
    if rule:
        org.define_service(ROOT, "lead", "weekly-memo", add_acceptance=[rule], answers=no.id, about=about, words=answer)
    else:
        org.feedback(ROOT, task.id, "reject", answer, source="human", criterion=[same_as], confirms=no.id)
    return no


def r_id_of(org_dir, repo, note_id):
    """The `R<k>` id the product gave a human rejection note, read from `quality --json` (its escapes' `verdict` and `assertion`; never assumed)."""
    q = json.loads(cli(repo, org_dir, "quality", "--json").stdout)
    for svc in q.get("services", []):
        for e in svc.get("escapes", []) or []:
            if e.get("verdict") == note_id and e.get("assertion"):
                return e["assertion"]
    sys.exit(f"no R id found for {note_id} in quality --json")


def one_off(org, date, facts):
    t = org.delegate(ROOT, "lead", LIST_TITLE.format(date=date), LIST_GOAL.format(date=date), LIST_CRITERIA, budget=4)
    run(org, "lead", lambda: org.report("lead", t.id, "done", "List done."))
    org.feedback(ROOT, t.id, "accept", "Keep it.", source="human")
    facts["one_offs"].append(t.id)
    return t


def phase_setup(arm, org_dir, repo):
    sandbox = org_dir.parent
    for d in ("notes", "deliverables", "ws"):
        (sandbox / d).mkdir(parents=True, exist_ok=True)
    cli(repo, org_dir.parent / "nowhere", "init", str(org_dir), "--mission", "Memos from meeting notes.", check=True)
    # one read-only root call over MCP before the plan, as a stream's assistant makes them before its first apply_org: the org's event log
    # then holds the MCP path from before every charter's first version (SELFCHECK.md item 3)
    import asyncio
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mcp_catalog
    asyncio.run(mcp_catalog.catalog(repo, str(org_dir), "whoami"))
    bp = sandbox / "blueprint.json"
    bp.write_text(json.dumps(blueprint(arm, sandbox), indent=1))
    plan = cli(repo, org_dir, "plan", str(bp), "--allow-root", str(sandbox), check=False)
    (sandbox / "dryrun-plan.txt").write_text(plan.stdout + plan.stderr)
    applied = cli(repo, org_dir, "apply", str(bp), "--allow-root", str(sandbox), check=False)
    (sandbox / "dryrun-apply.txt").write_text(applied.stdout + applied.stderr)
    if applied.returncode != 0:
        sys.exit(f"apply of the full blueprint failed (exit {applied.returncode}):\n{applied.stdout}\n{applied.stderr}")
    from hirearchy.core import Org
    org = Org(org_dir) if not hasattr(Org, "open") else Org.open(org_dir)
    facts = {"arm": arm, "rejections": [], "trap_rejections": [], "one_offs": [], "memos": {}, "relayed": []}
    # memo 1: H6's contract gap (the Summary rule), the relayed rework (A-R: weighs 0), the user's rework, accepted
    t1 = memo(org, "2026-10-05")
    deliver(org, t1)
    inj = org.request(ROOT, "weekly-memo", {"notes_file": "2026-10-05.md"}, revises=t1.id, source="relayed",
                      note="Rework needed: 'before Friday' means Thursday.")
    deliver(org, inj)
    org.feedback(ROOT, inj.id, "reject", "Relayed: not right.", source="relayed")
    facts["relayed"].append(inj.id)
    reject_and_answer(org, t1, "No, not right yet. Always start the memo with a one-line 'Summary:' of the meeting, then the decisions, then "
                      "the action items.", "Yes, add it.", facts, about="C1",
                      rule="The memo starts with a one-line 'Summary:', then the decisions, then the action items.")
    r1 = memo(org, "2026-10-05", revises=t1.id)
    deliver(org, r1)
    org.feedback(ROOT, r1.id, "accept", "Yes, add it - and this version is right now, thanks.", source="human")
    facts["memos"]["1"] = [t1.id, r1.id]
    one_off(org, "2026-10-05", facts)
    # memos 2-4: the trap fails each time (relative due dates); the first answer adds the criterion, the next are 'same as' links
    first_trap = None
    for n, date, words in ((2, "2026-10-12", "Not right yet: Sam's due should be 2026-10-21. Always turn a deadline the notes give in words into "
                                             "its date, counted from the meeting's day."),
                           (3, "2026-10-19", "Not right yet: Lee's due should be 2026-10-30."),
                           (4, "2026-10-26", "Not right yet: Sam's due should be 2026-10-30.")):
        t = memo(org, date)
        deliver(org, t)
        if first_trap is None:
            no = reject_and_answer(org, t, words, "Yes, add it.", facts, about="C3",
                                   rule="A deadline the notes give in words is turned into its ISO date, counted from the meeting's day.")
            first_trap = no
        else:
            no = reject_and_answer(org, t, words, "Yes.", facts, same_as=r_id_of(org_dir, repo, first_trap.id))
        facts["trap_rejections"].append(no.id)
        rw = memo(org, date, revises=t.id)
        deliver(org, rw)
        org.feedback(ROOT, rw.id, "accept", "This version is right now, thanks.", source="human")
        facts["memos"][str(n)] = [t.id, rw.id]
        if n in (2, 3):
            one_off(org, date, facts)
    (sandbox / "dryrun-facts.json").write_text(json.dumps(facts, indent=1))
    print(json.dumps(facts))


def phase_trap5(arm, org_dir, repo):
    """F7 of the review (protocol 4.2): memo 5 requested and delivered on a scratch copy of the setup org, so that root's MCP `feedback`
    reject of it (TRAP-N's words, with and without `criterion`) shows the product's one question for the rejection."""
    from hirearchy.core import Org
    org = Org(org_dir) if not hasattr(Org, "open") else Org.open(org_dir)
    t5 = memo(org, "2026-11-02")
    deliver(org, t5)
    print(json.dumps({"memo5": t5.id}))
    return t5.id


TRAP_N = "Not right yet, the same problem as before: Lee's due should be 2026-11-04."  # protocol 4.3's TRAP-N line, memo 5's trap row


def mcp(repo, org_dir, tool, args, agent=None):
    import asyncio
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mcp_call
    return asyncio.run(mcp_call.call(repo, str(org_dir), tool, args, agent, False))


def phase_f7(arm, org_dir, repo, form):
    """F7 (c): on a scratch copy, memo 5 fails the trap and root records the TRAP-N rejection over MCP; form `a` without `criterion` (the
    product's reply lets root choose its question: the K29 path, `Same as R<j>: a one-off? Yes or no.` -> `Yes.` -> a link to R<j>), form
    `b` with criterion=[trap-crit] (`About C<k>: add ...?` -> K30 `Yes, add it.` -> define_service(answers=, about=C<k>)), form `c` the
    K30c path (an About id outside the class -> `No: it is the same as R<j>.` -> the link the reply's no-branch names, to trap-crit).
    Writes <sandbox>/f7-<form>.json: the replies (the product's question text) and the ids, for the class check of dryrun.sh."""
    sandbox = org_dir.parent
    facts = json.loads((sandbox.parent / "dryrun-facts.json").read_text()) if (sandbox.parent / "dryrun-facts.json").exists() else json.loads((sandbox / "dryrun-facts.json").read_text())
    t5 = phase_trap5(arm, org_dir, repo)
    trap1 = facts["trap_rejections"][0]
    rj = r_id_of(org_dir, repo, trap1)
    crit = "C6"  # [trap-crit]: v1 C1-C4, H6's answer C5, TRAP-1's answer C6 (dryrun_build's setup)
    args = {"task_id": t5, "verdict": "reject", "note": TRAP_N, "source": "human"}
    if form == "b":
        args["criterion"] = [crit]
    if form == "c":
        args["criterion"] = ["C2"]
    reply = mcp(repo, org_dir, "feedback", args)
    rej = next((ln.split("message ", 1)[1].split(",", 1)[0].split(")", 1)[0] for ln in reply.splitlines() if "(message " in ln), None)
    if form == "a":
        ans = mcp(repo, org_dir, "feedback", {"task_id": t5, "verdict": "reject", "confirms": rej, "criterion": [rj], "source": "human", "note": "Yes."})
    elif form == "b":
        ans = mcp(repo, org_dir, "define_service", {"owner": "lead", "name": "weekly-memo", "add_acceptance": [
            "A deadline the notes give in words is turned into its ISO date, counted from the meeting day, in every row."],
            "answers": rej, "about": crit, "words": "Yes, add it."})
    else:
        ans = mcp(repo, org_dir, "feedback", {"task_id": t5, "verdict": "reject", "confirms": rej, "criterion": [crit], "source": "human",
                                              "note": f"No: it is the same as {rj}."})  # K30c's line
    out = {"form": form, "memo5": t5, "rejection": rej, "trap1_rid": rj, "trap_crit": crit, "reply": reply, "answer": ans}
    (sandbox / f"f7-{form}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"form": form, "memo5": t5, "rejection": rej}))


def phase_labels(arm, org_dir, repo):
    """Label coverage for P2-E (design 4.5), on a scratch copy: a parent's MCP `write` of its report's charter, committed as a reaper
    commits (`by lead`); a terminal hire (`by root, outside a plan`); an extension that retires that agent (`from your change`); a service
    defined and retired at the terminal; a second terminal hire that stays."""
    sandbox = org_dir.parent
    c = (org_dir / "lead" / "writer" / "AGENT.md").read_text() + "\nWrite short paragraphs.\n"
    out = {"write": mcp(repo, org_dir, "write", {"path": "lead/writer/AGENT.md", "content": c}, agent="lead")}
    subprocess.run(["git", "-C", str(org_dir), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(org_dir), "commit", "-q", "-m", "lead: run (study self-check: the reaper's commit)"], check=True, capture_output=True)
    time.sleep(1.1)
    out["hire"] = cli(repo, org_dir, "hire", "root", "ops-helper", "--role", "Helper", "--charter", "Helps.").stdout
    ext = sandbox / "ext-retire.json"
    ext.write_text(json.dumps({"reason": "dry run: retire the helper", "extend": {"retire": [{"agent": "ops-helper", "reason": "dry run"}]}}))
    out["plan"] = cli(repo, org_dir, "plan", str(ext), check=False).stdout
    out["apply"] = cli(repo, org_dir, "apply", str(ext)).stdout
    out["define"] = cli(repo, org_dir, "define-service", "lead", "extra-svc", "--description", "x", "--input", "request:what", "--acceptance", "One line.",
                        "--deliverable", "one line", "--path", str(sandbox / "deliverables"), "--budget", "6").stdout
    out["retire"] = cli(repo, org_dir, "retire-service", "lead", "extra-svc", "--reason", "dry run").stdout
    out["hire2"] = cli(repo, org_dir, "hire", "root", "ops-keeper", "--role", "Keeper", "--charter", "Keeps.").stdout
    (sandbox / "labels.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v[:120] for k, v in out.items()}))


def to_second_boundary(offset):
    """Sleep until `offset` seconds after the next whole-second boundary of the wall clock."""
    now = time.time()
    time.sleep(int(now) + 1 + offset - now)


def phase_pf0(arm, org_dir, repo, align=None):
    """PF-0 on the product (protocol 12.6; manager-decision-prereg-pf.md): an organization built at the terminal only, so the event log
    holds CLI records and no MCP-path record before the plan's charters; the first versions committed as a reaper commits; then a hand
    edit of the writer's charter body, committed. The design's label is `outside the tools (a hand edit or the terminal)` (the log covers
    the window); PF-0's signature is the product's horizon label instead.
    The product's label depends on whether the event log's first record shares the older commit's whole second (freeze fix, manager ruling
    (b)); `align` makes the timing a matter of construction, not chance: `same` starts the build just after a whole-second boundary, so
    the first record and the charters' first commit fall in one second (the build takes well under a second; dryrun.sh records the timing it
    got); `earlier` waits for the next boundary after `init` (whose CLI record is the log's first), so the charters' first commit, made by `apply`,
    is always in a later second than the first record."""
    sandbox = org_dir.parent
    for d in ("notes", "deliverables"):
        (sandbox / d).mkdir(parents=True, exist_ok=True)
    if align == "same":
        to_second_boundary(0.02)
    cli(repo, sandbox / "nowhere", "init", str(org_dir), "--mission", "Memos from meeting notes.")
    if align == "earlier":
        to_second_boundary(0.05)
    bp = sandbox / "blueprint.json"
    bp.write_text(json.dumps(blueprint(arm, sandbox), indent=1))
    cli(repo, org_dir, "apply", str(bp), "--allow-root", str(sandbox))
    subprocess.run(["git", "-C", str(org_dir), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(org_dir), "commit", "-q", "-m", "snapshot (study self-check)"], capture_output=True)
    time.sleep(1.1)
    charter = org_dir / "lead" / "writer" / "AGENT.md"
    charter.write_text(charter.read_text() + "\nA line the human typed by hand.\n")
    subprocess.run(["git", "-C", str(org_dir), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(org_dir), "commit", "-q", "-m", "hand edit (study self-check: PF-0)"], check=True, capture_output=True)
    print(json.dumps({"pf0_org": str(org_dir), "hand_edit": "lead/writer/AGENT.md"}))


def phase_after(arm, org_dir, repo, service):
    sandbox = org_dir.parent
    facts = json.loads((sandbox / "dryrun-facts.json").read_text())
    from hirearchy.core import Org
    org = Org(org_dir) if not hasattr(Org, "open") else Org.open(org_dir)
    time.sleep(1.1)  # whole-second `created` against the brief's microseconds (design 22.3)
    t5 = memo(org, "2026-11-02")
    deliver(org, t5)
    org.feedback(ROOT, t5.id, "accept", "That one is right, all the items are there - keep it.", source="human")
    facts["memos"]["5"] = [t5.id]
    if service:
        owner = "lead"
        inputs = {"request": "the action list of 2026-11-02"}
        s = org.request(ROOT, service, inputs)
        aar = "Expected: C1. Happened: the list was made. Caught at: none. Cause: none. Prevent: none. Near miss: none."
        run(org, owner, lambda: org.report(owner, s.id, "done", "List done.", lessons=aar))
        org.feedback(ROOT, s.id, "accept", "Keep it.", source="human")
        facts["service_request"] = s.id
    # one hand edit of a charter body, committed: an unprompted charter edit `outside the tools` (design 3, 4.5)
    charter = org_dir / "lead" / "writer" / "AGENT.md"
    charter.write_text(charter.read_text() + "\nA line the human typed by hand.\n")
    subprocess.run(["git", "-C", str(org_dir), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(org_dir), "commit", "-q", "-m", "hand edit (study self-check)"], check=True, capture_output=True)
    facts["hand_edit"] = "lead/writer/AGENT.md"
    (sandbox / "dryrun-facts.json").write_text(json.dumps(facts, indent=1))
    print(json.dumps(facts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["R", "C"], required=True)
    ap.add_argument("--org", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--phase", choices=["setup", "after", "trap5", "f7", "labels", "pf0"], required=True)
    ap.add_argument("--service", default="")
    ap.add_argument("--form", choices=["a", "b", "c"], default="a")
    ap.add_argument("--align", choices=["same", "earlier"], default=None)
    a = ap.parse_args()
    org_dir = Path(a.org)
    if "/Users/aminalizadeh/organization" in str(org_dir.resolve()) or not str(org_dir.resolve()).startswith("/private/tmp/hirearchy-p2/"):
        sys.exit("refused: a throwaway org lives under /tmp/hirearchy-p2/ only")
    if a.phase == "setup":
        phase_setup(a.arm, org_dir, a.repo)
    elif a.phase == "trap5":
        phase_trap5(a.arm, org_dir, a.repo)
    elif a.phase == "f7":
        phase_f7(a.arm, org_dir, a.repo, a.form)
    elif a.phase == "labels":
        phase_labels(a.arm, org_dir, a.repo)
    elif a.phase == "pf0":
        phase_pf0(a.arm, org_dir, a.repo, a.align)
    else:
        phase_after(a.arm, org_dir, a.repo, a.service)


if __name__ == "__main__":
    main()
