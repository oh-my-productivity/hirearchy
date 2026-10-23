"""Golden: the files hirearchy writes (ORG.md, messages, charters, SERVICE.md / PLAYBOOK.md) and the runtime's notice texts."""

from pathlib import Path

from golden_support import check
from scenarios import BRIEF, PLAYBOOK, company, deliver_service, dirs, write_artifact

from hirearchy.app import wiring
from hirearchy.core import ROOT, Org

PROJECT = Path(__file__).resolve().parents[2]


def text_of(org: Org, addr: str, box: str, msg) -> str:
    return (org.dir(addr) / box / f"{msg.id}.md").read_text(encoding="utf-8")


def test_org_md_of_a_new_org(tmp_path, clock, norm):
    org = Org.init(tmp_path / "org", "Golden mission: ship the thing.")
    check("files/org_md_with_mission.md", (org.root / "ORG.md").read_text(encoding="utf-8"))
    other = Org.init(tmp_path / "bare", None, {"default_budget": 7})
    check("files/org_md_default_mission_custom_config.md", (other.root / "ORG.md").read_text(encoding="utf-8"))
    listing = sorted(str(p.relative_to(org.root)) for p in org.root.iterdir() if p.name != ".git")
    check("files/org_layout.txt", "\n".join(listing) + "\n\n" + (org.root / ".gitignore").read_text(encoding="utf-8"))


