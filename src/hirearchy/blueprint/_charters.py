"""``CharterWriter``: the charter of an agent of a blueprint - its template, then the assignment from the approved plan, then what the blueprint adds."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ._protocols import Charters
from ._rules import is_code
from ._shapes import Split
from ._view import deliverable_of, has_plain_task, mapping_or_empty, needs_of, s, services_of
from .api import Agent


class CharterWriter(Charters):
    def charter(self, a: Agent, agents: Sequence[Agent], bp: Mapping[str, object], split: Mapping[str, Split]) -> str:
        by = {x.addr: x for x in agents}
        needs, d = needs_of(bp), deliverable_of(bp)
        offers = [s(x.get("name")) for x in services_of(bp)] if a.parent is None else []
        parts = [a.template.body] if a.template else []
        asg = ["## Assignment (from the approved plan)", f"Mission: {s(bp.get('mission'))}"]
        if d.get("description"):
            spec = ", ".join(x for x in (s(d.get("format")), f"at most {d['max_words']} words" if d.get("max_words") else "") if x)
            asg.append(f"Deliverable: {s(d['description'])}" + (f" ({spec})" if spec else ""))
        if a.parent is None and d.get("path"):
            asg.append(f"The assistant copies the final artifact to {s(d['path'])} after you report; name the artifact's path in your report.")
        if s(needs.get("quality_bar")):
            asg.append(f"Quality bar: {s(needs['quality_bar'])}")
        if s(needs.get("scope")):
            asg.append(f"Scope: {s(needs['scope'])}")
        if a.workspace:
            asg.append(f"Workspace: {a.workspace}. Everything you read, write or run outside hirearchy stays inside it; nothing else on the machine, and nothing under ~/.kiro or the organization directory. Relative paths in kiro tools resolve there; your org files (MEMORY.md, work/) are written with hirearchy `write`, never into the workspace.")
        if a.inputs:
            asg.append(f"Read-only inputs: {', '.join(a.inputs)}. Read them (kiro `read`, or hirearchy `read` by absolute path); never create, edit or delete anything there.")
        if "shell" in a.tools:
            asg.append("shell is not confined by the runtime: keep every command inside your workspace, and never write to the inputs, the organization directory or anywhere else.")
        code = mapping_or_empty(needs.get("code"))
        if is_code(bp) and a.kind != "manager" and code:
            asg.append("Engineering rules: " + "; ".join(f"{k}: {s(v)}" for k, v in code.items() if s(v)))
        asg.append(f"Reports to: {a.parent or 'root (the human)'}")
        if a.children:
            asg.append("Your team (fixed by the plan; you cannot change it):")
            for c in a.children:
                k = by[c]
                asg.append(f"- {c}: {k.role} ({k.kind}; tools: {', '.join(k.tools) or 'none'}; model: {k.model})")
            grants = [(c, split[c]["grant"]) for c in a.children]
            if offers and not has_plain_task(bp):
                asg.append("Budget plan: each request arrives with the budget of its service, and its split between you and your team is in the playbook (`## Budget plan`). "
                           "Hand down no more than that plan says, with `budget=` set explicitly; keep the reserve for one review and rework cycle. "
                           "Runs you do not spend return to your parent automatically with your final report.")
            else:
                asg.append(
                    f"Budget plan: you start with {split[a.addr]['grant']} runs. Initial grants, set explicitly with `budget=`: "
                    + ", ".join(f"{c} {n}" for c, n in grants) + f". Each grant already includes that worker's one rework (author) or re-check (verifier) run. You keep {split[a.addr]['keeps']} runs: your own runs plus the reserve for "
                    "one review and one rework cycle (rework tasks hand down 1-2 runs each). Do not hand down more than this up front. Runs you do not spend return to your parent automatically with your final report.")
            vs = [c for c in a.children if by[c].kind == "verifier"]
            if vs:
                au = [c for c in a.children if by[c].kind == "author"]
                asg.append(f"Review loop: {', '.join(au) or 'the authors'} produce; {', '.join(vs)} verif{'ies' if len(vs) == 1 else 'y'} independently and report findings and required changes to you; "
                           "you send them to the author with `revises`; verifiers never edit the author's file.")
        if offers:
            asg.append(
                f"Services you offer: {', '.join(offers)} (the runtime shows them, with their contract, in your prompt). A task with a `service:` "
                "header is a request for one: for it the playbook shown in your prompt is the procedure (steps, who does what, budget plan), "
                "and wherever this charter's general procedure differs, the playbook wins. You own the playbook and improve it with `revise_playbook` "
                "when the client's evidence calls for it (ORG.md rule 10). The acceptance criteria come from the request and the contract; improving the playbook "
                "may raise the bar, never lower it.")
        parts.append("\n".join(asg))
        if a.extra:
            parts.append(("## Additional instructions\n" if a.template else "") + a.extra)
        return "\n\n".join(parts)

    def extension_charter(self, a: Agent, team: Sequence[Agent], plan_id: str, extra: str) -> str:
        """Its template (or the charter text the entry gave), then the assignment from the user's change, then the additional instructions."""
        parts = [a.template.body if a.template else a.extra]
        asg = [f"## Assignment (from the user's change {plan_id})", f"Reports to: {a.parent or 'root (the human)'}"]
        if a.workspace:
            asg.append(f"Workspace: {a.workspace}. Everything you read, write or run outside hirearchy stays inside it; nothing else on the machine, and nothing under ~/.kiro or the organization directory. Relative paths in kiro tools resolve there; your org files (MEMORY.md, work/) are written with hirearchy `write`, never into the workspace.")
        if a.inputs:
            asg.append(f"Read-only inputs: {', '.join(a.inputs)}. Read them (kiro `read`, or hirearchy `read` by absolute path); never create, edit or delete anything there.")
        if "shell" in a.tools:
            asg.append("shell is not confined by the runtime: keep every command inside your workspace, and never write to the inputs, the organization directory or anywhere else.")
        if a.children:
            asg.append("Your team (fixed by the change; you cannot change it):")
            by = {x.addr: x for x in team}
            asg += [f"- {c}: {by[c].role} ({by[c].kind}; tools: {', '.join(by[c].tools) or 'none'}; model: {by[c].model})" for c in a.children if c in by]
        parts.append("\n".join(asg))
        if extra.strip():
            parts.append("## Additional instructions\n" + extra.strip())
        return "\n\n".join(p for p in parts if p)
