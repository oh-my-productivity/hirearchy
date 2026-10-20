# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import subprocess
import sys

import pytest
from testkit.cli_world import main


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)


# ------------------------------------------------------------------ CLI
def org_lines(capsys) -> list[str]:
    return [line for line in capsys.readouterr().err.splitlines() if line.startswith("org: ")]


def test_mutating_cli_commands_print_the_org_first(org, tmp_path, capsys):
    root = str(org.root)
    target = tmp_path / "newly"
    main(["init", str(target), "--mission", "m"])
    assert org_lines(capsys) == [f"org: {target.resolve()}"]

    for argv in (
        ["hire", "ceo", "dev", "--role", "Dev", "--charter", "Code."],
        ["task", "ceo", "--title", "T", "--goal", "g", "--acceptance", "a"],
        ["send", "ceo", "hello"],
        ["resume", "ceo"],
        ["review"],
        ["run", "--once"],
        ["inbox"],
    ):
        main(["--root", root, *argv])
        assert org_lines(capsys) == [f"org: {org.root}"], argv


def test_read_only_cli_commands_stay_quiet(org, capsys):
    for argv in (["status"], ["health"], ["review", "--dry-run"], ["inbox", "--keep"]):
        main(["--root", str(org.root), *argv])
        assert org_lines(capsys) == [], argv


def test_org_line_uses_the_discovered_org_and_comes_before_errors(org, monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(org.root)  # cwd discovery is unchanged
    main(["send", "ceo", "hi"])
    assert org_lines(capsys) == [f"org: {org.root}"]
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path / "nowhere"), "send", "ceo", "hi"])
    err = capsys.readouterr().err
    assert err.index("org: ") < err.index("error: ")


def test_module_entry_point_matches_the_script():
    done = subprocess.run([sys.executable, "-m", "orgmcp", "--help"], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0 and "usage: orgmcp" in done.stdout