def test_message_files(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    org.define_service(ROOT, "ceo", "weekly-brief", playbook=PLAYBOOK, **BRIEF)
    clock.tick()

    task = org.delegate(ROOT, "ceo", "Plan the launch", "Make a launch plan.", "plan.md exists\nlaunch date named",
                        ["ceo/work/brief.md"], 6)
    clock.tick()
    check("messages/task.md", norm(text_of(org, "ceo", "inbox", task)))

    note = org.send(ROOT, "ceo", "Here are two more runs; please finish by Friday.", title="More budget", budget=2)
    clock.tick()
    check("messages/note_with_budget.md", norm(text_of(org, "ceo", "inbox", note)))

    request = org.request(ROOT, "weekly-brief", {"topic": "ai chips"}, title="Brief on AI chips", note="Keep it short.")
    clock.tick()
    check("messages/service_request_task.md", norm(text_of(org, "ceo", "inbox", request)))

    org.begin_run("ceo")
    org.start_run_log("ceo")
    write_artifact(org, "ceo", "ceo/work/brief.md", "# Brief\nAll good.\n", clock)
    result = org.report("ceo", request.id, "done", "Delivered the brief.", ["ceo/work/brief.md"],
                        lessons="Ask for sources first; the fact-check then finds nothing.")
    org.end_run("ceo", ok=True)
    clock.tick()
    check("messages/result_with_artifacts_and_lessons.md", norm(text_of(org, ROOT, "inbox", result)))

    fb = org.feedback(ROOT, request.id, "reject", "Too long: cut to 600 words.", source="human")
    clock.tick()
    check("messages/feedback_note.md", norm(text_of(org, "ceo", "inbox", fb)))

    notice = org.notify("ceo", "Budget returned", org.runtime.notices.budget_returned("ceo/eng", 3, "ceo", "done early"))
    clock.tick()
    check("messages/runtime_notice.md", norm(text_of(org, "ceo", "inbox", notice)))
    quiet = org.notify("ceo", "FYI", "Nothing to do.", wake=False, trace=request.id)
    check("messages/runtime_notice_no_wake.md", norm(text_of(org, "ceo", "inbox", quiet)))

    # what the human sees: the rendering of the same messages
    rendered = "\n".join(m.render() for m in org.messages("ceo", "inbox"))
    check("messages/rendered_inbox.txt", norm(rendered))


def test_runtime_notice_texts(tmp_path, clock, norm):
    notices = wiring.open_runtime(tmp_path).notices
    parts = [
        notices.budget("ceo/eng", 3),
        notices.budget_returned("ceo/eng", 4, "ceo", "finished"),
        notices.failures("ceo/eng", 3, "ceo/eng/runs/20260115T090000000000.log"),
        notices.failures("ceo/eng", 3, "ceo/eng/runs/20260115T090000000000.log", to_human=False),
        notices.nudge("T-1", "Build the API"),
        notices.stalled("ceo", "T-1", "Build the API", ["ceo", "root"]),
        notices.review_item("ceo/eng", "stuck", "no result for 2h"),
        notices.review_item("ceo/eng", "low_quality", "2 of 3 reports rejected", act=False),
        notices.review_item("ceo/eng", "expensive", "9 runs", branch="ceo"),
        notices.review_manager("ceo", [notices.review_item("ceo/eng", "idle", "nothing for 3 days")]),
        notices.review_root("1 agent flagged", ["- `ceo/eng` idle: nothing for 3 days"], {"ceo": "paused"}),
    ]
    check("messages/notice_templates.txt", "\n=====\n".join(parts) + "\n")


def test_charters_written_by_hire(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    ws, inputs = dirs(tmp_path)
    norm.add(ws, "<WS>")
    norm.add(inputs, "<INPUTS>")
    org.hire(ROOT, "dev", "Developer", "Write code in the workspace.", model="claude-sonnet-5.5", tools=["shell", "read", "write"],
             can_hire=True, max_children=3, workspace=str(ws), inputs=[str(inputs)])
    clock.tick()
    org.hire(ROOT, "analyst", "Analyst", "# Analyst charter\n\nOwn heading wins.", tools=["read"], inputs=[str(inputs)])
    out = []
    for addr in ("ceo", "ceo/eng", "dev", "analyst"):
        out.append(f"##### {addr}/AGENT.md\n" + (org.dir(addr) / "AGENT.md").read_text(encoding="utf-8"))
    check("charters/hire.md", norm("\n".join(out)))
    layout = sorted(str(p.relative_to(org.root)) for p in org.dir("dev").rglob("*"))
    check("charters/hired_agent_layout.txt", "\n".join(layout) + "\n")


def fill(text: str, base: Path) -> str:
    """What the assistant does with a template: the placeholders it needs get the user's values."""
    for name in ("docs", "data", "proj", "deliverables"):
        (base / name).mkdir(exist_ok=True)
    for placeholder, value in (("<folder-with-your-files>", "docs"), ("<folder-with-your-data>", "data"),
                               ("<project-folder>", "proj"), ("<name>", "briefs"), ("<service-name>", "my-service"),
                               ("<input-name>", "topic")):
        text = text.replace(placeholder, value)
    return text


def apply_blueprint(tmp_path, clock, norm, text: str, label: str, roots=None) -> Org:
    org = Org.init(tmp_path / "org", "Blueprint org", {"poll_seconds": 0.05})
    norm.add(org.root, "<ORG>")
    clock.tick()
    bp = org.runtime.blueprint_loader.load_text(text)
    summary = org.runtime.blueprint_applier.apply(bp, allowed_roots=roots)
    out = [f"##### summary\n{norm(summary.text())}\n"]
    for addr in org.agents():
        out.append(f"##### {addr}/AGENT.md\n" + norm((org.dir(addr) / "AGENT.md").read_text(encoding="utf-8")))
    for m in org.messages(summary.to, "inbox"):
        out.append(f"##### first message ({m.id})\n" + norm((org.dir(summary.to) / "inbox" / f"{m.id}.md").read_text(encoding="utf-8")))
    for f in sorted(org.root.rglob("SERVICE.md")) + sorted(org.root.rglob("PLAYBOOK.md")):
        out.append(f"##### {f.relative_to(org.root)}\n" + norm(f.read_text(encoding="utf-8")))
    check(f"charters/apply_{label}.md", "\n".join(out))
    return org


def test_charters_written_by_blueprint_apply_research_example(tmp_path, clock, norm):
    text = (PROJECT / "examples" / "blueprint-research.yaml").read_text(encoding="utf-8")
    apply_blueprint(tmp_path, clock, norm, text, "research_example")


def test_blueprint_apply_service_example_writes_service_and_playbook(tmp_path, clock, norm):
    text = (PROJECT / "examples" / "blueprint-service.yaml").read_text(encoding="utf-8")
    apply_blueprint(tmp_path, clock, norm, text, "service_example")


def test_blueprint_apply_code_template_with_builtin_tools(tmp_path, clock, norm):
    base = tmp_path / "base"
    base.mkdir()
    norm.add(base, "<BASE>")
    text = fill(wiring.open_runtime(tmp_path).blueprint_examples.example("code", base), base)
    text = text.replace("<PLACEHOLDER>", "x")
    apply_blueprint(tmp_path, clock, norm, text, "code_template", roots=[tmp_path])


def test_service_and_playbook_files(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    org.define_service(ROOT, "ceo", "weekly-brief", playbook=PLAYBOOK, notes="Mind the sources.", locked=False, **BRIEF)
    clock.tick()
    org.define_service(ROOT, "ceo", "plain-brief", **{**BRIEF, "budget": 4})  # no playbook yet
    clock.tick()
    first = org.request(ROOT, "weekly-brief", {"topic": "ai"})
    clock.tick()
    deliver_service(org, "ceo", first, clock, lessons="Cite while drafting.")
    no1 = org.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    clock.tick()
    second = org.request(ROOT, "weekly-brief", {"topic": "chips"})  # the same criterion fails in a second case: evidence of the revision
    clock.tick()
    deliver_service(org, "ceo", second, clock, lessons="Cite while drafting.")
    no2 = org.feedback(ROOT, second.id, "reject", "Still too long.", source="human")
    for task, no in ((first, no1), (second, no2)):  # the user's yes: a criterion on the rejection itself would be the assistant's reading
        org.feedback(ROOT, task.id, "reject", "Yes, it is about C1.", source="human", criterion=["C1"], confirms=no.id)
    clock.tick()
    org.revise_playbook("ceo", "weekly-brief", PLAYBOOK + "4. Cut to 600 words before reporting [C1].\n", "Client rejected: too long.", ["C1"])
    clock.tick()
    out = []
    for name in ("weekly-brief", "plain-brief"):
        for f in ("SERVICE.md", "PLAYBOOK.md"):
            p = org.dir("ceo") / "services" / name / f
            out.append(f"##### ceo/services/{name}/{f}\n" + (norm(p.read_text(encoding="utf-8")) if p.exists() else "(missing)\n"))
    check("services/service_and_playbook_files.md", "\n".join(out))
    check("services/services_text_root.txt", norm(org.runtime.service_reports.services_text(ROOT)))
