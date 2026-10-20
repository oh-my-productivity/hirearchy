# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import copy

import pytest
import testkit
import testkit.legacy.yaml as yaml
from testkit.cli_world import main
from testkit.legacy.orgmcp.core import Org


EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"


@pytest.fixture
def base(tmp_path):
    """tmp_path as the only allowed root; the example research blueprint with its deliverable inside it."""
    (tmp_path / "deliverables").mkdir()
    bp = yaml.safe_load(EXAMPLE.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    return bp


@pytest.fixture
def empty_org(tmp_path):
    return Org.init(tmp_path / "org", "bp tests", {"poll_seconds": 0.05})


def mutate(bp, fn):
    out = copy.deepcopy(bp)
    fn(out)
    return out


# --------------------------------------------------------------------------------------------- CLI
def write_bp(tmp_path, bp, name="bp.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(bp, sort_keys=False))
    return str(p)


def test_cli_plan_ok_and_errors(base, tmp_path, empty_org, capsys):
    good = write_bp(tmp_path, base)
    main(["--root", str(empty_org.root), "plan", good, "--allow-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Plan for approval" in out and "Reply 'approve'" in out
    bad = write_bp(tmp_path, mutate(base, lambda b: b["task"].pop("acceptance")), "bad.yaml")
    with pytest.raises(SystemExit) as e:
        main(["--root", str(empty_org.root), "plan", bad, "--allow-root", str(tmp_path)])
    assert e.value.code == 1
    assert "Errors (1)" in capsys.readouterr().out
    assert empty_org.agents() == []


def test_cli_plan_works_without_an_org(base, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ORG_ROOT", raising=False)
    main(["plan", write_bp(tmp_path, base), "--allow-root", str(tmp_path)])
    assert "Plan for approval" in capsys.readouterr().out


def test_cli_apply(base, tmp_path, empty_org, capsys):
    path = write_bp(tmp_path, base)
    main(["--root", str(empty_org.root), "apply", path, "--allow-root", str(tmp_path)])
    cap = capsys.readouterr()
    assert f"org: {empty_org.root}" in cap.err  # announced on stderr before anything is changed
    assert "created 4 agents" in cap.out and "-> lead (budget 22)" in cap.out
    assert empty_org.exists("lead/factcheck")
    with pytest.raises(SystemExit) as e:  # second apply: names exist
        main(["--root", str(empty_org.root), "apply", path, "--allow-root", str(tmp_path)])
    assert e.value.code == 1
    assert "already exists" in capsys.readouterr().err


def test_cli_apply_error_exit(base, tmp_path, empty_org, capsys):
    bad = write_bp(tmp_path, mutate(base, lambda b: b["needs"].pop("deliverable")), "bad.yaml")
    with pytest.raises(SystemExit) as e:
        main(["--root", str(empty_org.root), "apply", bad, "--allow-root", str(tmp_path)])
    assert e.value.code == 1 and "nothing was created" in capsys.readouterr().err
    assert empty_org.agents() == []
