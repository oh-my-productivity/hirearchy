"""Every agent runs on claude-sonnet-5.5 unless its charter or the org config names another model."""

import os
import sys
import time

import pytest
import testkit
import yaml

from orgmcp import observe
from orgmcp.cli import main
from orgmcp.core import DEFAULT_CONFIG, DEFAULT_MODEL, ROOT, Org
from orgmcp.scheduler import Scheduler, kiro_runner

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


def model_arg(cmd: list[str]) -> str:
    assert cmd.count("--model") == 1
    return cmd[cmd.index("--model") + 1]


def fake_runner():
    def build(org, addr, prompt):
        return [sys.executable, FAKE], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": "work"}

    return build


# ------------------------------------------------------------------------------------------ the constant
def test_the_default_is_one_constant_used_by_the_default_config():
    assert DEFAULT_MODEL == "claude-sonnet-5.5" and DEFAULT_CONFIG["default_model"] == DEFAULT_MODEL


# ------------------------------------------------------------------------------------------ resolution order
def test_charter_model_beats_org_config_beats_default(org):
    assert org.model_for("ceo") == DEFAULT_MODEL  # no model anywhere
    set_config(org, default_model="org-model")
    assert org.model_for("ceo") == "org-model" and org.model_for("ceo/eng") == "org-model"
    charter_model(org, "charter-model")
    assert org.model_for("ceo") == "charter-model" and org.model_for("ceo/eng") == "org-model"


@pytest.mark.parametrize("value", [None, "", "<missing>"])
def test_an_org_without_an_explicit_default_model_runs_on_the_default(org, value):
    set_config(org, default_model=value)  # ORG.md says `default_model: null`, an empty value, or has no such key
    assert org.default_model == DEFAULT_MODEL and org.model_for("ceo") == DEFAULT_MODEL
    charter_model(org, "kept-explicit")
    assert org.model_for("ceo") == "kept-explicit"


def test_a_new_org_writes_the_default_and_an_explicit_one_is_kept(tmp_path):
    fresh = Org.init(tmp_path / "a", "m")
    assert fresh.config["default_model"] == DEFAULT_MODEL and "default_model: claude-sonnet-5.5" in (fresh.root / "ORG.md").read_text()
    other = Org.init(tmp_path / "b", "m", {"default_model": "claude-haiku-4.5"})
    assert other.default_model == "claude-haiku-4.5"


def test_hire_without_a_model_leaves_the_charter_unpinned_so_the_org_default_applies(org):
    org.hire(ROOT, "ops", "Ops", "Do ops.")
    assert "model" not in org.charter("ops")[0] and org.model_for("ops") == DEFAULT_MODEL
    set_config(org, default_model="later")
    assert org.model_for("ops") == "later"  # a later org-wide choice reaches the agent
    org.hire(ROOT, "pinned", "Pinned", "Pinned.", model="m-x")
    assert org.model_for("pinned") == "m-x"


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


# ------------------------------------------------------------------------------------------ the run command
def test_the_scheduler_command_always_carries_the_model(org):
    cmd, _, _ = kiro_runner()(org, "ceo", "P")
    assert model_arg(cmd) == "claude-sonnet-5.5" and cmd[-2:] == ["--model", "claude-sonnet-5.5"]
    cmd, _, _ = kiro_runner()(org, "ceo/eng", "P")
    assert model_arg(cmd) == "claude-sonnet-5.5"


def test_the_scheduler_command_keeps_an_explicit_model(org):
    set_config(org, default_model="org-model")
    charter_model(org, "charter-model")
    assert model_arg(kiro_runner()(org, "ceo", "P")[0]) == "charter-model"
    assert model_arg(kiro_runner()(org, "ceo/eng", "P")[0]) == "org-model"


@pytest.mark.parametrize("value", [None, "<missing>"])
def test_the_scheduler_command_for_a_legacy_org_config_uses_the_default(org, value):
    set_config(org, default_model=value)
    assert model_arg(kiro_runner()(org, "ceo", "P")[0]) == DEFAULT_MODEL


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
