# Manager decision: the P1 stage-1 gate (2026-10-27)

**Gate** (`stage-1-gate.md`). The 18.7 stop rule PASSES:
- F1 and I1 are both valid. No H rule is broken, and H-LOCK is ok under `manager-decision-lock-check3.md`.
- The probe passed. Empty-argument calls are 0 and 0. `memories.db` is unchanged during and between the streams.
- Credits: F1 100.23 and I1 121.49, each under 185. Stage 1 so far: 230.52 credits and 137 org runs, inside the stage-1 approval of about
  260-390 credits.

**Decision: GO to stage 2** (I2, F2, F3, I3, in that order), under the owner's approval of 2026-10-27. The stop rule stays: a stream over 185
credits pauses the study before the next one.

The four items:

## 1. `since` precision (gate 4.2): a scoring ruling for every stream; the frozen harness is not changed
- **The facts.** Design 14.4 names `since` but gives no precision. The quality JSON's one time format is whole seconds
  (`%Y-%m-%dT%H:%M:%SZ`). The harness line `rederive_watch.py:1172-1174`, `d.replace(microsecond=d.microsecond)`, does nothing. It shows an
  intent to normalise that was coded wrong. This is a harness defect, not a product defect.
- **The ruling.** The scorer reads a `since` value equal when the product's value and the re-derivation's value are equal after both are
  truncated to whole seconds, in UTC.
  - The re-derivation keeps microseconds for its own window computation (`E`, `D`, `K` and the windows). Only the displayed key's comparison is
    truncated.
  - It applies identically in every stream, in both arms.
  - The scorer applies it as a documented step over the frozen comparison output. It does not edit the frozen harness.
  - The scorer lists every mismatch it cleared, with both values, and puts the step's script and md5 under `measures/`.
  - A mismatch that remains at whole-second precision stands under 12.1 (f1).
- **Reported as finding `F-P1-n` (harness):** the no-op normalisation, and the lesson that a harness must compare every displayed key at the
  product's rendered precision.

## 2. G2(a)'s line form (gate 4.1)
- **Stage 2.**
  - The stream steps write every line of `lena-lines.txt` exactly as `turn <n> | rules <ids> | table rows ... | facts: ...`.
  - After writing each line, the step checks it with the frozen parser, read-only (`python3 -B`, importing `harness/guarantees.py`'s line
    parser, no file written). The parser must return that turn and its rules.
  - A line it does not read is fixed before the next turn is sent.
- **F1 and I1.**
  - The scorer reads a normalised copy: `rules ` is inserted where it is missing, and nothing else changes. The copy goes to
    `measures/<label>/lena-lines.normalised.txt`, with a note and the diff. The originals are not edited.
  - The gate's in-memory reading (PASS, 4 of 4 in each stream) is the expected result. The scorer re-derives it from the copies.
- **Fail-closed, every stream.** If the parser reads fewer Lena turns than `lena-lines.txt` has `turn <n> |` lines, G2(a) reads NOT
  DETERMINED, never PASS. The scorer checks every other consumer of `lena-lines.txt` in the harness for the same parse.
- **Reported as finding `F-P1-n` (harness):** `g2` passes on an empty list.

## 3. The memories block (gate 4.3): reported per stream, and it limits only the assistant-layer contrast
- **The facts.** The presence of the owner's `<memories>` block varies from session to session in the engine: F1 had none, I1 had one, and the
  four probe sessions had none. It is not caused by the arm, `memories.db` is unchanged, and protocol 8 says it is not H3.
- **The ruling.**
  - No stream is invalid for it.
  - Do not try to control it. That would need a different kiro home treatment, which F-G0-7 forbids.
  - The scorer records, per stream: the block's presence, its length, and whether its text equals the other streams' blocks.
- **The assistant-layer contrast** (credits, call counts, behaviour; descriptive only) compares a pair only when both of its streams have the
  same presence. A pair that differs is reported unpaired, with the confound named.
- The mechanical guarantees and the outcome measures are unaffected.
- **Reported as finding `F-P1-n` (environment).** Design 18.2's "the same owner's memories index" holds for the file, not for its delivery into
  the session.

## 4. Effort warnings (gate 4.4): reported, not H4; a backlog item for the product
- **The facts.** About 1 org run in 9 logs `failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels`, and one assistant
  turn logs `the engine did not load its model list in time`. Every `# cmd:` line carries `--effort high`. G0, E6 and E7 show the same pattern.
- **The ruling.** Not H4 under the frozen check. The scorer reports the count per stream (org runs and assistant turns) with the log lines.
- **Backlog (product, after P1).** The owner requires every seat at high. Investigate whether the launcher should wait for the engine's model
  list, retry, or flag a run whose effort could not be set. It looks like the same readiness race as `READINESS_TIMEOUT`. Tell the owner.

## Standing rules for the stage-2 streams
`manager-standing-rules-streams.md` collects every rule from the stage-1 rulings in one place.
