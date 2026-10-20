# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio

import pytest
from testkit.legacy.orgmcp.core import ROOT, Org
from testkit.skill_world import build_server


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORGMCP_WORKSPACE_ROOTS", str(tmp_path))


# ------------------------------------------------------------------------------------ install-skill
def test_install_skill_to_a_temp_dest(tmp_path, capsys):
    from testkit.legacy.orgmcp.app.wire_cli import run_cli as main
    from testkit.skill_world import skill_source

    dest = tmp_path / "skills"
    main(["install-skill", "--dest", str(dest)])
    target = dest / "orgmcp" / "SKILL.md"
    out = capsys.readouterr().out
    assert str(target.resolve()) in out and target.read_text() == skill_source().read_text()
    main(["install-skill", "--dest", str(dest)])  # identical: fine, nothing changes
    assert "up to date" in capsys.readouterr().out


def test_install_skill_refuses_to_overwrite_a_different_file_without_force(tmp_path, capsys):
    from testkit.legacy.orgmcp.app.wire_cli import run_cli as main

    target = tmp_path / "skills" / "orgmcp" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("my own version\n")
    with pytest.raises(SystemExit):
        main(["install-skill", "--dest", str(tmp_path / "skills")])
    assert "--force" in capsys.readouterr().err and target.read_text() == "my own version\n"
    main(["install-skill", "--dest", str(tmp_path / "skills"), "--force"])
    assert target.read_text().startswith("---\nname: orgmcp")


def test_install_skill_defaults_to_home_kiro_skills(tmp_path, monkeypatch, capsys):
    from testkit.legacy.orgmcp.app.wire_cli import run_cli as main

    monkeypatch.setenv("HOME", str(tmp_path))
    main(["install-skill"])
    assert (tmp_path / ".kiro" / "skills" / "orgmcp" / "SKILL.md").is_file()
    assert str((tmp_path / ".kiro" / "skills" / "orgmcp" / "SKILL.md").resolve()) in capsys.readouterr().out


def test_skill_names_the_final_tools_and_signatures(tmp_path):
    from testkit.skill_world import skill_source

    text = skill_source().read_text()
    tools = {t.name for t in asyncio.run(build_server(Org.init(tmp_path / "o", "m"), ROOT).list_tools())}
    for name in ("create_org", "propose_org", "apply_org", "progress", "start", "stop", "whoami", "status", "inbox", "send",
                 "blueprint_example"):
        assert name in tools and f"`{name}" in text, name
    assert "apply_org(blueprint=<the approved YAML, unchanged>, approved=True, plan_id=<from propose_org>)" in text
    assert "create_org(mission=" in text and "propose_org(blueprint=" in text
