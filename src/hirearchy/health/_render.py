"""``TextHealthRenderer``: the human report of an organization's health."""

from __future__ import annotations

from ..kernel import fmt_duration
from .api import AgentHealth, HealthRenderer, OrgHealth


def _escapes(h: AgentHealth, causes: bool) -> str:
    """The escapes segment. Root's reading (``causes``) adds the escapes that are not the verifier's, by cause, and the services it could not type."""
    text = f"escapes {h.escapes} of {h.judged} judged"
    if causes:
        listed = [(cause, n) for cause, n in h.not_its.items() if n > 0]
        if listed:
            text += f" (+{sum(n for _, n in listed)} not its: {', '.join(f'{n} {cause}' for cause, n in listed)})"
        if h.causes_unknown:
            text += f"; causes unknown ({h.causes_unknown})"
    return f"{text}, re-checks after a FAIL {h.rechecks} (author rework runs {h.rework_runs})"


class TextHealthRenderer(HealthRenderer):
    def render_text(self, health: OrgHealth, *, causes: bool = False) -> str:
        n, bad = len(health.agents), len(health.flagged)
        lines = [f"{n} agent{'s' * (n != 1)}, {bad} flagged"]
        base = min((h.depth for h in health.agents), default=0)
        for h in health.agents:
            left = "unlimited" if h.budget_left is None else h.budget_left
            parts = [
                f"{h.addr.rsplit('/', 1)[-1]} {h.state}",
                f"budget {left}/{h.budget_received}",
                f"runs {h.runs_used}",
                f"open {h.open_tasks}" + (f" (oldest {fmt_duration(h.oldest_open_age)})" if h.oldest_open_age is not None else ""),
                f"done {h.done} failed {h.failed} blocked {h.blocked} rework {h.rework}"
                + (f" (+{h.client_rework} by the client)" if h.client_rework else ""),
                *([_escapes(h, causes)] if h.judged else []),
                "runs/task " + ("-" if h.runs_per_task is None else f"{h.runs_per_task:.1f}"),
                f"empty {h.empty_runs}" + (f" (+{h.failed_runs} failed)" if h.failed_runs else ""),
                "last activity " + ("never" if h.since_activity is None else f"{fmt_duration(h.since_activity)} ago"),
            ]
            line = "  " * (h.depth - base) + ", ".join(parts)
            branch = health.branches[h.addr]
            if branch.agents > 1:
                line += (
                    f" | branch: runs {branch.runs_used}, open {branch.open_tasks}, done {branch.done}, "
                    f"failed {branch.failed}, blocked {branch.blocked}, rework {branch.rework}, "
                    f"worst {branch.worst_flag or 'none'}"
                )
            if h.flags:
                line += " | " + "; ".join(f"!{flag}: {why}" for flag, why in h.flags.items())
            lines.append(line)
        return "\n".join(lines)
