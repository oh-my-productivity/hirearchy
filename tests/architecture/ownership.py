"""On-disk ownership (ARCHITECTURE.md 2.3): every file or directory of an organization has exactly ONE writing package.

Machine-readable form of the 2.3 table, read by ``checks.single_writer_violations`` (test ``test_single_writer``): a package
other than the owner that mentions one of the ``fragments`` of a row inside a write call fails the test. ``test_ownership_matches_
document`` keeps this file and the document in step.

"Write call" = ``write_text write_bytes open(.., "w"/"a"/"x"/"+") atomic_write replace rename move mkdir touch unlink rmdir rmtree
write`` (see ``checks.WRITE_CALLS``). A fragment is matched against string constants in the call (receiver and arguments) and in
variables assigned from such constants inside the same function: as a whole path segment ("ORG.md", "inbox") or, for fragments
with a "/" or a ".", as a substring (".runtime/failures.json").

The kernel's file adapters (AtomicWriter, LedgerStore) write temp files and ledgers *on behalf of* the owners, so ``kernel`` and the
composition root ``app`` are never blamed. Ledger names (``kernel.LedgerStore``) are a closed registry, see ``LEDGERS``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Owned:
    path: str  # the 2.3 "Path" cell, for humans and for the document test
    owner: str  # the only writer
    fragments: tuple[str, ...]  # literal path fragments that identify the path in code


OWNERS: tuple[Owned, ...] = (
    Owned("ORG.md", "settings", ("ORG.md",)),
    Owned(".git/, .gitignore", "snapshots", (".git", ".gitignore")),
    Owned("<addr>/{inbox,inflight,read,sent}/*.md, root's own boxes", "mail", ("inbox", "inflight", "read", "sent")),
    Owned("<addr>/AGENT.md, agent directory skeleton, .retired/**", "agents", ("AGENT.md", ".retired")),
    Owned("<addr>/MEMORY.md (after creation), <addr>/work/**", "orgfiles", ("MEMORY.md", "work")),
    Owned("<addr>/runs/*.log", "runs", ("runs",)),
    Owned("<addr>/.paused", "eligibility", (".paused",)),
    Owned("<owner>/services/**", "services", ("services",)),
    Owned(".runtime/failures.json", "eligibility", ("failures.json",)),
    Owned(".runtime/running.json", "runs", ("running.json",)),
    Owned(".runtime/nudges.json", "stalls", ("nudges.json",)),
    Owned(".runtime/strays.json", "strays", ("strays.json",)),
    Owned(".runtime/reviews.json", "review", ("reviews.json",)),
    Owned(".runtime/scheduler.pid", "daemon", ("scheduler.pid",)),
    Owned(".runtime/scheduler.exit, .runtime/scheduler.log", "daemon", ("scheduler.exit", "scheduler.log")),
    Owned(".runtime/events/<day>/*.jsonl", "telemetry", ("events",)),
    Owned("~/.kiro/agents/hirearchy-*.json", "kiro", (".kiro/agents", "hirearchy-")),
    Owned("~/.kiro/skills/hirearchy/SKILL.md", "skill", (".kiro/skills",)),
)
# "workspace directories created for a plan" (blueprint) has no literal fragment: the paths come from the blueprint.

# Creator exceptions (2.3): directories and empty files, never content. package -> (fragments it may create, operations allowed).
CREATORS: dict[str, tuple[tuple[str, ...], frozenset[str]]] = {
    "agents": (("inbox", "inflight", "read", "sent", "work", "runs", "MEMORY.md"), frozenset({"mkdir", "touch", "write_text"})),
    "bootstrap": (("inbox", "inflight", "read", "sent", ".runtime"), frozenset({"mkdir"})),
}
# ``write_text`` is a creator operation only with an empty string ("empty MEMORY.md at creation"); checks.py enforces that.

# Packages that write on behalf of the owners and are never blamed.
NOT_BLAMED: frozenset[str] = frozenset({"kernel", "app"})

# Closed registry of ledger names (kernel.LedgerStore): name -> owning package. Each name literal, passed to a ledger call
# (``ledger("x")``, ``save_ledger("x", ..)``, ``<ledgers>.read("x")`` / ``.write("x", ..)``), may appear in its owner only.
LEDGERS: dict[str, str] = {
    "failures": "eligibility",
    "running": "runs",
    "nudges": "stalls",
    "strays": "strays",
    "reviews": "review",
}
