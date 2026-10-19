# mypy: ignore-errors
"""The texts an agent is shown: whoami, state summary, run prompt (prompts).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from ..kernel import latest_results, Message, ROOT


class PromptsMixin:
    """The texts an agent is shown: whoami, state summary, run prompt (prompts)."""

    def _agent_line(self, addr: str) -> str:
        meta, _ = self.charter(addr)
        return (
            f"{addr} [{meta.get('role', '?')}] {self.state(addr)}, budget {self.budget(addr)}, "
            f"open tasks {len(self.open_tasks(addr))}, delegated {len(self.outstanding(addr))}, unread {self.unread(addr)}"
        )

    @staticmethod
    def _indent(text: str, n: int) -> str:
        return "\n".join(" " * n + line for line in text.splitlines())

    def _quote(self, m: Message) -> str:
        """Quote a task's body verbatim, so its own headings do not mix with the prompt's structure.

        A very long body is cut like ``Message.render`` does, with the real path of the file to read the rest."""
        where = str(m.path.relative_to(self.root)) if m.path and m.path.is_relative_to(self.root) else None
        return "\n".join(f"> {line}".rstrip() for line in m.cut_body(where=where).strip().splitlines())

    def state_summary(self, addr: str, shown: set[str] | None = None) -> str:
        """The agent's situation. ``shown``: ids of tasks whose full text the caller already prints elsewhere."""
        a = self.require(addr)
        meta, _ = self.charter(a)
        lines = [f"- Address: `{a}`; parent: `{self.parent(a) or '-'}`; role: {meta.get('role', '?')}"]
        if a != ROOT:
            hiring = (
                f"allowed ({len(self.children(a))}/{meta.get('max_children', 5)} reports)"
                if meta.get("can_hire") else "not allowed"
            )
            tools = ", ".join(meta.get("tools") or []) or "none"
            lines.append(f"- Budget: {self.budget(a)} run(s) left (this run already counted). Hiring: {hiring}")
            lines.append(f"- Tools beyond orgmcp: {tools}" + (f"; workspace: {meta['workspace']}" if meta.get("workspace") else ""))
            lines += self._files_lines(a, meta)
        kids = self.children(a)
        lines.append("- Direct reports:" + ("" if kids else " none"))
        lines += [f"  - {self._agent_line(k)}" for k in kids]
        siblings = [s for s in self.children(self.parent(a)) if s != a] if a != ROOT else []
        if siblings:
            lines.append("- Siblings: " + ", ".join(siblings))
        tasks = self.open_tasks(a)
        lines.append("- Open tasks assigned to you:" + ("" if tasks else " none"))
        for t in tasks:
            lines.append(f"  - {t.id} \"{t.title}\" from {t.sender}")
            if t.id in (shown or ()):
                lines.append("    (full text: see the new messages below)")
            else:  # the contract you are accountable for, verbatim
                lines.append(self._indent(self._quote(t), 4))
        blocked = self._blocked_tasks(a)
        if blocked:
            lines.append("- Tasks you reported blocked (not final):")
            for t in blocked:
                lines.append(
                    f"  - {t.id} \"{t.title}\" from {t.sender}: reported blocked; "
                    "you may re-report it once the blocker is resolved"
                )
                if t.id in (shown or ()):
                    lines.append("    (full text: see the new messages below)")
                else:
                    lines.append(self._indent(self._quote(t), 4))
        out = self.outstanding(a)
        lines.append("- Work you delegated that is still outstanding:" + ("" if out else " none"))
        lines += [f"  - {t.id} \"{t.title}\" -> {t.to} ({self.state(t.to) if self.exists(t.to) else 'gone'})" for t in out]
        return "\n".join(lines)

    def _files_lines(self, addr: str, meta: dict) -> list[str]:
        """The "Files" part of an agent's state: where each kind of path points, and which tool reaches it.

        The orgmcp tools show up in kiro as ``@orgmcp/<tool>``; kiro's built-in ``read``/``write``/``shell`` reach the
        workspace (``read`` also the org, by absolute path). A built-in ``read``/``write`` hides the orgmcp tool of the
        same name, which is then called ``org_read``/``org_write`` (see :meth:`tool_names`): the agent is told which
        name it has. Empty for an agent with no workspace, no inputs and no built-in tools.
        """
        ws, inputs = self.workspace_of(addr), self.inputs_of(addr)
        tools = set(meta.get("tools") or [])
        builtin = sorted(tools & {"read", "write", "shell"})
        if ws is None and not inputs and not builtin:
            return []
        names = self.tool_names(addr)
        rn, wn = names["read"], names["write"]
        lines = [
            "- Files:",
            f"  - orgmcp tools (shown as `@orgmcp/{wn}`, `@orgmcp/{rn}`, ...): paths are relative to the org root; your "
            f"notes and memory: `{addr}/MEMORY.md`, `{addr}/work/` (orgmcp `{wn}` only).",
        ]
        if builtin:
            kinds = ", ".join(f"`{t}`" for t in builtin)
            if not tools & {"read", "write"}:  # only `shell`: no name clash
                reach = "they work on the workspace only and never reach the org. "
                how = "`@orgmcp/write` and read with `@orgmcp/read`, never with the built-in `write`/`read`."
                intro = "have the same short names as orgmcp's but are not the same tools"
            else:
                reach = (
                    "they write and run only in the workspace and never change the org. " if "read" in tools
                    else "they work on the workspace only and never reach the org. "
                )
                intro = "are not orgmcp's tools"
                if "write" in tools:
                    how = (
                        f"`@orgmcp/{wn}`, never with the built-in `write`: kiro's built-in `write` has the name `write`; "
                        f"the orgmcp write tool is `@orgmcp/{wn}` for you: use it for MEMORY.md and org files "
                        "(wherever ORG.md says `@orgmcp/write`, use that name)."
                    )
                else:
                    how = "`@orgmcp/write`, never with the built-in `write`."
                if "read" in tools:
                    how += (
                        " Your `read` is kiro's built-in: it reads org files too, but only by ABSOLUTE path, "
                        f"`{self.root}/<path in the org>` (a relative path starts in your working directory); the orgmcp "
                        f"read tool is `@orgmcp/{rn}` for you (relative org paths; wherever ORG.md says `@orgmcp/read`, "
                        "use that name)."
                    )
                else:
                    how += " Read org files with `@orgmcp/read`."
            lines.append(
                f"  - Do not mix up the two kinds of tools: kiro's built-in {kinds} {intro}: {reach}"
                f"Org files (`{addr}/MEMORY.md`, `{addr}/work/`, anything under `{addr}/`) are written with " + how
            )
        if ws is not None:
            lines.append(
                f"  - Workspace (kiro read/write/shell, and the working directory of kiro tools): `{ws}`; relative "
                "paths in kiro tools resolve there."
            )
        else:
            lines.append(f"  - You have no workspace: kiro tools start in your org directory (`{addr}/`) and cannot write.")
        if inputs:
            lines.append(
                f"  - Read-only inputs (kiro `read` or orgmcp `{rn}` by absolute path): "
                + ", ".join(f"`{p}`" for p in inputs) + ". Never modify them."
            )
        lines.append(
            "  - Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by "
            "absolute path."
        )
        if tools & {"read", "write"}:
            lines.append("  - kiro `write` is limited to the workspace and kiro `read` to workspace + inputs + the organization (read-only); other paths are refused.")
        if "shell" in tools:
            lines.append(
                "  - You have `shell`, which the runtime cannot confine: use it only inside your workspace; never write "
                "to inputs, to the org directory, or anywhere else."
            )
        return lines

    def whoami(self, addr: str) -> str:
        a = self.require(addr)
        _, charter = self.charter(a)
        return f"{self.state_summary(a)}\n\n## Charter\n{charter or '(root has no charter)'}"

    def _render_in_context(self, addr: str, m: Message) -> str:
        """A batch message; a result is followed by the task it answers, so it is judged against what was asked."""
        text = m.render()
        if m.type != "result" or not m.reply_to:
            return text
        task = next((t for t in self.sent(addr) if t.type == "task" and t.id == m.reply_to), None)
        if task is None:
            return text
        out = (
            f"{text}\n[The task you delegated to {task.to} that this result answers ({task.id}). "
            f"Judge the result against these criteria, verbatim:]\n{self._quote(task)}\n"
        )
        # Which of your own tasks does it serve? Derivable only if exactly one was already yours at the time.
        up = self._upstream(addr, task)
        if up is not None:
            mine, reported = up
            if reported is None:
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your open task "
                    f"{mine.id} \"{mine.title}\": the result must also satisfy that task's criteria (shown in full in this prompt).]\n"
                )
            elif reported.status == "blocked":
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your task "
                    f"{mine.id} \"{mine.title}\", which you already reported blocked. That is not final: you may `report` "
                    "it again, once, if the blocker is resolved (its criteria are shown in your state). The new report must meet "
                    "rule 6: `done` only if every criterion is met and verified by you, including any required review of "
                    "the FINAL version, not an earlier draft; otherwise report `blocked` or `failed`. Do not claim in a note "
                    "that criteria are met.]\n"
                )
            else:
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your task "
                    f"{mine.id} \"{mine.title}\", which you already reported {reported.status}: that is final. Do not claim "
                    "in a note that its criteria are met or try to change its outcome; if you have information for "
                    f"{mine.sender}, send it as information only, saying what was and was not verified.]\n"
                )
        return out

    def _upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        """The one task of ``addr`` that a delegation probably serves, with its latest result (None = still open).

        A candidate was assigned before the delegation and is open, reported ``blocked`` or was reported only after
        the delegation. None when there is not exactly one candidate.
        """
        latest = latest_results(self.sent(addr))
        found = [
            (t, latest.get(t.id)) for t in self.received(addr)
            if t.type == "task" and t.id < delegated.id
            and ((r := latest.get(t.id)) is None or r.status == "blocked" or r.id > delegated.id)
        ]
        return found[0] if len(found) == 1 else None

    def run_prompt(self, addr: str, batch: list[Message]) -> str:
        a = self.require(addr)
        _, charter = self.charter(a)
        memory = self.memory(a).strip() or "(empty: this may be your first run)"
        cap, words = int(self.config["memory_max_words"]), len(memory.split())
        if words > cap:
            memory += (
                f"\n\n**Your memory is {words} words, over the {cap}-word limit, and writes that keep it over "
                f"the limit are refused. This run, condense it: rewrite {a}/MEMORY.md (not append) with only what "
                "your next run needs; move detail into files under your work/ directory.**"
            )
        messages = "\n".join(self._render_in_context(a, m) for m in batch) or "(none)"
        shown = {m.id for m in batch if m.type == "task"}
        wn = self.tool_names(a)["write"]
        notice = self.stray_notice(a)
        notice = f"\n{notice}\n" if notice else ""
        if self.service_names(a):  # only agents that offer a service get these sections
            notice += self.runtime.service_prompt_sections.prompt_sections(a, batch)
        return f"""# orgmcp run: you are `{a}`

{self.rules()}

# Your charter ({a}/AGENT.md, owned by your parent)
{charter}

# Your memory ({a}/MEMORY.md)
{memory}

# Your state
{self.state_summary(a, shown)}
- Paths: every path (read, write, artifacts) is relative to the org root. Yours start with `{a}/`.
{notice}
# New messages for this run ({len(batch)})
{messages}
---
Handle every new message above with the orgmcp tools, following the protocol.
Messages may be redelivered after a crash: if your state shows one was already handled, skip it.
Before you stop, update your memory with `@orgmcp/{wn}`(path="{a}/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`). Do not wait for replies; end the run when done.
"""
