"""Every agent runs on claude-sonnet-5.5 unless its charter or the org config names another model."""

import os
import sys
import time

import testkit
import yaml

from orgmcp import observe
from orgmcp.cli import main
from orgmcp.core import DEFAULT_MODEL, ROOT, Org
from orgmcp.scheduler import Scheduler

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
    org.write(ROOT, "ceo/AGENT.md", CHARTER.format(model=f"model: {model}\n" if model else ""))


def fake_runner():
    def build(org, addr, prompt):
        return [sys.executable, FAKE], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": "work"}

    return build


def test_the_cli_init_and_hire_without_model_use_the_default(tmp_path, capsys):
    target = tmp_path / "org"
    main(["init", str(target), "--mission", "m"])
    assert Org(target).default_model == DEFAULT_MODEL
    main(["--root", str(target), "hire", "root", "ceo", "--role", "CEO", "--charter", "Lead."])
    assert Org(target).model_for("ceo") == DEFAULT_MODEL
    main(["init", str(tmp_path / "o2"), "--mission", "m", "--model", "claude-haiku-4.5"])
    assert Org(tmp_path / "o2").config["default_model"] == "claude-haiku-4.5"
    capsys.readouterr()


def test_create_org_without_a_model_uses_the_default(tmp_path, monkeypatch):
    from orgmcp.server import resolve_binding

    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "new"))
    binding, _ = resolve_binding()
    org = binding.create("A mission")
    assert org.config["default_model"] == DEFAULT_MODEL


def run_start_models(org: Org) -> dict[str, str]:
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
    sched = Scheduler(org, fake_runner(), echo=lambda _: None)
    sched.acquire()
    try:
        for _ in range(500):
            if not sched.tick():
                break
            time.sleep(0.02)
    finally:
        sched.release()
    return {e["agent"]: e["model"] for e in observe.events(org, kind="run.start", since="1h")}


def test_the_run_start_event_reports_the_resolved_model(org):
    assert run_start_models(org) == {"ceo": DEFAULT_MODEL, "ceo/eng": DEFAULT_MODEL}


def test_the_run_start_event_reports_explicit_models(org):
    set_config(org, default_model="org-model")
    charter_model(org, "charter-model")
    assert run_start_models(org) == {"ceo": "charter-model", "ceo/eng": "org-model"}
