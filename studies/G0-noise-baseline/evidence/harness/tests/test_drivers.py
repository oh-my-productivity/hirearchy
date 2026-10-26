"""Tests of the G0 stream drivers (helper S). Nothing real is created: no sandbox, no profile, no kiro home, no org, no chat.

Run (cwd = the harness dir):
  PYTHONDONTWRITEBYTECODE=1 /Volumes/workspace/hirearchy/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_drivers.py

Rules these tests keep:
- `run_turn.sh`, `after_turn.sh`, `quality_snapshot.sh`, `finish_stream.sh`, `setup_stream.sh` (without --dry-run) are never run; only their
  text is checked (and `zsh -n`).
- Scripts that read ~/.kiro run with a fake HOME under tmp_path and a minimal environment (no credentials are passed on).
- `prepare_m0_home.sh` and `skill_check.sh` are also run for real, but only as COPIES whose path constants are rewritten to tmp_path
  (the shipped scripts are not modified).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

H = Path(__file__).resolve().parent.parent
REPO = Path("/Volumes/workspace/hirearchy")
E7EV = REPO / "studies/E7-org-growth-0a4-recheck/evidence"
E7H = E7EV / "harness"
G0EV = REPO / "studies/G0-noise-baseline/evidence"
SKILL_MD5 = "a3e46347b70a7ece5f734f70198c607f"
SKILL_MD5_E7 = "fd89a7fda55b8f342cf0306173c363fb"

SHELL_SCRIPTS = [
    "run_turn.sh", "ambient_snapshot.sh", "after_turn.sh", "quality_snapshot.sh", "setup_stream.sh", "run_arm.sh",
    "skill_check.sh", "finish_stream.sh", "copy_org_evidence.sh", "model_check.sh", "safety-snapshot.sh", "prepare_m0_home.sh",
]
PY_SCRIPTS = ["skill_check.py", "org_state.py", "ambient_context.py", "extract_tool_calls.py", "extract_proposals.py"]


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def clean_env(home: Path, **extra: str) -> dict[str, str]:
    """A minimal environment: no credential variable of the real environment is passed on."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home), "LANG": "en_US.UTF-8", "TZ": "UTC"}
    env.update(extra)
    return env


