"""The texts of the server: the instructions it sends on every connection, and what a root server says before an organization exists.

The wording is part of the contract (golden): ``ROOT_INSTRUCTIONS`` is sent on every connection and stays under 2700 characters.
"""

from __future__ import annotations

from ..kernel import ROOT
from .api import OrgBindingPort
from ._ports import ServerInstructions, SetupMode

INSTRUCTIONS = """\
You are a member of a file-based organization of agents. Your identity is fixed by the runtime.
Work flows down as tasks (delegate), results flow up (report), everything else is a note (send).
Call whoami first if you do not know your role, reports, budget and open tasks.
"""

ROOT_INSTRUCTIONS = """\
You are connected to ONE hirearchy organization as `root`, the human's seat. {where}
- Use only this organization: never look for, create or modify another (no other paths or ORG_ROOT).
- Never claim the org did work unless hirearchy tools show it; if a tool fails, tell the user instead of substituting.
- Before you build an org or rate a delivery, activate the hirearchy skill.
- `whoami` and `status` show the state; `start`/`stop` control the scheduler. `observe` (read-only): what ran or failed.
- Services: `services` (check it before building a new org), `request`, `feedback` (rate a delivery), `define_service`.
  On a reject: `feedback` first, then ONE yes/no question naming an id, then the change (`define_service(answers=...)`).
  `quality`: how the work went.
When the user asks for an org, team or agents for a goal:
1. Ask what you need in ONE message. Propose defaults only where a generic one exists; ASK for any list not
   given, never invent. Default deliverable place: a new `deliverables/` folder here (say so). Also ask: format,
   length, exact checkable criteria, sources/web, workspace and tests (code), budget in runs,
   models (all claude-sonnet-5.5 at high effort; nothing below is available), review, approval.
2. Start the blueprint from `blueprint_example(kind)` (`service=True` for recurring work), then `propose_org`. Show the
   "PLAN FOR YOU" block exactly as returned. Fix errors; settle its warnings (e.g. model policy) with the user
   or state them; wait for approval. The user's own files go in `needs.inputs` (read-only);
   built-in `write` only for code.
3. After approval: `create_org` (if none exists), `apply_org(blueprint, approved=True, plan_id=<from propose_org>)`,
   `start`. Spend beyond the plan needs their OK: ask at the FIRST budget request, not after the reserve is gone;
   first check `status` for stranded runs and `reclaim` them.
4. Answer "status?" with `progress`. Never promise to tell the user later (your turn ends at the reply): to be told when
   it is done, say you will wait now and call `progress(wait_seconds=N)`, repeat if asked; else tell them to ask
   "status?". Relay escalations with a recommendation.
5. When it is done: read the deliverable, check it against EVERY acceptance criterion (send it back with
   `request`/`delegate(..., revises=...)` if not; never patch it yourself), copy it where they want it. `start` ends by
   itself when the work is done; `stop` only if the user cancels, declines more budget or you hand over an
   unverified result (say the task stays open). Final answer: as short as asked.
"""

DS_STORE = ".DS_Store"  # macOS Finder litter does not make a directory "not empty" for create_org


class InstructionText(ServerInstructions, SetupMode):
    """The instructions of a server for an identity, and the setup state, both read from the binding."""

    def __init__(self, binding: OrgBindingPort) -> None:
        self._binding = binding

    def for_identity(self, me: str) -> str:
        return self._for_root() if me == ROOT else INSTRUCTIONS

    def _for_root(self) -> str:
        located, root = self._binding.location(), self._binding.root
        if located is not None:
            where = f"The organization is at {located}."
        elif root is not None:
            where = (f"No organization exists at {root} yet: the first step is create_org(mission=...), "
                     "after which all tools work.")
        else:
            where = ("No organization exists and none is bound: the first step is create_org(mission=..., "
                     "path=<absolute path>), after which all tools work.")
        return ROOT_INSTRUCTIONS.format(where=where)

    def active(self) -> bool:
        return self._binding.peek() is None

    def state(self) -> str:
        root = self._binding.root
        where = f"at {root}" if root is not None else "(none found: ORG_ROOT is not set)"
        path_arg = "" if root is not None else ", path=<absolute path>"
        return (f"Setup: no organization exists {where} yet.\n"
                f"Next step: call create_org(mission=\"...\"{path_arg}) to create it; then propose_org and apply_org "
                "a plan, and start() the scheduler. Until then every other tool returns an error.\n"
                "scheduler: stopped")
