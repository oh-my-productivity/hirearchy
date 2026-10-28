"""The package graph of ARCHITECTURE.md, machine-readable (section 2.2 "Allowed dependencies", section 4.1 levels).

This is the single source the generators and the checks read: ``gen_importlinter`` turns it into import-linter contracts,
``test_graph`` proves it equals the document (2.2, 4.3 and the levels of 4.1) so the two cannot drift. Feature steps do not
edit it (it is complete for all 43 packages from build 2a on).

``kernel`` is level 0 and implicit for everyone; ``entry`` packages (scheduler, mcp_server, cli, dashboard) form one layer above
all features and are independent of each other; ``app`` (the composition root) may import everything and is not listed here.
"""

from __future__ import annotations

from dataclasses import dataclass

KERNEL = "kernel"
APP = "app"


@dataclass(frozen=True)
class Package:
    name: str
    kind: str  # "kernel" | "feature" | "entry"
    deps: tuple[str, ...]  # the complete list of packages it may import (always through their api), kernel included


def _p(name: str, kind: str, deps: str) -> tuple[str, Package]:
    return name, Package(name, kind, tuple(deps.split()))


PACKAGES: dict[str, Package] = dict([
    _p("kernel", "kernel", ""),
    # --- L1
    _p("agents", "feature", "kernel"),
    _p("eventlog", "feature", "kernel"),
    _p("locator", "feature", "kernel"),
    _p("processes", "feature", "kernel"),
    _p("runs", "feature", "kernel"),
    _p("settings", "feature", "kernel"),
    _p("skill", "feature", "kernel"),
    _p("snapshots", "feature", "kernel"),
    _p("templates", "feature", "kernel"),
    # --- L2
    _p("access", "feature", "kernel agents settings"),
    _p("bootstrap", "feature", "kernel settings snapshots templates"),
    _p("mail", "feature", "kernel agents"),
    _p("telemetry", "feature", "kernel eventlog settings snapshots"),
    _p("upgrade", "feature", "kernel settings snapshots templates"),
    # --- L3
    _p("kiro", "feature", "kernel agents settings access"),
    _p("orgfiles", "feature", "kernel agents settings access"),
    _p("strays", "feature", "kernel agents access"),
    _p("traces", "feature", "kernel mail"),
    # --- L4
    _p("delivery", "feature", "kernel mail traces"),
    # --- L5
    _p("budget", "feature", "kernel agents runs settings mail delivery"),
    # --- L6
    _p("dispatch", "feature", "kernel agents settings templates access mail delivery budget"),
    _p("eligibility", "feature", "kernel agents mail budget"),
    _p("hierarchy", "feature", "kernel agents settings templates access mail delivery budget"),
    # --- L7
    _p("health", "feature", "kernel agents runs settings mail budget eligibility"),
    _p("services", "feature", "kernel agents settings mail delivery dispatch"),
    _p("stalls", "feature", "kernel agents runs settings templates mail delivery eligibility"),
    # --- L8
    _p("attention", "feature", "kernel agents mail budget eligibility stalls"),
    _p("blueprint", "feature", "kernel agents settings snapshots kiro dispatch hierarchy services"),
    _p("overview", "feature", "kernel agents mail budget eligibility services"),
    _p("reflection", "feature", "kernel agents runs settings mail services"),
    _p("review", "feature", "kernel agents runs settings templates mail delivery budget eligibility health"),
    # --- L9
    _p("daemon", "feature", "kernel processes snapshots mail attention"),
    _p("prompts", "feature", "kernel agents settings access mail strays budget eligibility services reflection"),
    _p("retro", "feature", "kernel agents eventlog runs settings mail budget eligibility health services attention reflection blueprint"),
    # --- L10
    _p("observability", "feature", "kernel agents eventlog processes runs settings mail budget eligibility attention daemon"),
    _p("progress", "feature", "kernel agents runs mail budget eligibility attention reflection daemon"),
    # --- L11
    _p("dashdata", "feature", "kernel agents eventlog runs settings access mail budget eligibility health services attention "
                              "reflection daemon observability progress"),
    # --- entry points
    _p("scheduler", "entry", "kernel agents processes runs settings snapshots templates access mail telemetry kiro strays delivery "
                             "budget eligibility stalls attention review daemon prompts"),
    _p("mcp_server", "entry", "kernel agents locator settings access bootstrap mail telemetry orgfiles traces budget dispatch "
                              "hierarchy health services attention blueprint overview reflection daemon prompts retro observability "
                              "progress"),
    _p("cli", "entry", "kernel agents locator settings skill snapshots bootstrap mail telemetry upgrade kiro dispatch eligibility "
                       "hierarchy health services blueprint overview reflection review daemon retro observability progress dashdata"),
    _p("dashboard", "entry", "kernel dashdata"),
])

FEATURES: tuple[str, ...] = tuple(n for n, p in PACKAGES.items() if p.kind == "feature")
ENTRY_POINTS: tuple[str, ...] = tuple(n for n, p in PACKAGES.items() if p.kind == "entry")
ALL_PACKAGES: tuple[str, ...] = tuple(PACKAGES) + (APP,)  # the 43 packages of section 2.2


def level(name: str) -> int:
    """Level in the dependency DAG (4.1): kernel 0, otherwise 1 + the highest level among the dependencies."""
    deps = [d for d in PACKAGES[name].deps if d != KERNEL]
    return 0 if name == KERNEL else 1 + max((level(d) for d in deps), default=0)


def feature_levels() -> dict[int, tuple[str, ...]]:
    """{level: features of that level}; level 1 = depends on the kernel only. Entry points are not in here."""
    levels: dict[int, list[str]] = {}
    for name in FEATURES:
        levels.setdefault(level(name), []).append(name)
    return {n: tuple(sorted(names)) for n, names in sorted(levels.items())}


def edges() -> set[tuple[str, str]]:
    """Every (importer, imported) pair allowed between non-kernel packages (219 in section 4.3)."""
    return {(n, d) for n, p in PACKAGES.items() for d in p.deps if d != KERNEL}


def allowed_imports(name: str) -> frozenset[str]:
    """Packages ``name`` may import: its declared dependencies, itself, and the kernel. ``app`` may import everything."""
    if name == APP:
        return frozenset(ALL_PACKAGES)
    return frozenset(PACKAGES[name].deps) | {name, KERNEL}
