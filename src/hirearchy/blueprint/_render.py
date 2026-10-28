"""``TextPlanRenderer``: the plan as text - the block for the user, the details, and what ``propose_org`` returns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._plan_texts import PLAN_END, PLAN_SHOW
from ._protocols import ExtensionPlanning, PlanBasis, PlanDetailing, UserPlanning
from .api import BlueprintLoader, Issue, PlanIdentity, PlanRenderer, errors, is_extension

NEXT_EXTENSION = (
    "plan_id: {pid}\nNext: show the PLAN FOR YOU block above to the user exactly as written (a plain-words intro line before it is fine) and wait for "
    "their explicit approval. Then apply_org(blueprint=<this exact YAML>, approved=True, plan_id=\"{pid}\"). If you change the blueprint, or anything "
    "it names changes in the organization, call propose_org(blueprint, extend=\"current\") again: the plan_id changes."
)


class TextPlanRenderer(PlanRenderer):
    def __init__(
        self, loader: BlueprintLoader, basis: PlanBasis, details: PlanDetailing, user_plan: UserPlanning, identity: PlanIdentity,
        extensions: ExtensionPlanning | None = None,
    ) -> None:
        self._loader = loader
        self._basis = basis
        self._details = details
        self._user_plan = user_plan
        self._identity = identity
        self._extensions = extensions

    def render_plan(self, bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        """The plan the user approves: goal, needs, org tree, budget, review, deliverable, checkpoints, warnings. An extension of the organization
        (design 5.3): its block, then its details."""
        if self._extensions is not None and is_extension(bp):
            text = self._extensions.plan(bp, allowed_roots=allowed_roots)
            return text.block + "\n\n" + text.details
        return self._details.render(bp, issues, allowed_roots)

    def plan_for_user(self, bp: Mapping[str, object], issues: Sequence[Issue] | None = None, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        """The compact, plain-language plan the assistant shows to the user verbatim (about 40 lines at most)."""
        if self._extensions is not None and is_extension(bp):
            return self._extensions.plan(bp, allowed_roots=allowed_roots).block
        return self._user_plan.render(bp, issues, allowed_roots)

    def propose_text(
        self, bp: Mapping[str, object], *, target: str = "", allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False,
    ) -> str:
        """What ``propose_org`` returns: the block for the user, the full details and the plan_id."""
        if self._extensions is not None and is_extension(bp):
            text = self._extensions.plan(bp, allowed_roots=allowed_roots, require_sources=require_sources)
            failed = bool(errors(text.issues))
            nxt = ("plan_id: none (the blueprint has errors). Fix them and call propose_org again; do not ask the user to approve this." if failed
                   else NEXT_EXTENSION.format(pid=self._identity.plan_id(bp)))
            parts = (target, "" if failed else PLAN_SHOW, text.block, PLAN_END, "Details (the full plan, for you; the user need not read it):\n" + text.details, nxt)
            return "\n\n".join(x for x in parts if x)
        issues = self._basis.issues(bp, allowed_roots, require_sources)
        block = self.plan_for_user(bp, issues, allowed_roots=allowed_roots)
        details = self.render_plan(bp, issues, allowed_roots=allowed_roots)
        if errors(issues):
            nxt = "plan_id: none (the blueprint has errors). Fix them and call propose_org again; do not ask the user to approve this."
        else:
            pid = self._identity.plan_id(bp)
            nxt = (f"plan_id: {pid}\nNext: show the PLAN FOR YOU block above to the user exactly as written (a plain-words intro line "
                   f"before it is fine) and wait for their explicit approval. Then apply_org(blueprint=<this exact YAML>, "
                   f"approved=True, plan_id=\"{pid}\"). If you change the blueprint, call propose_org again: the plan_id changes.")
        show = "" if errors(issues) else PLAN_SHOW
        return "\n\n".join(x for x in (target, show, block, PLAN_END, "Details (the full plan, for you; the user need not read it):\n" + details, nxt) if x)

    def propose(self, source: object, *, allowed_roots: Sequence[str | Path] | None = None) -> str:
        """Load a blueprint (text, path or dict), validate it and return the plan text. Writes nothing."""
        bp = self._loader.load(source)
        return self.render_plan(bp, self._basis.issues(bp, allowed_roots), allowed_roots=allowed_roots)
