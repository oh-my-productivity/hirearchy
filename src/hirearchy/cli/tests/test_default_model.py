# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.cli_world import main
from testkit.reach.hirearchy.core import DEFAULT_MODEL, Org


def test_the_cli_init_and_hire_without_model_use_the_default(tmp_path, capsys):
    target = tmp_path / "org"
    main(["init", str(target), "--mission", "m"])
    assert Org(target).default_model == DEFAULT_MODEL
    main(["--root", str(target), "hire", "root", "ceo", "--role", "CEO", "--charter", "Lead."])
    assert Org(target).model_for("ceo") == DEFAULT_MODEL
    main(["init", str(tmp_path / "o2"), "--mission", "m", "--model", "claude-opus-5.5"])
    assert Org(tmp_path / "o2").config["default_model"] == "claude-opus-5.5"
    capsys.readouterr()


def test_the_cli_init_refuses_a_model_below_the_floor(tmp_path, capsys):
    capsys.readouterr()
    with pytest.raises(SystemExit) as refused:
        main(["init", str(tmp_path / "o3"), "--mission", "m", "--model", "claude-haiku-4.5"])
    assert refused.value.code != 0
    err = capsys.readouterr().err
    assert "cannot create the organization: default_model: " in err and "allowed: claude-sonnet-5.5, claude-opus-5.5" in err
    assert not (tmp_path / "o3" / "ORG.md").exists()
