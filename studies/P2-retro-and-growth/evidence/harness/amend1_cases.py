#!/usr/bin/env python3
"""P2 protocol amendment 1: the harness items' constructed cases (`../protocol-amendment-1.md` item 5; `selfcheck.sh` part "amendment 1").

    python3 -B amend1_cases.py --scratch DIR --product-src SRC      every case; the last line `amend1_cases: <k> of <n> ok`; exit 0 iff all

Written test-first: each case was run on the harness as frozen before amendment 1 (RED) and after the fix (GREEN); both lines are in
`CHANGES.md` and `../harness-selfcheck/SELFCHECK.md` ("Amendment 1").
  (A) turn.sh's sequence check (protocol 3.2): a first snapshot time with a `+00:00` offset before the boundary must STOP; an unparseable time
      must STOP (fail closed); a `+00:00` time after the boundary reads `checked` with the comparison; no snapshot record and no `no org yet`
      record must STOP. The first three run through turn.sh itself (a selfcheck label, the fake chat, a 1-s boundary); the others call the
      check the wrapper runs.
  (B) the finish's org-run cost path (protocol 3.5, finish_stream.sh's `EM_ARGV`): on a constructed stream whose effort-stopped run's session
      folder holds `session.json` and no `messages.jsonl` (the run log carries `# kiro: effort not set`), cost.txt is written, the stop is
      counted in it and cost_total.py gives a figure; the same folder without the effort mark fails closed (no cost.txt); P1's
      extract_mechanical.py stays byte-identical to its pin.
  (C) the injection wrapper (protocol 3.4; E7 5.3's last bullet): injection.sh writes `S/injection/window.txt` from the injection log with no
      facilitator step; a log without a window end writes none; `--stop` writes none; an existing different window.txt is kept.
  (D) the manager's D1 (`../manager-decision-row-R1-t7.md`, "Amendment 1's review: rulings"): arm.sh's md5gate_ok, called in isolation on
      a constructed EV copy, gates every `protocol-amendment-*.md` and `standing-rules-streams-amendment-*.md` against its `.md5`: a missing
      or different `.md5` fails, matching passes, and no amendment file at all passes as before. The real `.md5` files are never written.
Every case runs under DIR (under /tmp/hirearchy-p2/): no stream, no live kiro-cli session, no org, no product source file opened. (B)'s
extract imports the product's `client_questions` from SRC as the finish does (P1's one stated product import)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
EXTRACT_PIN = "73b27e25bd18ea9ec17ad5e64c7f6d1c"  # P1's extract_mechanical.py line in P1's MD5SUMS and in P2's harness/MD5SUMS
sys.dont_write_bytecode = True
sys.path.insert(0, str(H))

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def run(argv, env=None, cwd=None):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    e.pop("KIRO_HOME", None)
    e.update(env or {})
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, env=e, cwd=cwd)


# ---------------------------------------------------------------- (A) turn.sh's sequence check
FAKE_CHAT = '#!/bin/zsh\necho "fake reply to: ${@[-1]}"\n'


def wrapper_world(root: Path, calls_line: str | None) -> Path:
    if root.exists():
        shutil.rmtree(root)
    (root / "bin").mkdir(parents=True)
    (root / "ev" / "quality").mkdir(parents=True)
    (root / "S").mkdir()
    (root / "bin" / "kiro-cli").write_text(FAKE_CHAT)
    (root / "bin" / "kiro-cli").chmod(0o755)
    (root / "ev" / "sandbox-path.txt").write_text(f"{root / 'S'}\n")
    (root / "prompt.txt").write_text("Hello.\n")
    if calls_line is not None:
        (root / "ev" / "quality" / "calls.txt").write_text(calls_line + "\n")
    return root


def wrapper_last_line(root: Path) -> str:
    r = run(["zsh", H / "turn.sh", "selfcheck-R", "1", root / "prompt.txt"],
            env={"P2_EVDIR": str(root / "ev"), "P2_KIRO_CLI": str(root / "bin" / "kiro-cli"), "P2_BOUNDARY": "1"})
    w = root / "ev" / "turn-01.wrapper.txt"
    lines = w.read_text().splitlines() if w.exists() else []
    return lines[-1] if lines else f"(no wrapper record; exit {r.returncode}; {r.stderr.strip()[:200]})"


def cases_a(scratch: Path) -> None:
    base = scratch / "A"
    last = wrapper_last_line(wrapper_world(base / "a1", "turn-01 start 2020-01-01T00:00:00.000000+00:00 end 2020-01-01T00:00:01.000000+00:00 exit 0 bytes 1 json ok product x"))
    check("(A) turn.sh: a first snapshot at 2020-01-01T00:00:00.000000+00:00, before the turn's end + boundary: STOP", last.startswith("STOP: snapshot before the boundary"), last)
    last = wrapper_last_line(wrapper_world(base / "a2", "turn-01 start 2026-13-45Tnot-a-time end x exit 0 bytes 1 json ok product x"))
    check("(A) turn.sh: an unparseable snapshot time: STOP (fail closed)", last.startswith("STOP:") and "unparseable" in last, last)
    last = wrapper_last_line(wrapper_world(base / "a3", "turn-01 start 2099-01-01T00:00:00.000000+00:00 end 2099-01-01T00:00:01.000000+00:00 exit 0 bytes 1 json ok product x"))
    check("(A) turn.sh: a first snapshot at 2099-01-01T00:00:00.000000+00:00, after the boundary: checked, with the comparison",
          last.startswith("after_turn sequential: checked (turn end ") and "2099-01-01T00:00:00+00:00" in last, last)
    # the check the wrapper runs, called directly (the cases turn.sh's own run cannot construct: after_turn always writes a record)
    seq = H / "turn_seqcheck.py"
    tt = "turn 3: 10:41:57 - 10:44:32  1-0=155s  utc 2026-10-29T10:41:57Z - 2026-10-29T10:44:32Z  exit 0  sleep 20 ended utc 2026-10-29T10:44:52Z\n"

    def direct(name: str, times: str, calls: str | None) -> str:
        d = base / name
        if d.exists():
            shutil.rmtree(d)
        (d / "quality").mkdir(parents=True)
        (d / "turn-times.txt").write_text(times)
        if calls is not None:
            (d / "quality" / "calls.txt").write_text(calls)
        r = run([sys.executable, "-B", seq, d, "3"])
        return (r.stdout.strip().splitlines() or [f"(no output; exit {r.returncode}; {r.stderr.strip()[:200]})"])[-1]
    out = direct("u1", tt, "turn-03 start 2026-10-29T10:44:53.169316+00:00 end 2026-10-29T10:44:53.484650+00:00 exit 0 bytes 8096 json ok\n")
    check("(A) R1 v1's turn-3 record form (+00:00, 1.17 s after the boundary): checked, with the comparison",
          out.startswith("after_turn sequential: checked (turn end 2026-10-29T10:44:32+00:00 + 20 s <= first snapshot 2026-10-29T10:44:53.169316+00:00)"), out)
    out = direct("u2", tt, "turn-03 start 2026-10-29T10:44:51.900000+00:00 end x\n")
    check("(A) a +00:00 snapshot 0.1 s before the boundary: STOP", out.startswith("STOP: snapshot before the boundary"), out)
    out = direct("u3", tt, "turn-03 start 2026-10-29T10:44:53Z end x\n")
    check("(A) a Z time still parses: checked", out.startswith("after_turn sequential: checked (turn end"), out)
    out = direct("u4", tt, "turn-03 2026-10-29T10:44:53Z: no org yet, quality not run\n")
    check("(A) the snapshot's own `no org yet` record: checked (no snapshot taken: no org yet)", out == "after_turn sequential: checked (no snapshot taken: no org yet)", out)
    out = direct("u5", tt, "turn-02 2026-10-29T10:41:41Z: no org yet, quality not run\n")
    check("(A) no record of this turn's snapshot at all: STOP (fail closed)", out.startswith("STOP:"), out)
    out = direct("u6", tt, None)
    check("(A) no quality/calls.txt: STOP (fail closed)", out.startswith("STOP:"), out)
    out = direct("u7", tt.replace("2026-10-29T10:44:32Z", "2026-10-29T25:44:32Z"), "turn-03 start 2026-10-29T10:44:53Z end x\n")
    check("(A) an unparseable turn end in turn-times.txt: STOP (fail closed)", out.startswith("STOP:") and "unparseable" in out, out)


# ---------------------------------------------------------------- (B) the finish's org-run cost path on an effort-stopped session
def msg(path: Path, hdr: dict, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(f"{k}: {v}" for k, v in hdr.items()) + f"\n---\n{body}")


def cost_world(d: Path, effort_mark: bool) -> Path:
    """A stream dir in P1's no-sandbox form (P1's tests' synthetic stream, P2's names): two org runs, `boss` (a normal session with 2.5
    credits) and `boss-scribe` (stopped after 12 s with exit -9; its session folder holds session.json only)."""
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "sandbox-path.txt").write_text("/tmp/hirearchy-p2/selfcheck-amend1-none\n")
    ts = "2026-11-01T10:00:00.000Z"
    rows = [{"timestamp": ts, "payload": {"type": "user", "content": "hi"}}, {"timestamp": ts, "payload": {"type": "turn_start"}},
            {"timestamp": "2026-11-01T10:00:05.000Z", "payload": {"type": "turn_end"}}]
    (d / "assistant-session-messages.jsonl").write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    (d / "turn-times.txt").write_text("turn 1: 10:00:00 - 10:00:05  1-0=5s  utc 2026-11-01T10:00:00Z - 2026-11-01T10:00:05Z  exit 0  sleep 20 ended utc 2026-11-01T10:00:25Z\n")
    (d / "session-turn-times-utc.txt").write_text("turn 1: user_ts x turn_start 2026-11-01T10:00:00.000Z turn_end 2026-11-01T10:00:05.000Z stop end_turn "
                                                  "status success elapsed_ms 5000 credits 1.0000\ntotal assistant credits: 1.0000\n")
    (d / "lena-lines.txt").write_text("turn 1 | rules H1 | table rows none | facts: x\n")
    (d / "turn-01.prompt.txt").write_text("Hi\n")
    (d / "events" / "2026-11-01").mkdir(parents=True)
    (d / "memos").mkdir()
    msg(d / "msgs" / "sent" / "20261101T100001000000-root-aaaa.md",
        {"id": "20261101T100001000000-root-aaaa", "from": "root", "to": "boss", "type": "task", "created": "'2026-11-01T10:00:01+00:00'", "service": "daily-brief"})
    runs = {"boss": ("20261101T100002000000", "2026-11-01T10:00:02.500Z", "ok\n# exit 0 after 5s\n", 2.5),
            "boss-scribe": ("20261101T100003000000", "2026-11-01T10:00:03.500Z",
                            ("# kiro: effort not set, run stopped (kiro-cli: failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort "
                             "levels); tool effects: none\n" if effort_mark else "") + "# exit -9 after 12s\n", None)}
    for agent, (stamp, created, tail, usage) in runs.items():
        cwd = f"/state/kiro-cwd/orgid/{agent}-1"
        (d / "run-logs" / agent).mkdir(parents=True, exist_ok=True)
        (d / "run-logs" / agent / f"{stamp}.log").write_text(
            f"# run of {agent}\n# cwd: {cwd}\n# cmd: x --agent prof --model claude-sonnet-5.5 --effort high\n# ---- prompt ----\nPROMPT\n# ---- output ----\n{tail}")
        sd = d / "org-kiro-sessions" / "h0" / f"sess_{agent}"
        sd.mkdir(parents=True)
        (sd / "session.json").write_text(json.dumps({"id": f"sess_{agent}", "agentMode": "prof", "workspacePaths": [cwd], "createdAt": created,
                                                     "modelId": "claude-sonnet-5.5"}))
        if usage is not None:
            (sd / "messages.jsonl").write_text(json.dumps({"payload": {"type": "usage_summary", "promptTurnSummaries": [{"usage": usage}]}}) + "\n")
    (d / "org-files").mkdir()
    (d / "org-files" / "boss-inspector-AGENT.md").write_text("You review and check the work.\n")
    return d


def finish_extract_argv() -> list[str]:
    """The extract command finish_stream.sh runs (its `EM_ARGV=(python3 -B $H0/<script> $D $S --product-src $REPO_A/src)` line)."""
    m = re.search(r"^EM_ARGV=\(python3 -B \$H0/(\S+) ", (H / "finish_stream.sh").read_text(), re.M)
    return [sys.executable, "-B", str(H / m.group(1))] if m else []


def cases_b(scratch: Path, product_src: str) -> None:
    import cost_total
    argv = finish_extract_argv()
    check("(B) finish_stream.sh names its extract command (EM_ARGV)", bool(argv), str(argv))
    d = cost_world(scratch / "B" / "stop", effort_mark=True)
    r = run([*argv, d, "-", "--product-src", product_src])
    cost = d / "cost.txt"
    text = cost.read_text() if cost.exists() else ""
    check("(B) an effort-stopped run's session with no messages.jsonl: the finish's extract exits 0 and writes cost.txt",
          r.returncode == 0 and cost.exists(), f"exit {r.returncode}; {(r.stderr.strip().splitlines() or [''])[-1][:200]}")
    m = re.search(r"^effort stops read as empty sessions \(.*?\): (\d+) \((.*)\)$", text, re.M)
    check("(B) cost.txt counts the stop: 1 (boss-scribe's run -> sess_boss-scribe)",
          bool(m) and m.group(1) == "1" and "sess_boss-scribe" in m.group(2) and "20261101T100003000000" in m.group(2), m.group(0) if m else "(no count line)")
    ln = cost_total.line_of(text) if text else None
    check("(B) cost_total.py's figure from that cost.txt: 3.50 (assistant 1.00 + org runs 2.50; the stop 0 credits, no estimate)",
          ln == "stream total credits: 3.50 (assistant 1.00 + org runs 2.50)", str(ln))
    smap = (d / "run-session-map.txt").read_text() if (d / "run-session-map.txt").exists() else ""
    check("(B) the stopped run stays matched to its session (credits 0.000000), so no run counts as unmatched",
          bool(re.search(r"20261101T100003000000 model=claude-sonnet-5.5 exit=-9 secs=12 -> session sess_boss-scribe credits 0.000000", smap))
          and "unmatched runs: []" in smap, smap[-300:])
    d2 = cost_world(scratch / "B" / "nomark", effort_mark=False)
    r2 = run([*argv, d2, "-", "--product-src", product_src])
    unv = d2 / "cost.txt.unverified"
    check("(B) the same folder with no effort mark in its run log: fail closed (exit != 0, no cost.txt; the extract's file kept as "
          "cost.txt.unverified with a FAIL-CLOSED line naming the session)",
          r2.returncode != 0 and not (d2 / "cost.txt").exists() and unv.exists() and "FAIL-CLOSED" in unv.read_text() and "sess_boss-scribe" in unv.read_text(),
          f"exit {r2.returncode}; {(r2.stdout + r2.stderr).strip()[-300:]}")
    got = run(["md5", "-q", H / "extract_mechanical.py"]).stdout.strip()
    check(f"(B) P1's extract_mechanical.py is byte-identical to its pin ({EXTRACT_PIN})", got == EXTRACT_PIN, got)


# ---------------------------------------------------------------- (C) the injection wrapper writes window.txt
FAKE_UV = r'''#!/usr/bin/env python3
# a stand-in for `uv --directory <repo> run python <injection script> ... --out <dir> [mode]`: writes E7's log lines, makes no product call
import sys, pathlib
a = sys.argv[1:]
out = pathlib.Path(a[a.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
mode = pathlib.Path(sys.argv[0]).parent.joinpath("mode").read_text().strip()
lines = ["## INJECTION script md5 x", "started: 2026-10-29T10:48:27Z (local 10:48:27 WET)", "injected task id: 20261029T104827993019-root-269a",
         "window start (request): 2026-10-29T10:48:27Z (local 10:48:27 WET)",
         "--- progress at 2026-10-29T10:50:27Z (local 10:50:27 WET) -> reply at 2026-10-29T10:50:27Z (local 10:50:27 WET)"]
if mode != "no-end":
    lines.append("window end (final progress): 2026-10-29T10:50:27Z (local 10:50:27 WET)")
with open(out / "injection-log.txt", "a") as f:
    f.write("\n".join(lines) + "\n")
print("fake injection:", " ".join(a))
'''


def inj_world(root: Path, mode: str) -> Path:
    if root.exists():
        shutil.rmtree(root)
    (root / "bin").mkdir(parents=True)
    (root / "ev").mkdir()
    (root / "S" / "org").mkdir(parents=True)
    (root / "bin" / "uv").write_text(FAKE_UV)
    (root / "bin" / "uv").chmod(0o755)
    (root / "bin" / "mode").write_text(mode + "\n")
    (root / "ev" / "sandbox-path.txt").write_text(f"{root / 'S'}\n")
    return root


def inject(root: Path, *args: str):
    return run(["zsh", H / "injection.sh", "selfcheck-R", *args],
               env={"P2_EVDIR": str(root / "ev"), "PATH": f"{root / 'bin'}:{os.environ.get('PATH', '')}"})


def cases_c(scratch: Path) -> None:
    w = inj_world(scratch / "C" / "c1", "full")
    r = inject(w, "20261029T104533934917-root-f18f")
    wf = w / "S" / "injection" / "window.txt"
    got = wf.read_text() if wf.exists() else None
    check("(C) injection.sh writes S/injection/window.txt from the log, with no facilitator step: `2026-10-29T10:48:27 2026-10-29T10:50:27` (E7's form)",
          r.returncode == 0 and got == "2026-10-29T10:48:27 2026-10-29T10:50:27\n", f"exit {r.returncode}; window.txt {got!r}; {r.stdout.strip()[-200:]}")
    w = inj_world(scratch / "C" / "c2", "no-end")
    r = inject(w, "20261029T104533934917-root-f18f")
    check("(C) a log with no window end: no window.txt, and a NOTE line", not (w / "S" / "injection" / "window.txt").exists() and "NOTE:" in r.stdout,
          r.stdout.strip()[-300:])
    w = inj_world(scratch / "C" / "c3", "full")
    r = inject(w, "--stop")
    check("(C) `injection.sh --stop` writes no window.txt", not (w / "S" / "injection" / "window.txt").exists(), r.stdout.strip()[-200:])
    w = inj_world(scratch / "C" / "c4", "full")
    (w / "S" / "injection").mkdir(parents=True)
    (w / "S" / "injection" / "window.txt").write_text("2026-10-29T10:48:27 2026-10-29T10:59:59\n")
    r = inject(w, "20261029T104533934917-root-f18f")
    check("(C) an existing different window.txt is kept, with a STOP line", (w / "S" / "injection" / "window.txt").read_text() == "2026-10-29T10:48:27 2026-10-29T10:59:59\n"
          and "STOP:" in r.stdout, r.stdout.strip()[-300:])


# ---------------------------------------------------------------- (D) D1: md5gate_ok gates the amendment files
def gate_world(root: Path, files: dict[str, str | None]) -> Path:
    """A constructed EV (never the real one): protocol.md and standing-rules-streams.md with matching .md5 files, harness/MD5SUMS with one
    matching line, and `files`: name -> text, each amendment written with its .md5 unless the value of `<name>.md5` says otherwise
    (None = no .md5; a string = that .md5 text)."""
    if root.exists():
        shutil.rmtree(root)
    (root / "harness").mkdir(parents=True)

    def md5(p: Path) -> str:
        return run(["md5", "-q", p]).stdout.strip()
    for name in ("protocol.md", "standing-rules-streams.md"):
        (root / name).write_text(f"{name}\n")
        (root / name.replace(".md", ".md5")).write_text(f"{md5(root / name)}  {name}\n")
    (root / "harness" / "x.py").write_text("x\n")
    (root / "harness" / "MD5SUMS").write_text(f"{md5(root / 'harness' / 'x.py')}  x.py\n")
    for name, text in files.items():
        if name.endswith(".md5"):
            continue
        (root / name).write_text(text)
        m = files.get(name[:-3] + ".md5", "auto")
        if m == "auto":
            (root / (name[:-3] + ".md5")).write_text(f"{md5(root / name)}  {name}\n")
        elif m is not None:
            (root / (name[:-3] + ".md5")).write_text(m)
    return root


def gate(root: Path) -> tuple[int, str]:
    """arm.sh's md5gate_ok, called in isolation with EV and H pointed at the constructed copy (arm.sh sourced with a selfcheck label)."""
    r = run(["zsh", "-c", f'source "{H}/arm.sh" selfcheck-R >/dev/null || exit 9; EV="{root}"; H="{root}/harness"; md5gate_ok'])
    return r.returncode, (r.stdout + r.stderr).strip().replace("\n", "; ")


