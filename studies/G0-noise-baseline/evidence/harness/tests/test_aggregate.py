"""Tests of aggregate.py (design 20.5): the table maths and the n/a rules, on synthetic stream dirs in tmp_path.

A stream dir needs only what the test gives it: arm.txt, measures/*.json, measures/validity.json, measures/judged.json, quality/end.json,
rederived/mismatches.txt. A missing file makes its cells `missing` (never a value)."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
sys.dont_write_bytecode = True
SCRIPT = HARNESS / "aggregate.py"
TEMPLATE = HARNESS / "judged-template.json"
PY = sys.executable


def run(*args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([PY, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=env)


def mk_stream(root: Path, label, arm=None, stratum="A", copies=4, hand=(0, 4), decisions=(8, 8), bytes_first=20000, valid=True, why="", skip=()):
    d = root / label
    (d / "measures").mkdir(parents=True)
    if arm is not None:
        (d / "arm.txt").write_text(arm + "\n")
    af = {"measures": {"skill_stratum": stratum, "copies": copies, "hand_edits": {"k": hand[0], "n": hand[1]}, "p2_unrated": 1, "wall_time": "34:25",
                       "plans_with_budget_line": {"k": 0, "n": 1}, "assistant_credits": 25.3791, "schedulers_running_at_turn_end": {"k": 0, "n": 0}}}
    sm = {"final_totals": {"decisions": {"k": decisions[0], "n": decisions[1]}, "actions": {"k": 15, "n": 15}, "wrong_dates": 0, "extra_rows": 0, "summary": {"k": 3, "n": 3}},
          "delivered": {"k": 4, "n": 8}}
    ps = {"bytes": {"first": bytes_first, "max": bytes_first + 10000, "last": bytes_first + 5000, "last_minus_first": 5000}, "reflect_words": {"max": 600, "min": 500, "sections": 3}}
    docs = {"assistant_facts.json": af, "score_memos.json": sm, "prompt_sizes.json": ps}
    for name, doc in docs.items():
        if name not in skip:
            (d / "measures" / name).write_text(json.dumps(doc))
    (d / "measures" / "validity.json").write_text(json.dumps({"valid": valid, "reason": why}))
    return d


# ------------------------------------------------------------------ the maths
def test_median_of_an_odd_and_an_even_count():
    import aggregate as ag
    assert ag.median([3, 1, 2]) == 2
    assert ag.median([4, 1, 2, 3]) == 2.5  # the mean of the two middle values
    assert ag.median([5]) == 5


def test_numeric_spread_is_min_median_max_and_trims_floats():
    import aggregate as ag
    assert ag.spread_num([20, 21, 25]) == "20 / 21 / 25"
    assert ag.spread_num([1.5, 2.0, 4.0, 8.0]) == "1.5 / 3 / 8"
    assert ag.fmt(25.37910) == "25.3791" and ag.fmt(3.0) == "3" and ag.fmt(0.0001) == "0.0001"


def test_a_rate_renders_k_of_n_and_zero_denominators_render_n_a():
    import aggregate as ag
    assert ag.show_rate({"k": 2, "n": 11}) == "2 of 11"
    assert ag.show_rate({"k": 0, "n": 0}) == "n/a (0 of 0)"
    assert ag.pool_rates([{"k": 1, "n": 4}, {"k": 0, "n": 3}, {"k": 1, "n": 4}]) == {"k": 2, "n": 11}
    assert ag.show_rate(ag.pool_rates([{"k": 0, "n": 0}, {"k": 0, "n": 0}])) == "n/a (0 of 0)"


def test_a_cell_with_fewer_than_three_streams_reports_its_values_and_n_a_k_of_3():
    import aggregate as ag
    assert ag.cell("num", [20, 25]) == "20; 25; spread n/a (2 of 3)"
    assert ag.cell("num", [20]) == "20; spread n/a (1 of 3)"
    assert ag.cell("num", [20, 21, 25]) == "20 / 21 / 25"
    assert ag.cell("rate", [{"k": 1, "n": 4}, {"k": 0, "n": 3}]) == "1 of 4; 0 of 3; spread n/a (2 of 3)"
    assert ag.cell("rate", [{"k": 1, "n": 4}, {"k": 0, "n": 3}, {"k": 1, "n": 4}]) == "2 of 11"
    assert ag.cell("bin", [True, False, True]) == "2 of 3"
    assert ag.cell("bin", [True, False]) == "yes; no; spread n/a (2 of 3)"
    assert ag.cell("cat", ["A", "A", "B"]) == "A 2, B 1"
    assert ag.cell("num", []) == "n/a (0 of 0)"


def test_missing_values_are_left_out_and_counted():
    import aggregate as ag
    assert ag.cell("num", [20, 21, 25], missing=1) == "20 / 21 / 25 (1 missing)"
    assert ag.cell("num", [], missing=2) == "missing (all 2 streams)"


# ------------------------------------------------------------------ whole tables
def test_streams_are_grouped_by_arm_and_stratum_and_the_spread_columns_follow(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    for i, (arm, st, first) in enumerate([("m0", "A", 20000), ("m0", "A", 21000), ("m0", "A", 25000), ("m1", "A", 22000), ("m1", "B", 23000), ("m1", "A", 24000)], 1):
        mk_stream(root, f"{arm}-s{i}", arm=arm, stratum=st, bytes_first=first)
    out = tmp_path / "baseline.md"
    r = run(root, "--out", out)
    assert r.returncode == 0, r.stderr
    md = out.read_text()
    assert "## A. Team layer" in md and "## B. Assistant layer" in md and "## C. Product layer" in md
    row = next(l for l in md.splitlines() if l.startswith("| Lead prompt bytes, first"))
    cells = [c.strip() for c in row.strip("|").split("|")]
    # streams in arm, stratum, label order: m0-s1 m0-s2 m0-s3 (M0/A) then m1-s4 m1-s6 (M1/A) then m1-s5 (M1/B)
    hdr = next(l for l in md.splitlines() if l.startswith("| Measure |") and "m0-s1" in l)
    cols = [c.strip() for c in hdr.strip("|").split("|")]
    assert cols[1].startswith("m0-s1") and cols[3].startswith("m0-s3") and cols[4].startswith("m1-s4") and cols[5].startswith("m1-s6") and cols[6].startswith("m1-s5")
    by = dict(zip(cols, cells))
    assert by["M0"] == "20000 / 21000 / 25000"            # three M0 streams: a spread
    assert by["M1"] == "22000 / 23000 / 24000"
    assert by["M0 x A"] == "20000 / 21000 / 25000"
    assert by["M1 x B"] == "23000; spread n/a (1 of 3)"   # fewer than 3 streams: the value and n/a (k of 3)
    assert by["M1 x A"] == "22000; 24000; spread n/a (2 of 3)"
    assert by["A"] == "20000 / 22000 / 25000" or by["A"].count("/") == 2
    assert by["all valid"].count("/") == 2


def test_a_rate_row_pools_k_and_n_and_a_zero_denominator_stays_n_a(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    for i in range(1, 4):
        mk_stream(root, f"m0-s{i}", arm="m0", hand=(0, 4))
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    md = out.read_text()
    hdr = next(l for l in md.splitlines() if l.startswith("| Measure |") and "m0-s1" in l)
    cols = [c.strip() for c in hdr.strip("|").split("|")]
    row = next(l for l in md.splitlines() if l.startswith("| Copies that were hand edits"))
    by = dict(zip(cols, [c.strip() for c in row.strip("|").split("|")]))
    assert by["m0-s1 (M0/A)"] == "0 of 4" and by["M0"] == "0 of 12" and by["all valid"] == "0 of 12"
    row = next(l for l in md.splitlines() if l.startswith("| Schedulers running at the end of a turn"))
    by = dict(zip(cols, [c.strip() for c in row.strip("|").split("|")]))
    assert by["m0-s1 (M0/A)"] == "n/a (0 of 0)" and by["M0"] == "n/a (0 of 0)"


def test_a_missing_measures_file_reports_missing_and_never_a_value(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    mk_stream(root, "m0-s1", arm="m0")
    mk_stream(root, "m0-s2", arm="m0", skip=("prompt_sizes.json",))
    mk_stream(root, "m0-s3", arm="m0")
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    md = out.read_text()
    hdr = next(l for l in md.splitlines() if l.startswith("| Measure |") and "m0-s1" in l)
    cols = [c.strip() for c in hdr.strip("|").split("|")]
    row = next(l for l in md.splitlines() if l.startswith("| Lead prompt bytes, first"))
    by = dict(zip(cols, [c.strip() for c in row.strip("|").split("|")]))
    assert by["m0-s2 (M0/A)"] == "missing (no measures/prompt_sizes.json)"
    assert by["M0"] == "20000; 20000; spread n/a (2 of 3) (1 missing)"


def test_an_invalid_stream_is_listed_and_left_out_of_the_spread(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    for i, first in enumerate([20000, 21000, 22000], 1):
        mk_stream(root, f"m0-s{i}", arm="m0", bytes_first=first)
    mk_stream(root, "m0-s4", arm="m0", bytes_first=99999, valid=False, why="H1: a turn exited 1")
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    md = out.read_text()
    assert "Invalid streams" in md and "m0-s4" in md and "H1: a turn exited 1" in md
    hdr = next(l for l in md.splitlines() if l.startswith("| Measure |") and "m0-s1" in l)
    cols = [c.strip() for c in hdr.strip("|").split("|")]
    row = next(l for l in md.splitlines() if l.startswith("| Lead prompt bytes, first"))
    by = dict(zip(cols, [c.strip() for c in row.strip("|").split("|")]))
    assert by["all valid"] == "20000 / 21000 / 22000" and "99999" not in by["M0"]
    assert any("invalid" in c and "m0-s4" in c for c in cols)  # its own column still shows its values, marked invalid


def test_judged_rows_come_from_the_template_and_judged_json(tmp_path):
    tpl = json.loads(TEMPLATE.read_text())
    key = next(t["key"] for t in tpl["measures"] if t["type"] == "rate")
    root = tmp_path / "ev"
    root.mkdir()
    for i in range(1, 4):
        d = mk_stream(root, f"m0-s{i}", arm="m0")
        (d / "measures" / "judged.json").write_text(json.dumps({key: {"k": i, "n": 4}}))
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    label = next(t["label"] for t in tpl["measures"] if t["key"] == key)
    row = next(l for l in out.read_text().splitlines() if l.startswith(f"| {label}"))
    assert "6 of 12" in row and "1 of 4" in row


def test_unjudged_streams_show_not_yet_judged_never_a_default(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    mk_stream(root, "m0-s1", arm="m0")
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    tpl = json.loads(TEMPLATE.read_text())
    label = tpl["measures"][0]["label"]
    row = next(l for l in out.read_text().splitlines() if l.startswith(f"| {label}"))
    assert "missing (no measures/judged.json)" in row


def test_streams_option_selects_streams_and_default_discovers_g0_labels(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    for lab, arm in (("m0-s1", "m0"), ("m1-s1", "m1"), ("m0-s2", "m0")):
        mk_stream(root, lab, arm=arm)
    (root / "notes").mkdir()
    (root / "harness").mkdir()
    out = tmp_path / "b.md"
    assert run(root, "--out", out, "--streams", "m0-s1,m1-s1").returncode == 0
    md = out.read_text()
    assert "m0-s2" not in md and "m0-s1" in md and "m1-s1" in md
    assert run(root, "--out", out).returncode == 0
    assert "m0-s2" in out.read_text()


def test_the_arm_comes_from_arm_txt_else_the_label_prefix_else_e7(tmp_path):
    import aggregate as ag
    root = tmp_path / "ev"
    root.mkdir()
    a = mk_stream(root, "m1-s7", arm="m0")  # arm.txt wins
    b = mk_stream(root, "m1-s8")
    c = mk_stream(root, "s1")
    assert ag.Stream(a).arm == "m0" and ag.Stream(b).arm == "m1" and ag.Stream(c).arm == "e7"


def test_a_malformed_json_is_a_missing_cell_with_a_reason(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    d = mk_stream(root, "m0-s1", arm="m0")
    (d / "measures" / "prompt_sizes.json").write_text("{not json")
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    row = next(l for l in out.read_text().splitlines() if l.startswith("| Lead prompt bytes, first"))
    assert "missing (unreadable measures/prompt_sizes.json)" in row


def test_the_note_states_the_median_rule_and_the_n_a_rule(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    mk_stream(root, "m0-s1", arm="m0")
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    md = out.read_text()
    assert "mean of the two middle values" in md and "n/a (k of 3)" in md and "min / median / max" in md


def test_product_layer_counts_come_from_quality_json_and_the_rederivation(tmp_path):
    root = tmp_path / "ev"
    root.mkdir()
    d = mk_stream(root, "m0-s1", arm="m0")
    (d / "quality").mkdir()
    (d / "quality" / "end.json").write_text(json.dumps({"schema": 1, "services": [{
        "cases": [{"id": "c1", "user_cost": 15, "runs": 20, "relayed_runs": 5}, {"id": "c2", "user_cost": 5, "runs": 5, "relayed_runs": 0}],
        "first_deliveries": {"accepted": 2, "rejected": 1, "no_verdict": 0, "superseded": 0, "neither": 0, "never_delivered": 0},
        "deliveries": {"total": 4, "judged": 3, "unjudged_cases": [], "relayed_only": [], "unseen_relayed": ["x"], "not_as_delivered": [], "neither": [], "legacy_verdicts": 0, "not_on_a_delivery": []},
        "escapes": [{"cause": "reviewer-miss"}, {"cause": "reviewer-miss"}, {"cause": "ambiguity"}], "verifiers": [{"addr": "lead/reviewer", "judged": 3}],
        "alarms": {"repeat": {"state": "no"}, "cost": {"state": "fires"}}, "timeline": [{"kind": "contract"}, {"kind": "playbook"}, {"kind": "top-up"}]}],
        "moved_past": [], "nested": [], "one_off": None}))
    (d / "rederived").mkdir()
    (d / "rederived" / "mismatches.txt").write_text("MISMATCH services.0.cases.0.runs: product=20 rederived=19\ncompared 210 keys, 1 mismatches\n")
    out = tmp_path / "b.md"
    assert run(root, "--out", out).returncode == 0
    md = out.read_text()
    c = md.split("## C. Product layer")[1]
    row = lambda start: next(l for l in c.splitlines() if l.startswith(start))  # noqa: E731
    assert "| 2 |" in row("| Cases") or "2" in row("| Cases")
    assert "| 4 |" in row("| Deliveries, total") or "4" in row("| Deliveries, total")
    assert "3" in row("| Escapes, total")
    assert "reviewer-miss" in c and "yes" in row("| Cost alarm fires")
    assert "1" in row("| Re-derivation mismatches") and "210" in row("| Re-derivation keys compared")
    assert "25" in row("| Case runs (sum)") and "20" in row("| User runs (sum of user_cost)")


def test_the_template_lists_every_judged_measure_with_key_definition_and_type():
    tpl = json.loads(TEMPLATE.read_text())
    keys = [t["key"] for t in tpl["measures"]]
    assert len(keys) == len(set(keys)) and len(keys) >= 15
    for t in tpl["measures"]:
        assert set(t) >= {"key", "label", "layer", "definition", "type"} and t["layer"] in ("A", "B", "C")
        assert t["type"] in ("rate", "binary", "count", "enum", "text", "number")
        assert t["definition"].strip()
        if t["type"] == "enum":
            assert t["values"]
