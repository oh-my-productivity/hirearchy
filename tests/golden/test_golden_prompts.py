"""Golden: the run prompt (``Org.run_prompt``) every agent gets. Byte-identical across the refactor."""

from golden_support import check
from scenarios import BRIEF, PLAYBOOK, company, deliver_service, dirs, run, write_artifact

from hirearchy.core import ROOT


def test_prompt_plain_worker(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    org.delegate(ROOT, "ceo", "Plan the launch", "Make a launch plan.", "plan.md exists", [], 6)
    clock.tick()
    org.delegate("ceo", "ceo/eng", "Build the API", "Implement the API.", "tests pass", ["ceo/work/plan.md"], 3)
    clock.tick()
    org.write("ceo/eng", "ceo/eng/MEMORY.md", "Last run: read the repo layout.\n")
    batch = run(org, "ceo/eng", clock)
    check("prompts/plain_worker.txt", norm(org.run_prompt("ceo/eng", batch)))


def test_prompt_manager_with_reports_and_open_tasks(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    org.delegate(ROOT, "ceo", "Plan the launch", "Make a launch plan.", "plan.md exists\nlaunch date named", [], 8)
    clock.tick()
    run(org, "ceo", clock)  # the first run: the ceo reads the task and delegates it to eng
    org.end_run("ceo", ok=True)
    org.delegate("ceo", "ceo/eng", "Draft the plan", "Draft plan.md.", "plan.md exists", [], 3)
    clock.tick()
    org.delegate("ceo", "ceo/qa", "Review the plan", "Review plan.md for gaps.", "gaps listed", [], 2)
    clock.tick()
    # eng answers; qa has not: the ceo's next batch holds eng's result and a note from root
    org.begin_run("ceo/eng")
    write_artifact(org, "ceo/eng", "ceo/eng/work/plan.md", "# Plan\n", clock)
    eng_task = next(m for m in org.received("ceo/eng") if m.type == "task")
    org.report("ceo/eng", eng_task.id, "done", "Plan drafted.", ["ceo/eng/work/plan.md"])
    org.end_run("ceo/eng", ok=True)
    clock.tick()
    org.send(ROOT, "ceo", "Please keep it under one page.", title="Constraint")
    clock.tick()
    batch = run(org, "ceo", clock)
    check("prompts/manager_with_reports.txt", norm(org.run_prompt("ceo", batch)))


def test_prompt_agent_with_builtin_read_write_shell(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    ws, inputs = dirs(tmp_path)
    norm.add(ws, "<WS>")
    norm.add(inputs, "<INPUTS>")
    org.hire(ROOT, "dev", "Developer", "Write code in the workspace.", tools=["read", "write", "shell"],
             workspace=str(ws), inputs=[str(inputs)])
    clock.tick()
    org.delegate(ROOT, "dev", "Fix the bug", "Fix the parser bug.", "tests pass", [], 4)
    clock.tick()
    batch = run(org, "dev", clock)
    check("prompts/builtin_read_write_shell.txt", norm(org.run_prompt("dev", batch)))


def test_prompt_service_owner_with_playbook_and_reflect_section(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    org.define_service(ROOT, "ceo", "weekly-brief", playbook=PLAYBOOK, notes="Mind the sources.", **BRIEF)
    clock.tick()
    first = org.request(ROOT, "weekly-brief", {"topic": "ai chips"}, title="Brief on AI chips")
    clock.tick()
    deliver_service(org, "ceo", first, clock, lessons="The fact-check found two uncited claims; cite while drafting.")
    org.feedback(ROOT, first.id, "reject", "Too long: cut to 600 words.")
    clock.tick()
    org.request(ROOT, "weekly-brief", {"topic": "ai chips", "week": "2026-W03"}, title="Brief on AI chips", note="Shorter please.",
                revises=first.id, budget=6)
    clock.tick()
    batch = run(org, "ceo", clock)
    check("prompts/service_owner_reflect.txt", norm(org.run_prompt("ceo", batch)))


def test_prompt_service_owner_without_playbook(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    org.define_service(ROOT, "ceo", "weekly-brief", **BRIEF)
    clock.tick()
    org.request(ROOT, "weekly-brief", {"topic": "batteries"})
    clock.tick()
    batch = run(org, "ceo", clock)
    check("prompts/service_owner_no_playbook.txt", norm(org.run_prompt("ceo", batch)))


def test_prompt_agent_with_oversized_memory(tmp_path, clock, norm):
    org = company(tmp_path, clock, config={"memory_max_words": 30})
    org.delegate(ROOT, "ceo", "Plan the launch", "Make a launch plan.", "plan.md exists", [], 6)
    clock.tick()
    org.delegate("ceo", "ceo/eng", "Build the API", "Implement the API.", "tests pass", [], 3)
    clock.tick()
    memory = " ".join(f"note{i}" for i in range(45)) + "\n"
    (org.dir("ceo/eng") / "MEMORY.md").write_text(memory, encoding="utf-8")  # past the cap: writes would be refused
    batch = run(org, "ceo/eng", clock)
    check("prompts/oversized_memory.txt", norm(org.run_prompt("ceo/eng", batch)))


def test_prompt_with_a_stray_file_notice(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    ws, _ = dirs(tmp_path)
    norm.add(ws, "<WS>")
    org.hire(ROOT, "dev", "Developer", "Write code.", tools=["write"], workspace=str(ws))
    clock.tick()
    org.delegate(ROOT, "dev", "Fix the bug", "Fix it.", "tests pass", [], 4)
    clock.tick()
    org.save_ledger("strays", {"dev": {"paths": [str(ws / "MEMORY.md"), str(ws / "dev" / "work")], "told": False}})
    batch = run(org, "dev", clock)
    first = org.run_prompt("dev", batch)
    check("prompts/stray_notice.txt", norm(first))
    assert "Notice from the runtime" not in org.run_prompt("dev", batch)  # told once


FILES_VARIANTS = {
    "shell_only": dict(tools=["shell"]),
    "read_only": dict(tools=["read"]),
    "write_only": dict(tools=["write"]),
    "read_write": dict(tools=["read", "write"]),
    "workspace_no_tools": dict(tools=[]),
}


def test_state_files_block_per_tool_shape(tmp_path, clock, norm):
    """The state of an agent (it embeds the "Files" part), for every combination of built-in tools."""
    org = company(tmp_path, clock)
    ws, inputs = dirs(tmp_path)
    norm.add(ws, "<WS>")
    norm.add(inputs, "<INPUTS>")
    out = []
    for label, kw in FILES_VARIANTS.items():
        org.hire(ROOT, label.replace("_", "-"), "Worker", "Work.", workspace=str(ws), inputs=[str(inputs)], **kw)
        clock.tick()
        addr = label.replace("_", "-")
        out.append(f"### {label} ({addr})\n" + org.state_summary(addr) + "\n")
    org.hire(ROOT, "bare", "Bare", "No tools, no workspace.")
    out.append("### bare\n" + org.state_summary("bare") + "\n")
    check("prompts/files_block_variants.txt", norm("\n".join(out)))