def cases_d(scratch: Path) -> None:
    base = scratch / "D"
    A1, S1 = "protocol-amendment-1.md", "standing-rules-streams-amendment-1.md"
    rc, out = gate(gate_world(base / "d0", {}))
    check("(D) D1: no amendment file: the gate passes (protocol.md, the standing rules and MD5SUMS match)", rc == 0, f"rc {rc}; {out}")
    rc, out = gate(gate_world(base / "d1", {A1: "a1\n", S1: "s1\n"}))
    check("(D) D1: both amendment files with matching .md5 files: the gate passes", rc == 0, f"rc {rc}; {out}")
    rc, out = gate(gate_world(base / "d2", {A1: "a1\n", "protocol-amendment-1.md5": None, S1: "s1\n"}))
    check("(D) D1: protocol-amendment-1.md without its .md5: the gate fails, naming it", rc != 0 and "protocol-amendment-1" in out, f"rc {rc}; {out}")
    rc, out = gate(gate_world(base / "d3", {A1: "a1\n", S1: "s1\n", "standing-rules-streams-amendment-1.md5": "0123456789abcdef0123456789abcdef  x\n"}))
    check("(D) D1: standing-rules-streams-amendment-1.md with a different .md5: the gate fails, naming it",
          rc != 0 and "standing-rules-streams-amendment-1" in out, f"rc {rc}; {out}")
    rc, out = gate(gate_world(base / "d4", {A1: "a1\n", S1: "s1\n", "standing-rules-streams-amendment-1.md5": None}))
    check("(D) D1: standing-rules-streams-amendment-1.md without its .md5: the gate fails", rc != 0 and "standing-rules-streams-amendment-1" in out, f"rc {rc}; {out}")
    rc, out = gate(gate_world(base / "d5", {A1: "a1\n", S1: "s1\n", "protocol-amendment-2.md": "a2\n", "protocol-amendment-2.md5": None}))
    check("(D) D1: a later protocol-amendment-2.md without its .md5 is gated too (the glob): the gate fails", rc != 0 and "protocol-amendment-2" in out, f"rc {rc}; {out}")
    w = gate_world(base / "d6", {A1: "a1\n", S1: "s1\n"})
    (w / A1).write_text("a1 edited after its freeze\n")
    rc, out = gate(w)
    check("(D) D1: protocol-amendment-1.md edited after its .md5 was written: the gate fails", rc != 0 and "protocol-amendment-1" in out, f"rc {rc}; {out}")


def main(argv: list[str]) -> int:
    scratch = Path(argv[argv.index("--scratch") + 1])
    product_src = argv[argv.index("--product-src") + 1]
    if not str(scratch.resolve()).startswith(("/tmp/hirearchy-p2/", "/private/tmp/hirearchy-p2/")):
        print("amend1_cases: --scratch must lie under /tmp/hirearchy-p2/", file=sys.stderr)
        return 2
    scratch.mkdir(parents=True, exist_ok=True)
    for part in (cases_a, lambda s: cases_b(s, product_src), cases_c, cases_d):
        try:
            part(scratch)
        except Exception as e:  # noqa: BLE001 - a case that cannot run is a failed case, named
            check(f"a part raised {type(e).__name__}", False, str(e)[:300])
    for name, ok, detail in results:
        print(f"{'ok' if ok else 'MISMATCH'}  {name}" + ("" if ok else f"\n      got: {detail}"))
    k = sum(ok for _, ok, _ in results)
    print(f"amend1_cases: {k} of {len(results)} ok")
    return 0 if k == len(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