def run(cmd: list[str], env: dict[str, str], cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def g0_glob() -> list[str]:
    return sorted(p.name for p in Path("/tmp").glob("hirearchy-g0-*"))


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    k = home / ".kiro"
    (k / "settings").mkdir(parents=True)
    (k / "settings" / "cli.json").write_text('{"chat.x": 1}\n')
    (k / "settings" / "cli.json.lock").write_text("lock\n")
    (k / "settings" / "mcp.json").write_text('{"secret": "SENTINEL-SECRET"}\n')
    (k / "settings" / "mcp.json.bak").write_text("bak SENTINEL-SECRET\n")
    (k / "settings" / "mcp.json.bak-x").write_text("bak2 SENTINEL-SECRET\n")
    (k / "settings" / "survey_state.json").write_text("{}\n")
    (k / "settings" / "subdir").mkdir()
    (k / "settings" / "subdir" / "inner.json").write_text("inner\n")
    (k / "skills" / "hirearchy").mkdir(parents=True)
    (k / "skills" / "hirearchy" / "SKILL.md").write_bytes((REPO / "skills/hirearchy/SKILL.md").read_bytes())
    (k / "skills" / "autoresearch").mkdir()
    (k / "skills" / "autoresearch" / "SKILL.md").write_text("autoresearch skill\n")
    (home / ".agents" / "skills" / "agents").mkdir(parents=True)
    (home / ".agents" / "skills" / "agents" / "SKILL.md").write_text("agents skill\n")
    (k / "skills" / "agents").symlink_to("../../.agents/skills/agents")
    (k / "memories").mkdir()
    (k / "memories" / "memories.db").write_bytes(b"not a real db")
    (k / "agents").mkdir()
    (k / "agents" / "claude-sonnet-5.5.json").write_text("{}\n")
    (k / "secrets.json").write_text('{"token": "SENTINEL-SECRET"}\n')
    (k / "sessions").mkdir()
    return home


def tree_state(root: Path) -> list[tuple]:
    out = []
    for p in sorted(root.rglob("*")):
        st = p.lstat()
        out.append((str(p.relative_to(root)), st.st_mode, st.st_size, st.st_mtime_ns, os.readlink(p) if p.is_symlink() else None))
    return out


def sed_copy(src: Path, dst: Path, subs: dict[str, str]) -> Path:
    """Copy a shipped script with the line that matches each regex (exactly one line) replaced; for the tmp_path runs."""
    text = src.read_text()
    for pat, rep in subs.items():
        text, n = re.subn(pat, lambda _m, rep=rep: rep, text, flags=re.M)
        assert n == 1, f"{pat!r} matched {n} lines in {src.name}"
    dst.write_text(text)
    return dst


# --------------------------------------------------------------------------------------------- files exist, syntax
@pytest.mark.parametrize("name", SHELL_SCRIPTS)
def test_zsh_syntax(name: str) -> None:
    p = H / name
    assert p.is_file(), f"{name} is missing"
    r = subprocess.run(["zsh", "-n", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("name", PY_SCRIPTS)
def test_python_scripts_compile(name: str) -> None:
    p = H / name
    assert p.is_file(), f"{name} is missing"
    compile(p.read_text(), str(p), "exec")


def test_no_e7_paths_or_product_imports_in_executable_lines() -> None:
    bad = []
    for name in SHELL_SCRIPTS + PY_SCRIPTS:
        for i, line in enumerate((H / name).read_text().splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            if re.search(r"E7-org-growth|18a4531|hirearchy-study-e7|hirearchy-e7-|import hirearchy|from hirearchy", line):
                bad.append(f"{name}:{i}: {line[:120]}")
    # org_state.py, ambient_context.py, extract_* are E7's logic; their code lines must hold no E7 path either
    assert not bad, "\n".join(bad)


# --------------------------------------------------------------------------------------------- byte copies of E7's files
def test_workspace_cli_json_is_byte_identical() -> None:
    assert md5(H / "workspace-cli.json") == "05d30ccbfd35530747c8a542eb67985c"
    assert (H / "workspace-cli.json").read_bytes() == (E7H / "workspace-cli.json").read_bytes()


def test_inject_root_rework_untouched() -> None:
    assert md5(H / "inject_root_rework.py") == "1c4e7824e448a3a34e24a7b759a59fcd"


@pytest.mark.parametrize("name", ["test_poll_loop.py", "ambient_context.py", "extract_tool_calls.py", "extract_proposals.py"])
def test_files_that_name_no_e7_path_are_byte_identical_to_e7s(name: str) -> None:
    assert (H / name).read_bytes() == (E7H / name).read_bytes()


def test_org_state_differs_from_e7s_only_in_names() -> None:
    a = (E7H / "org_state.py").read_text().splitlines()
    b = (H / "org_state.py").read_text().splitlines()
    assert len(a) == len(b)
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    assert diff, "org_state.py was not adapted at all (its docstring names E7)"
    for x, y in diff:
        assert "E7" in x and "G0" in y and x.replace("E7", "G0") == y


# --------------------------------------------------------------------------------------------- profile template
def test_profile_template_differs_from_e7s_only_in_the_three_named_fields() -> None:
    g = json.loads((H / "profile-template.json").read_text())
    e = json.loads((E7H / "profile-template.json").read_text())
    assert g["name"] == "hirearchy-study-g0-<LABEL>-assistant"
    assert g["description"] == "internal: hirearchy usability study G0 stream <LABEL> assistant; deleted after the stream"
    assert g["mcpServers"]["hirearchy"]["env"]["ORG_ROOT"] == "/tmp/hirearchy-g0-<LABEL>-<epoch>/org"
    for d in (g, e):
        d["name"] = d["description"] = None
        d["mcpServers"]["hirearchy"]["env"]["ORG_ROOT"] = None
    assert g == e
    a = (E7H / "profile-template.json").read_text().splitlines()
    b = (H / "profile-template.json").read_text().splitlines()
    assert len(a) == len(b)
    assert sum(1 for x, y in zip(a, b) if x != y) == 3


# --------------------------------------------------------------------------------------------- run_arm.sh
def run_arm(evdir: Path, *args: str, home: Path | None = None) -> subprocess.CompletedProcess:
    home = home or evdir
    return run(["zsh", str(H / "run_arm.sh"), *args], clean_env(home, G0_RUN_ARM_EV=str(evdir)))


def first_line_labels(out: str) -> list[str]:
    m = re.search(r"^next labels: (.*)$", out, re.M)
    assert m, out
    return m.group(1).split()


def test_run_arm_label_computation_empty(tmp_path: Path) -> None:
    r = run_arm(tmp_path, "m0", "2")
    assert r.returncode == 0, r.stderr
    assert first_line_labels(r.stdout) == ["m0-s1", "m0-s2"]


def test_run_arm_label_computation_next_after_highest_and_replacements_do_not_count(tmp_path: Path) -> None:
    for d in ["m0-s1", "m0-s2", "m0-s2r", "m0-s2r2", "m0-s1r", "m1-s1", "m1-s2", "m1-s3", "m1-s3r", "harness", "notes", "m0-s10x"]:
        (tmp_path / d).mkdir()
    (tmp_path / "m0-s7").write_text("a file is not a stream dir\n")
    r = run_arm(tmp_path, "m0", "2")
    assert first_line_labels(r.stdout) == ["m0-s3", "m0-s4"]
    r = run_arm(tmp_path, "m1", "1")
    assert first_line_labels(r.stdout) == ["m1-s4"]


def test_run_arm_ten_is_above_nine(tmp_path: Path) -> None:
    for n in (1, 9, 10):
        (tmp_path / f"m1-s{n}").mkdir()
    assert first_line_labels(run_arm(tmp_path, "m1", "1").stdout) == ["m1-s11"]


def test_run_arm_plan_has_the_protocol_6_command_sequence_per_label(tmp_path: Path) -> None:
    r = run_arm(tmp_path, "m1", "2")
    out = r.stdout
    for label in ("m1-s1", "m1-s2"):
        block = out[out.index(f"== {label}"):]
        for needle in [f"setup_stream.sh {label}", f"run_turn.sh", f"after_turn.sh {label}", "inject_root_rework.py", "--revises",
                       f"finish_stream.sh {label}", "skill_check.sh", "ambient_context.py", "model_check.sh org", "model_check.sh assistant"]:
            assert needle in block, f"{needle} missing in the plan of {label}"
    # the plan only prints: nothing was created in the evidence root
    assert sorted(p.name for p in tmp_path.iterdir()) == []


def test_run_arm_rejects_bad_arguments_and_setup_with_k_above_one(tmp_path: Path) -> None:
    for args in (["m2", "1"], ["m0", "0"], ["m0", "x"], ["m0"], [], ["m0", "2", "--setup"], ["m0", "1", "--bogus"]):
        r = run_arm(tmp_path, *args)
        assert r.returncode == 2, (args, r.stdout, r.stderr)
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------------------------- prepare_m0_home.sh
def test_prepare_m0_home_dry_run_plans_and_creates_nothing(fake_home: Path) -> None:
    target = "/tmp/hirearchy-g0-m0home-m0-s1-1700000000"
    assert not Path(target).exists()
    before = g0_glob()
    home_state = tree_state(fake_home)
    r = run(["zsh", str(H / "prepare_m0_home.sh"), "m0-s1", target, "--dry-run"], clean_env(fake_home))
    assert r.returncode == 0, r.stderr + r.stdout
    assert not Path(target).exists()
    assert g0_glob() == before
    assert tree_state(fake_home) == home_state
    out = r.stdout
    assert "DRY-RUN" in out
    assert "cli.json" in out and "cli.json.lock" in out and "survey_state.json" in out
    assert "mcp.json" not in out.replace("mcp.json*", "")  # no mcp.json* file is planned for a copy
    assert "subdir" not in out.replace("subdirectories", "")
    assert "skills/hirearchy/SKILL.md" in out and SKILL_MD5 in out
    assert re.search(r"symlink .*skills/autoresearch -> .*/\.kiro/skills/autoresearch", out)
    assert re.search(r"symlink .*skills/agents -> .*/\.kiro/skills/agents", out)
    assert "memories" in out and "NOT created" in out
    assert not (G0EV / "m0-s1").exists()


def test_prepare_m0_home_guard_refuses_other_targets(fake_home: Path, tmp_path: Path) -> None:
    for tgt in (str(tmp_path / "m0home"), "/tmp/other-dir-xyz", "/tmp/hirearchy-g0-m0-s1-1", str(fake_home / ".kiro"), "relative/dir"):
        r = run(["zsh", str(H / "prepare_m0_home.sh"), "m0-s1", tgt, "--dry-run"], clean_env(fake_home))
        assert r.returncode != 0, tgt
        assert "REFUSED" in r.stdout + r.stderr, tgt
        assert not Path(tgt).exists() or tgt == str(fake_home / ".kiro")
    r = run(["zsh", str(H / "prepare_m0_home.sh"), "m1-s1", "/tmp/hirearchy-g0-m0home-m1-s1-1", "--dry-run"], clean_env(fake_home))
    assert r.returncode != 0 and "arm" in (r.stdout + r.stderr)  # M0 homes only for arm m0


def test_prepare_m0_home_accepts_the_preflight_label_in_a_dry_run(fake_home: Path) -> None:
    """Protocol 11: the preflight's M0 kiro-home check uses prepare_m0_home.sh with the label 'preflight'; other labels stay refused."""
    target = "/tmp/hirearchy-g0-m0home-preflight-1700000000"
    before = g0_glob()
    r = run(["zsh", str(H / "prepare_m0_home.sh"), "preflight", target, "--dry-run"], clean_env(fake_home))
    assert r.returncode == 0, r.stderr + r.stdout
    assert "DRY-RUN" in r.stdout and not Path(target).exists() and g0_glob() == before
    for bad in ("preflight2", "probe", "m1-preflight"):
        r = run(["zsh", str(H / "prepare_m0_home.sh"), bad, f"/tmp/hirearchy-g0-m0home-{bad}-1", "--dry-run"], clean_env(fake_home))
        assert r.returncode != 0 and "REFUSED" in (r.stdout + r.stderr), bad


def make_prepare_copy(tmp_path: Path) -> tuple[Path, Path, Path]:
    ev = tmp_path / "evidence"
    (ev / "m0-s1").mkdir(parents=True)
    pre = tmp_path / "m0homes" / "hirearchy-g0-m0home-"
    pre.parent.mkdir()
    script = sed_copy(H / "prepare_m0_home.sh", tmp_path / "prepare_copy.sh", {
        r"^EV=.*$": f"EV={ev}",
        r"^M0_PREFIX=.*$": f"M0_PREFIX={pre}",
    })
    return script, ev, pre


def test_prepare_m0_home_real_run_in_a_copy(fake_home: Path, tmp_path: Path) -> None:
    script, ev, pre = make_prepare_copy(tmp_path)
    target = Path(f"{pre}m0-s1-1700000000")
    gstate = tree_state(fake_home)
    r = run(["zsh", str(script), "m0-s1", str(target)], clean_env(fake_home))
    assert r.returncode == 0, r.stderr + r.stdout
    k = target / ".kiro"
    assert sorted(p.name for p in target.iterdir()) == [".kiro"]
    assert sorted(p.name for p in k.iterdir()) == ["agents", "settings", "skills"]  # no memories, sessions, secrets.json
    assert list((k / "agents").iterdir()) == []
    # settings: byte copies (cp -p) of the regular files except mcp.json*
    names = sorted(p.name for p in (k / "settings").iterdir())
    assert names == ["cli.json", "cli.json.lock", "survey_state.json"]
    for n in names:
        a, b = fake_home / ".kiro/settings" / n, k / "settings" / n
        assert a.read_bytes() == b.read_bytes()
        assert int(a.stat().st_mtime) == int(b.stat().st_mtime)  # cp -p
    # skills: a real directory; hirearchy/SKILL.md a real copy; the others symlinks to the owner's entries
    sk = k / "skills"
    assert sk.is_dir() and not sk.is_symlink()
    assert (sk / "hirearchy").is_dir() and not (sk / "hirearchy").is_symlink()
    assert (sk / "hirearchy" / "SKILL.md").read_bytes() == (REPO / "skills/hirearchy/SKILL.md").read_bytes()
    assert not (sk / "hirearchy" / "SKILL.md").is_symlink()
    assert sorted(p.name for p in sk.iterdir()) == ["agents", "autoresearch", "hirearchy"]
    for n in ("agents", "autoresearch"):
        assert (sk / n).is_symlink()
        assert os.readlink(sk / n) == f"{fake_home}/.kiro/skills/{n}"
    # evidence
    setup = (ev / "m0-s1" / "m0-home" / "setup.txt").read_text()
    assert (ev / "m0-s1" / "m0-home-path.txt").read_text().strip() == str(target)
    assert str(target) in setup and "cli.json" in setup and SKILL_MD5 in setup and "autoresearch ->" in setup
    assert "SENTINEL-SECRET" not in setup
    assert "ls -la" in setup
    # the owner's home is untouched
    assert tree_state(fake_home) == gstate
    # refuses an existing target
    r2 = run(["zsh", str(script), "m0-s1", str(target)], clean_env(fake_home))
    assert r2.returncode != 0 and "REFUSED" in r2.stdout + r2.stderr


def test_prepare_m0_home_skill_rules_in_a_copy(fake_home: Path, tmp_path: Path) -> None:
    script, ev, pre = make_prepare_copy(tmp_path)
    gs = fake_home / ".kiro/skills/hirearchy/SKILL.md"
    # global SKILL.md exists but differs from the repo's: no copy is made (and it is not a symlink either); a warning is recorded
    gs.write_text("a different skill\n")
    t1 = Path(f"{pre}m0-s1-1")
    r = run(["zsh", str(script), "m0-s1", str(t1)], clean_env(fake_home))
    assert r.returncode == 0, r.stderr
    assert not (t1 / ".kiro/skills/hirearchy").exists()
    assert "differs" in (ev / "m0-s1" / "m0-home" / "setup.txt").read_text()
    # global hirearchy skill absent: M0 has none either
    import shutil
    shutil.rmtree(fake_home / ".kiro/skills/hirearchy")
    (ev / "m0-s1" / "m0-home").rename(tmp_path / "old-home-evidence")
    (ev / "m0-s1" / "m0-home-path.txt").unlink()
    t2 = Path(f"{pre}m0-s1-2")
    r = run(["zsh", str(script), "m0-s1", str(t2)], clean_env(fake_home))
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in (t2 / ".kiro/skills").iterdir()) == ["agents", "autoresearch"]
    assert "absent" in (ev / "m0-s1" / "m0-home" / "setup.txt").read_text()


# --------------------------------------------------------------------------------------------- setup_stream.sh --dry-run
@pytest.mark.parametrize("label,arm", [("m0-s1", "m0"), ("m1-s2", "m1"), ("m0-s2r", "m0"), ("m1-s3r2", "m1")])
def test_setup_stream_dry_run_prints_plan_and_creates_nothing(fake_home: Path, label: str, arm: str) -> None:
    before = g0_glob()
    home_state = tree_state(fake_home)
    r = run(["zsh", str(H / "setup_stream.sh"), label, "--dry-run"], clean_env(fake_home), timeout=300)
    out = r.stdout
    assert r.returncode == 0, r.stderr + out
    assert g0_glob() == before
    assert tree_state(fake_home) == home_state  # incl. ~/.kiro/agents
    assert not (G0EV / label).exists()
    assert "DRY-RUN" in out
    assert re.search(rf"S=/tmp/hirearchy-g0-{label}-\d+\b", out)
    assert f"arm: {arm}" in out
    pname = f"hirearchy-study-g0-{label}-assistant"
    if arm == "m1":
        assert f"{fake_home}/.kiro/agents/{pname}.json" in out
        assert "M0H=" not in out
    else:
        assert re.search(rf"M0H=/tmp/hirearchy-g0-m0home-{label}-\d+\b", out)
        assert re.search(rf"/tmp/hirearchy-g0-m0home-{label}-\d+/\.kiro/agents/{pname}\.json", out)
        assert f"{fake_home}/.kiro/agents/{pname}.json" not in out
    for needle in ["gate: protocol.md", "gate: MD5SUMS", "gate: HEAD", "gate: freeze diff", "workspace-cli.json", "SKILL.md",
                   "creations.txt", "safety-before.txt", "ambient/setup.txt", "skill_check.sh", "setup.txt"]:
        assert needle in out, needle


@pytest.mark.parametrize("label", ["foo", "m2-s1", "m0-s0", "m0-s1x", "m0-s", "M0-s1", "m0-s1r-2", "m0-s1/../x", ""])
def test_setup_stream_rejects_bad_labels(fake_home: Path, label: str) -> None:
    r = run(["zsh", str(H / "setup_stream.sh"), label, "--dry-run"], clean_env(fake_home))
    assert r.returncode == 2, (r.stdout, r.stderr)


def test_setup_stream_text_has_the_gates_and_exit_code_3() -> None:
    t = (H / "setup_stream.sh").read_text()
    assert "GATE FAILED:" in t and "exit 3" in t
    assert "3c841bb9" in t and "diff --stat" in t and "protocol.md5" in t and "MD5SUMS" in t


# --------------------------------------------------------------------------------------------- run_turn.sh / after_turn.sh / finish_stream.sh text
def test_run_turn_boundary_line_is_e7s_exactly_and_cmd_begins_with_env() -> None:
    e7 = (E7H / "run_turn.sh").read_text()
    g0 = (H / "run_turn.sh").read_text()
    boundary = next(ln for ln in e7.splitlines() if ln.startswith('"${CMD[@]}" >'))
    assert boundary in g0.splitlines()
    assert "env -u KIRO_HOME" in g0 and "KIRO_HOME=" in g0 and "m0-home-path.txt" in g0
    cmd_line = next(ln for ln in g0.splitlines() if ln.startswith("CMD=("))
    assert cmd_line.startswith("CMD=(")
    assert "kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-g0-$LABEL-assistant" in cmd_line
    assert cmd_line.index("${KIRO_ENV[@]}") < cmd_line.index("kiro-cli")
    # the turn-times line is E7's
    tt = next(ln for ln in e7.splitlines() if ln.startswith('echo "turn $T:'))
    assert tt in g0.splitlines()
    assert 'sleep 20' in boundary


def test_after_turn_runs_quality_snapshot_last() -> None:
    t = (H / "after_turn.sh").read_text()
    cmds = [ln for ln in t.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert "quality_snapshot.sh" in cmds[-1] and "turn-$NN" in cmds[-1]
    assert t.count("quality_snapshot.sh") >= 1
    assert "hirearchy-study-g0-$LABEL-assistant" in t
    assert "m0-home-path.txt" in t and "model_check.sh org" in t and "model_check.sh assistant" in t
    assert "scheduler.signal" in t and "run.orphan" in t and "scheduler.exit" in t
    assert "grep -E 'listing md5|memories" in t


def test_finish_stream_order() -> None:
    t = (H / "finish_stream.sh").read_text()
    order = ["--stop", "copy_org_evidence.sh", "check", "quality_snapshot.sh", "extract_tool_calls.py", "extract_proposals.py",
             "extract_mechanical.py", "scheduler_survival.py", "injection_files.py", "assistant_facts.py", "score_memos.py",
             "ambiguity_recall.py", "prompt_sizes.py", "playbook_attempts.py", "rederive_quality.py", "model_check.sh all",
             "deletions.txt", "safety-after.txt", "ambient/end.txt", "AFTER the last turn"]
    pos = -1
    for needle in order:
        i = t.find(needle, pos + 1)
        assert i > pos, f"{needle!r} missing or out of order in finish_stream.sh"
        pos = i
    assert "rm -rf" not in t  # the M0 home is not deleted here
    assert "--compare" in t and "quality/end.json" in t


def test_quality_snapshot_text() -> None:
    t = (H / "quality_snapshot.sh").read_text()
    assert "no org yet, quality not run" in t and "ORG.md" in t
    assert "--root" in t and "quality --json" in t and "cli-*.jsonl" in t and "calls.txt" in t


# --------------------------------------------------------------------------------------------- ambient_snapshot.sh
def snap(home: Path, *args: str) -> list[str]:
    r = run(["zsh", str(H / "ambient_snapshot.sh"), *args], clean_env(home))
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def e7_snap(home: Path, label: str) -> list[str]:
    r = run(["zsh", str(E7H / "ambient_snapshot.sh"), label], clean_env(home))
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def test_ambient_snapshot_owner_sections_equal_e7s_and_it_is_read_only(fake_home: Path) -> None:
    before = tree_state(fake_home)
    g = snap(fake_home, "m1-s1 setup")
    e = e7_snap(fake_home, "m1-s1 setup")
    strip = lambda ls: [ln for ln in ls if not ln.startswith("date_utc:")]  # noqa: E731
    assert strip(g) == strip(e)
    assert tree_state(fake_home) == before
    assert any(ln.startswith("skills listing md5: ") for ln in g)
    assert any(ln.startswith("memories.db md5") for ln in g)


def test_ambient_snapshot_with_a_kiro_home_appends_three_sections(fake_home: Path, tmp_path: Path) -> None:
    m0 = tmp_path / "m0h" / ".kiro"
    (m0 / "skills" / "hirearchy").mkdir(parents=True)
    (m0 / "skills" / "hirearchy" / "SKILL.md").write_text("copy\n")
    (m0 / "skills" / "autoresearch").symlink_to(fake_home / ".kiro/skills/autoresearch")
    (m0 / "skills" / "agents").symlink_to(fake_home / ".kiro/skills/agents")
    before = tree_state(tmp_path / "m0h")
    g = snap(fake_home, "m0-s1 before turn 2", str(m0))
    e = e7_snap(fake_home, "m0-s1 before turn 2")
    strip = lambda ls: [ln for ln in ls if not ln.startswith("date_utc:")]  # noqa: E731
    assert strip(g)[: len(strip(e))] == strip(e)  # the owner's output is unchanged and comes first
    extra = g[len(e):]
    text = "\n".join(extra)
    assert f"{m0}/skills" in text and "find -P" in text and "find -L" in text
    assert f"{m0}/memories" in text
    assert "(absent)" in extra
    md5_absent = hashlib.md5(b"(absent)\n").hexdigest()
    assert f"home memories listing md5: {md5_absent}" in extra
    lines = {ln.split(": ")[0] for ln in extra if "listing md5" in ln}
    assert lines == {"home skills listing md5", "home skills-through-links listing md5", "home memories listing md5"}
    # the find -P listing shows the link targets, the find -L one reaches through them
    assert any(str(m0 / "skills/autoresearch") in ln and "|Symbolic Link|" in ln for ln in extra)
    assert any(str(m0 / "skills/autoresearch/SKILL.md") in ln and "|Regular File|" in ln for ln in extra)
    assert tree_state(tmp_path / "m0h") == before


def test_ambient_snapshot_home_with_memories_lists_them(fake_home: Path, tmp_path: Path) -> None:
    m0 = tmp_path / "m0h2" / ".kiro"
    (m0 / "skills").mkdir(parents=True)
    (m0 / "memories").mkdir()
    (m0 / "memories" / "m.db").write_text("x")
    g = snap(fake_home, "x", str(m0))
    assert any(f"{m0}/memories/m.db" in ln for ln in g)
    assert "(absent)" not in g[len(e7_snap(fake_home, "x")):]


# --------------------------------------------------------------------------------------------- skill_check.py
def load_json(p: Path) -> dict:
    return json.loads(p.read_text())


@pytest.mark.parametrize("stream,call,utc,propose,feedback", [
    ("s1", 6, "2026-10-25T07:01:29.788Z", 11, 30),
    ("s2", 2, "2026-10-25T07:42:16.597Z", 9, 31),
    ("s3", 6, "2026-10-25T08:21:56.137Z", 11, 30),
])
def test_skill_check_on_e7_streams(tmp_path: Path, stream: str, call: int, utc: str, propose: int, feedback: int) -> None:
    out = tmp_path / "o.json"
    r = run([sys.executable, "-B", str(H / "skill_check.py"), str(E7EV / stream), "--required-md5", SKILL_MD5_E7, "--json-out", str(out)],
            clean_env(tmp_path))
    assert r.returncode == 0, r.stderr
    j = load_json(out)
    assert j["stratum"] == "A"
    assert j["first_disclose"]["call"] == call and j["first_disclose"]["turn"] == 1 and j["first_disclose"]["utc"] == utc
    assert j["first_disclose"]["status"] == "completed"
    assert j["first_propose_org"]["call"] == propose and j["first_feedback"]["call"] == feedback
    assert j["disclose_calls"] == 1
    assert j["note_count"] == {"messages": 0, "tool_calls": 0}
    assert "stratum A" in r.stdout and f"CALL #{call}" in r.stdout and utc in r.stdout
    assert j["script"]["name"] == "skill_check.py" and re.fullmatch(r"[0-9a-f]{32}", j["script"]["md5"])
    assert "assistant-session-messages.jsonl" in j["source_files"]


def test_skill_check_selfcheck_mode_on_e7(tmp_path: Path) -> None:
    exp = json.loads((H / "selfcheck/e7-expected-drivers.json").read_text())
    assert isinstance(exp, list) and exp
    for e in exp:
        assert set(e) == {"stream", "key", "expected", "source"}
        assert e["stream"] in ("s1", "s2", "s3") and e["source"]
    keys = {(e["stream"], e["key"]) for e in exp}
    for s in ("s1", "s2", "s3"):
        for k in ("stratum", "first_disclose.call", "first_disclose.utc", "first_disclose.turn"):
            assert (s, k) in keys
    r = run([sys.executable, "-B", str(H / "skill_check.py"), "--selfcheck", str(E7EV), "--out", str(tmp_path / "sc")], clean_env(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    last = r.stdout.strip().splitlines()[-1]
    assert re.fullmatch(rf"selfcheck skill_check: {len(exp)} of {len(exp)} OK", last), last
    assert "MISMATCH" not in r.stdout
    for s in ("s1", "s2", "s3"):
        assert (tmp_path / "sc" / f"e7-{s}" / "skill_check.json").is_file()
        assert (tmp_path / "sc" / f"e7-{s}" / "skill_check.txt").is_file()


def test_skill_check_selfcheck_reports_a_mismatch(tmp_path: Path) -> None:
    exp = json.loads((H / "selfcheck/e7-expected-drivers.json").read_text())
    exp[0]["expected"] = "WRONG"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(exp))
    r = run([sys.executable, "-B", str(H / "skill_check.py"), "--selfcheck", str(E7EV), "--out", str(tmp_path / "sc"), "--expected", str(bad)],
            clean_env(tmp_path))
    assert r.returncode == 1
    assert "MISMATCH" in r.stdout and r.stdout.strip().splitlines()[-1] == f"selfcheck skill_check: {len(exp) - 1} of {len(exp)} OK"


def call_row(ts, tool, args, cid, kiro=None):
    p = {"type": "tool_call", "toolCallId": cid, "toolName": tool, "args": args, "status": "completed"}
    if kiro:
        p["_meta"] = {"kiro": kiro}
    return {"timestamp": ts, "id": cid, "payload": json.dumps(p)}


def res_row(ts, cid, content="ok", is_error=False):
    p = {"type": "tool_result", "toolCallId": cid, "content": content}
    if is_error:
        p["isError"] = True
    return {"timestamp": ts, "id": "r" + cid, "payload": p}


def user_row(ts, text="hi"):
    return {"timestamp": ts, "id": "u" + ts, "payload": {"type": "user", "content": text}}


def disclose(ts, cid, uri="file:///private/tmp/x/.kiro/skills/hirearchy/SKILL.md", name="hirearchy"):
    return call_row(ts, "disclose_context", {"name": name}, cid, {"toolId": "disclose_context", "disclosedContext": {"type": "skill", "displayName": name, "uri": uri}})


def propose(ts, cid, wrapped=True):
    if wrapped:
        return call_row(ts, "tool_call", {"tool_id": "hirearchy::propose_org", "arguments": {}}, cid)
    return call_row(ts, "hirearchy::propose_org", {}, cid, {"toolId": "hirearchy::propose_org"})


def feedback(ts, cid):
    return call_row(ts, "tool_call", {"tool_id": "hirearchy::feedback", "arguments": {}}, cid)


def write_stream(d: Path, rows: list[dict], tool_calls_txt: str | None = None) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "assistant-session-messages.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    if tool_calls_txt is not None:
        (d / "assistant-tool-calls.txt").write_text(tool_calls_txt)
    return d


def sc(d: Path, *extra: str) -> dict:
    out = d / "sc.json"
    r = run([sys.executable, "-B", str(H / "skill_check.py"), str(d), "--json-out", str(out), *extra], clean_env(d))
    assert r.returncode in (0, 1), r.stderr
    j = load_json(out)
    j["_rc"] = r.returncode
    j["_stdout"] = r.stdout
    return j


def test_skill_check_strata_a_b_n_na(tmp_path: Path) -> None:
    a = write_stream(tmp_path / "a", [user_row("2026-10-26T01:00:00.000Z"), disclose("2026-10-26T01:00:01.000Z", "c1"),
                                    res_row("2026-10-26T01:00:01.100Z", "c1"), propose("2026-10-26T01:00:05.000Z", "c2"),
                                    feedback("2026-10-26T01:10:00.000Z", "c3")])
    assert sc(a)["stratum"] == "A"
    b = write_stream(tmp_path / "b", [user_row("2026-10-26T01:00:00.000Z"), propose("2026-10-26T01:00:05.000Z", "c1"),
                                    disclose("2026-10-26T01:00:06.000Z", "c2"), res_row("2026-10-26T01:00:06.100Z", "c2"),
                                    feedback("2026-10-26T01:10:00.000Z", "c3")])
    jb = sc(b)
    assert jb["stratum"] == "B" and jb["first_disclose"]["call"] == 2 and jb["first_propose_org"]["call"] == 1
    b2 = write_stream(tmp_path / "b2", [user_row("2026-10-26T01:00:00.000Z"), propose("2026-10-26T01:00:05.000Z", "c2"),
                                      feedback("2026-10-26T01:10:00.000Z", "c3"),
                                      disclose("2026-10-26T01:11:00.000Z", "c4"), res_row("2026-10-26T01:11:00.100Z", "c4")])
    assert sc(b2)["stratum"] == "B"
    n = write_stream(tmp_path / "n", [user_row("2026-10-26T01:00:00.000Z"), propose("2026-10-26T01:00:05.000Z", "c1")])
    jn = sc(n)
    assert jn["stratum"] == "N" and jn["first_disclose"] is None and jn["disclose_calls"] == 0
    na = write_stream(tmp_path / "na", [user_row("2026-10-26T01:00:00.000Z"), disclose("2026-10-26T01:00:01.000Z", "c1"),
                                        res_row("2026-10-26T01:00:01.100Z", "c1")])
    jna = sc(na)
    assert jna["stratum"] == "n/a" and jna["first_propose_org"] is None and jna["first_feedback"] is None
    nn = write_stream(tmp_path / "nn", [user_row("2026-10-26T01:00:00.000Z")])
    assert sc(nn)["stratum"] == "n/a"


def test_skill_check_only_propose_or_only_feedback_counts(tmp_path: Path) -> None:
    d = write_stream(tmp_path / "p", [user_row("2026-10-26T01:00:00.000Z"), disclose("2026-10-26T01:00:01.000Z", "c1"),
                                      res_row("2026-10-26T01:00:01.100Z", "c1"), propose("2026-10-26T01:00:05.000Z", "c2", wrapped=False)])
    j = sc(d)
    assert j["stratum"] == "A" and j["first_propose_org"]["call"] == 2 and j["first_feedback"] is None


def test_skill_check_error_result_and_other_skills_do_not_count(tmp_path: Path) -> None:
    rows = [user_row("2026-10-26T01:00:00.000Z"),
            disclose("2026-10-26T01:00:01.000Z", "c1", uri="file:///x/.kiro/skills/other/SKILL.md", name="other"),
            res_row("2026-10-26T01:00:01.100Z", "c1"),
            disclose("2026-10-26T01:00:02.000Z", "c2"), res_row("2026-10-26T01:00:02.100Z", "c2", content="Error: no such skill", is_error=True),
            propose("2026-10-26T01:00:05.000Z", "c3"),
            user_row("2026-10-26T01:01:00.000Z"),
            disclose("2026-10-26T01:01:01.000Z", "c4", uri="file:///a/hirearchy/SKILL.md", name="x"), res_row("2026-10-26T01:01:01.100Z", "c4")]
    j = sc(write_stream(tmp_path / "e", rows))
    assert j["first_disclose"]["call"] == 4 and j["first_disclose"]["turn"] == 2  # matched by the uri ending /hirearchy/SKILL.md
    assert j["stratum"] == "B"
    assert j["disclose_calls"] == 3 and j["skill_disclose_calls"] == 2  # all disclose_context calls (E7's line); the calls for the skill


def test_skill_check_md5_of_the_disclosed_file_and_the_note_count(tmp_path: Path) -> None:
    skill = tmp_path / "ws" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text("skill bytes\n")
    good = hashlib.md5(b"skill bytes\n").hexdigest()
    rows = [user_row("2026-10-26T01:00:00.000Z"), disclose("2026-10-26T01:00:01.000Z", "c1", uri=f"file://{skill}"),
            res_row("2026-10-26T01:00:01.100Z", "c1", content="Note: the installed skill at /x differs"), propose("2026-10-26T01:00:05.000Z", "c2")]
    d = write_stream(tmp_path / "m", rows, tool_calls_txt="Note: the installed skill at here\nNote: the installed skill at again\n")
    j = sc(d, "--required-md5", good)
    assert j["first_disclose"]["skill_file_md5"] == good and j["first_disclose"]["valid"] is True and j["_rc"] == 0
    assert j["note_count"] == {"messages": 1, "tool_calls": 2}
    j2 = sc(d, "--required-md5", "0" * 32)
    assert j2["first_disclose"]["valid"] is False and j2["_rc"] == 1
    skill.unlink()
    j3 = sc(d, "--required-md5", good)
    assert j3["first_disclose"]["skill_file_md5"] is None and j3["first_disclose"]["valid"] is None and j3["_rc"] == 0
    assert "absent" in j3["_stdout"]


# --------------------------------------------------------------------------------------------- skill_check.sh (a copy, tmp_path)
def make_skill_check_env(tmp_path: Path, fake_home: Path, arm: str, m0_copy: str | None):
    ev = tmp_path / "evidence"
    label = f"{arm}-s1"
    sdir = ev / label
    sdir.mkdir(parents=True)
    S = tmp_path / "sandbox"
    (S / ".kiro/skills/hirearchy").mkdir(parents=True)
    (S / ".kiro/skills/hirearchy/SKILL.md").write_bytes((REPO / "skills/hirearchy/SKILL.md").read_bytes())
    (sdir / "sandbox-path.txt").write_text(str(S) + "\n")
    if arm == "m0":
        m0h = tmp_path / "m0h"
        (m0h / ".kiro/skills").mkdir(parents=True)
        if m0_copy is not None:
            (m0h / ".kiro/skills/hirearchy").mkdir()
            (m0h / ".kiro/skills/hirearchy/SKILL.md").write_text(m0_copy) if m0_copy != "repo" else \
                (m0h / ".kiro/skills/hirearchy/SKILL.md").write_bytes((REPO / "skills/hirearchy/SKILL.md").read_bytes())
        (sdir / "m0-home-path.txt").write_text(str(m0h) + "\n")
    script = sed_copy(H / "skill_check.sh", tmp_path / "skill_check_copy.sh", {r"^EV=.*$": f"EV={ev}", r"^H=.*$": f"H={H}"})
    return script, sdir, label, S


def sk_run(script: Path, label: str, mode: str, home: Path) -> subprocess.CompletedProcess:
    return run(["zsh", str(script), label, mode], clean_env(home))


def test_skill_check_sh_m1_rules(tmp_path: Path, fake_home: Path) -> None:
    script, sdir, label, S = make_skill_check_env(tmp_path, fake_home, "m1", None)
    r = sk_run(script, label, "setup", fake_home)
    assert r.returncode == 0, r.stdout + r.stderr
    t = (sdir / "skill-check.txt").read_text()
    assert SKILL_MD5 in t and "verdict: OK" in t and "arm: m1" in t and "lines 125" in t
    # global differs from the workspace copy: invalid
    (fake_home / ".kiro/skills/hirearchy/SKILL.md").write_text("changed\n")
    r = sk_run(script, label, "setup", fake_home)
    assert r.returncode == 1 and "INVALID (H2)" in (sdir / "skill-check.txt").read_text()
    # global absent: valid for M1
    (fake_home / ".kiro/skills/hirearchy/SKILL.md").unlink()
    r = sk_run(script, label, "setup", fake_home)
    assert r.returncode == 0 and "global (md5 only): absent" in (sdir / "skill-check.txt").read_text()
    # the workspace copy differs from the repo's: invalid
    (S / ".kiro/skills/hirearchy/SKILL.md").write_text("x\n")
    assert sk_run(script, label, "setup", fake_home).returncode == 1


@pytest.mark.parametrize("global_present,m0_copy,ok", [
    (True, "repo", True), (True, None, False), (True, "other bytes\n", False), (False, None, True), (False, "repo", False),
])
def test_skill_check_sh_m0_rules(tmp_path: Path, fake_home: Path, global_present: bool, m0_copy, ok: bool) -> None:
    script, sdir, label, S = make_skill_check_env(tmp_path, fake_home, "m0", m0_copy)
    if not global_present:
        (fake_home / ".kiro/skills/hirearchy/SKILL.md").unlink()
    r = sk_run(script, label, "setup", fake_home)
    t = (sdir / "skill-check.txt").read_text()
    assert (r.returncode == 0) == ok, t
    assert ("verdict: OK" in t) == ok
    assert "M0 copy" in t


def test_skill_check_sh_turn1_adds_the_disclosure(tmp_path: Path, fake_home: Path) -> None:
    script, sdir, label, S = make_skill_check_env(tmp_path, fake_home, "m1", None)
    skill = S / ".kiro/skills/hirearchy/SKILL.md"
    rows = [user_row("2026-10-26T01:00:00.000Z"), disclose("2026-10-26T01:00:01.000Z", "c1", uri=f"file://{skill}"),
            res_row("2026-10-26T01:00:01.100Z", "c1"), propose("2026-10-26T01:00:05.000Z", "c2")]
    (sdir / "assistant-session-messages.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    r = sk_run(script, label, "turn1", fake_home)
    assert r.returncode == 0, r.stdout + r.stderr
    t = (sdir / "skill-check.txt").read_text()
    assert "first disclose_context call for the skill: CALL #1, turn 1" in t and "stratum A" in t and "verdict: OK" in t
    # a disclosed file with other bytes: invalid
    skill.write_text("tampered\n")
    r = sk_run(script, label, "turn1", fake_home)
    assert r.returncode == 1 and "INVALID (H2)" in (sdir / "skill-check.txt").read_text()


def test_skill_check_sh_usage(tmp_path: Path, fake_home: Path) -> None:
    script, sdir, label, S = make_skill_check_env(tmp_path, fake_home, "m1", None)
    assert run(["zsh", str(script), label, "bogus"], clean_env(fake_home)).returncode == 2
    assert run(["zsh", str(script)], clean_env(fake_home)).returncode == 2


# --------------------------------------------------------------------------------------------- copy_org_evidence.sh: memos/versions
def git(org: Path, *a: str, date: str | None = None) -> str:
    env = clean_env(org.parent, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    if date:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = date
    r = run(["git", "-C", str(org), *a], env)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_copy_org_evidence_leaves_memos_versions_to_extract_mechanical() -> None:
    """Protocol 15 item 14: memos/versions/ has ONE writer, extract_mechanical.py, with E7's rule (every .md under the owner's */work/ folders
    except the final-check seat's), run by finish_stream.sh after copy_org_evidence.sh. copy_org_evidence.sh must not write it."""
    copy = (H / "copy_org_evidence.sh").read_text()
    code = "\n".join(ln for ln in copy.splitlines() if not ln.lstrip().startswith("#"))
    assert "memos/versions" not in code and "INDEX.txt" not in code
    em = (H / "extract_mechanical.py").read_text()
    assert '"memos" / "versions" / "INDEX.txt"' in em and '"/work/" in x' in em and "seat_path" in em
    fin = (H / "finish_stream.sh").read_text()
    assert fin.index("step copy_org_evidence") < fin.index("step extract_mechanical")


def test_copy_org_evidence_keeps_every_e7_line() -> None:
    e7 = (E7H / "copy_org_evidence.sh").read_text().splitlines()
    g0 = (H / "copy_org_evidence.sh").read_text().splitlines()
    kept = [ln for ln in e7 if not ln.startswith("#") and "EV=" not in ln and ln.strip() != ""]
    for ln in kept:
        assert ln in g0, f"E7 line lost: {ln[:100]}"
