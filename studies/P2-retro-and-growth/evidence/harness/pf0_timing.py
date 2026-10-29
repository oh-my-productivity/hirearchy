#!/usr/bin/env python3
"""The dry run's verdict on the PF-0 timings (protocol 12.6 and 13.3; the freeze fix, manager ruling (b)). No product.
Usage: pf0_timing.py <builds.json>   -> one line `PASS|FAIL: <note>`; exit 0 on PASS, 1 on FAIL.
builds.json: a list of {"kind": "same"|"earlier"|"other"|"failed", "classified": "PF-0 <a> PF-1 <b> new <c>"} (one per build, in order).
The product's PF-0 label depends on the sub-second timing of the build, so the dry run aligns each build to a whole-second boundary
(dryrun_build.py --align) and then checks every timing it reached; this function decides:
- every 'same second' build must read `PF-0 1 PF-1 0 new 0` and every 'earlier second' build `PF-0 0 PF-1 0 new 0`; any other reading FAILs;
- at least one 'same second' build must exist (a PF-0 reproduced); none FAILs, as does an empty list (fail closed);
- an 'earlier second' timing not reached is recorded `not reached; covered by the constructed cases ...`, and is not a failure."""
import json
import sys

EXPECT = {"same": "PF-0 1 PF-1 0 new 0", "earlier": "PF-0 0 PF-1 0 new 0"}
# the constructed cases (selfcheck_cases.py, by the start of their names) that cover the 'earlier second' timing
COVERED_BY = ["D8: the log's first record in the same second as the older commit",
              "an 'earlier second' build: the product gives the design's label, the classifier finds no difference"]


def decide(builds):
    bad = [b for b in builds if b.get("kind") in EXPECT and b.get("classified") != EXPECT[b["kind"]]]
    if bad:
        return "FAIL", "misclassified: " + "; ".join(f"{b['kind']} second read {b.get('classified')!r}, expected {EXPECT[b['kind']]!r}" for b in bad)
    kinds = [b.get("kind") for b in builds]
    if "same" not in kinds:
        return "FAIL", f"no 'same second' build reached, so no PF-0 was reproduced (builds: {kinds or 'none'})"
    note = f"{kinds.count('same')} 'same second' build(s) read PF-0 1; {kinds.count('earlier')} 'earlier second' build(s) read no difference"
    if "earlier" not in kinds:
        note += "; earlier second: not reached; covered by the constructed cases " + " | ".join(COVERED_BY)
    return "PASS", note


if __name__ == "__main__":
    verdict, note = decide(json.load(open(sys.argv[1])))
    print(f"{verdict}: {note}")
    sys.exit(0 if verdict == "PASS" else 1)
