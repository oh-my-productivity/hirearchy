# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import os
import sys
import time

import testkit
import testkit.reach.yaml as yaml
from testkit.reach.hirearchy.core import DEFAULT_MODEL, ROOT, Org
from testkit.scheduler_loop import loop_over

FAKE = str(testkit.FAKE_AGENT)
CHARTER = "---\nrole: CEO\n{model}tools: [read]\n---\nLead.\n"


def set_config(org: Org, **kw) -> None:
    """Rewrite ORG.md's frontmatter (a legacy org: ``default_model: null`` or no key at all)."""
    path = org.root / "ORG.md"
    meta, body = path.read_text().split("---\n", 2)[1:]
    cfg = yaml.safe_load(meta)
    cfg.update(kw)
    for k in [k for k, v in kw.items() if v == "<missing>"]:
        cfg.pop(k)
    path.write_text("---\n" + yaml.safe_dump(cfg) + "---\n" + body)


def charter_model(org: Org, model: str | None) -> None:
    """A charter written before the model floor (docs/design/org-agent-model-floor.md): on disk, behind ``write``, which would refuse the id."""
    (org.dir("ceo") / "AGENT.md").write_text(CHARTER.format(model=f"model: {model}\n" if model else ""), encoding="utf-8")


def fake_runner():
    def build(org, addr, prompt):
        return [sys.executable, FAKE], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": "work"}

    return build


def run_start_models(org: Org) -> dict[str, str]:
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    sched = loop_over(org, fake_runner(), echo=lambda _: None)
    sched.acquire()
    try:
        for _ in range(500):
            if not sched.tick():
                break
            time.sleep(0.02)
    finally:
        sched.release()
    return {e["agent"]: e["model"] for e in org.runtime.event_queries.events(kind="run.start", since="1h")}


def test_the_run_start_event_reports_the_resolved_model(org):
    assert run_start_models(org) == {"ceo": DEFAULT_MODEL, "ceo/eng": DEFAULT_MODEL}


def test_the_run_start_event_reports_explicit_models(org):
    set_config(org, default_model="org-model")
    charter_model(org, "charter-model")
    assert run_start_models(org) == {"ceo": "charter-model", "ceo/eng": "org-model"}
