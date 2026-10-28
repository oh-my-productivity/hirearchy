#!/usr/bin/env python3
"""P1 stream credits (protocol 11; design 18.7's stop rule).

A stream's credits = `total assistant credits` + the sum of `per-model credits (all runs)` (every org run of the stream, the injection
window included), both read from the stream's cost.txt (extract_mechanical.py writes them), added as decimals and rounded half-up to 2
decimals. "Over 185 credits" means > 185.00. Runs without a matched session (cost.txt's `runs without a matched session: N`, whose
credits the per-model sum lacks) are added conservatively, N times the stream's mean credits per matched run, and flagged on the line, so
the 185-credit comparison is never low (protocol 11, the manager's decision on L1); with N > 0 and no matched run there is no figure.
finish_stream.sh writes the figure as one line into the stream's credits.txt, `stream total credits: <x> (assistant <a> + org runs <o>)`
or `stream total credits: <x> (assistant <a> + org runs <o> + <N> runs without a matched session x <mean> = <e> estimated; FLAGGED)`
(cost.txt stays G0's, byte for byte), and next_stream.sh and the stage gate read exactly that line.

    python3 -B cost_total.py <cost.txt>                prints the line; exit 2 when a figure is missing
    python3 -B cost_total.py --over 185 <credits.txt>  reads the `stream total credits:` line; exit 0 if over, 1 if not, 2 if missing
    python3 -B cost_total.py --selfcheck --out DIR     G0's six cost.txt files against G0's published totals, and the --over edges
"""
from __future__ import annotations

import ast
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

G0 = Path("/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence")
G0_PUBLISHED = {"m0-s1": "71.99", "m0-s2": "63.69", "m0-s3": "71.41", "m1-s1": "62.98", "m1-s2": "71.45", "m1-s3": "63.49"}  # G0 STUDY.md
LINE = re.compile(r"^stream total credits: (\d+\.\d{2}) ", re.M)


def figures(text: str) -> tuple | None:
    """(total, assistant, org runs, N unmatched, mean per matched run, estimate), each 2 decimals but N, or None (no figure)."""
    a = re.search(r"^total assistant credits: ([0-9.]+)\s*$", text, re.M)
    m = re.search(r"^\s*per-model credits \(all runs\): (\{.*\})\s*$", text, re.M)
    if not a or not m:
        return None
    org = sum((Decimal(str(v)) for v in ast.literal_eval(m.group(1)).values()), Decimal(0))
    ass = Decimal(a.group(1))
    u = re.search(r"runs without a matched session: (\d+)", text)
    n_un = int(u.group(1)) if u else 0
    runs = sum(int(x) for x in re.findall(r"^\s*total runs (\d+) ", text, re.M))
    est = mean = Decimal(0)
    if n_un:
        matched = runs - n_un
        if matched <= 0:
            return None  # no matched run to estimate from: no figure (next_stream.sh refuses the next stream)
        mean = org / matched
        est = mean * n_un
    q = Decimal("0.01")
    r = lambda x: x.quantize(q, ROUND_HALF_UP)  # noqa: E731
    return r(ass + org + est), r(ass), r(org), n_un, r(mean), r(est)


def line_of(text: str) -> str | None:
    f = figures(text)
    if f is None:
        return None
    if f[3]:
        return (f"stream total credits: {f[0]} (assistant {f[1]} + org runs {f[2]} + {f[3]} runs without a matched session x {f[4]} = "
                f"{f[5]} estimated; FLAGGED: protocol 11)")
    return f"stream total credits: {f[0]} (assistant {f[1]} + org runs {f[2]})"


def over(text: str, limit: str) -> int:
    m = LINE.search(text)
    if not m:
        return 2
    return 0 if Decimal(m.group(1)) > Decimal(limit) else 1


def selfcheck(out: Path) -> int:
    lines, ok, n = [], 0, 0
    for lab, want in G0_PUBLISHED.items():
        n += 1
        ln = line_of((G0 / lab / "cost.txt").read_text())
        got = LINE.search(ln + "\n").group(1) if ln else None
        ok += got == want
        lines.append(f"{'OK  ' if got == want else 'FAIL'} G0 {lab}: {ln} (G0 published {want})")
    synth = ("total assistant credits: 50.0000\n  outside the injection window (counted toward the 45 cap):\n    total runs 38 secs 900 credits "
             "95.0000\n  injection window:\n    total runs 4 secs 100 credits 5.0000\norg-run credits are read from each run's kiro session "
             "(usage_summary); runs without a matched session: {u}\n  per-model credits (all runs): {{'claude-sonnet-5.5': 100.0}}\n")
    for u, want in ((2, "stream total credits: 155.00 (assistant 50.00 + org runs 100.00 + 2 runs without a matched session x 2.50 = 5.00 "
                        "estimated; FLAGGED: protocol 11)"), (42, None), (0, "stream total credits: 150.00 (assistant 50.00 + org runs 100.00)")):
        n += 1
        got = line_of(synth.format(u=u))
        ok += got == want
        lines.append(f"{'OK  ' if got == want else 'FAIL'} {u} runs without a matched session of 42: {got} (want {want})")
    for txt, lim, want in (("stream total credits: 185.00 (assistant 70.00 + org runs 115.00)\n", "185", 1),
                           ("stream total credits: 185.01 (assistant 70.00 + org runs 115.01)\n", "185", 0),
                           ("stream total credits: 185.01 (assistant 70.00 + org runs 110.00 + 2 runs without a matched session x 2.50 = "
                            "5.01 estimated; FLAGGED: protocol 11)\n", "185", 0),
                           ("total runs 5 secs 170 credits 5.4151\n", "185", 2)):
        n += 1
        got = over(txt, lim)
        ok += got == want
        lines.append(f"{'OK  ' if got == want else 'FAIL'} --over {lim} on {txt.strip()!r}: exit {got} (want {want})")
    lines.append(f"cost_total: {ok} of {n} checks OK")
    text = "\n".join(lines)
    print(text)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cost_total.out").write_text(text + "\n")
    return 0 if ok == n else 1


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck(Path(argv[argv.index("--out") + 1]))
    if "--over" in argv:
        i = argv.index("--over")
        p = Path(argv[i + 2])
        return over(p.read_text() if p.exists() else "", argv[i + 1])
    ln = line_of(Path(argv[0]).read_text())
    if ln is None:
        print("stream total credits: MISSING (no `total assistant credits` or `per-model credits (all runs)` line, or runs without a matched "
              "session and no matched run to estimate them from)")
        return 2
    print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
