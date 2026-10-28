# Manager decision: arm F's lock-hook check 3 and the note's sender (2026-10-27)

**What happened** (`F1/harness-failures/lock-check3-from-root.txt`). After F1's turn 3 the lock hook printed `STOP: LOCK FAILED`:
- check 1 (the reply names the lock) passed;
- check 2 (`SERVICE.md` v2 `locked: true`) passed;
- check 3 failed on one clause only.

`harness/after_turn.sh` line 32 requires the owner's quiet note to have `from: root`. The product writes it as:
- `from: runtime`;
- `type: note`, `wake: false`;
- a body that begins "root changed the contract of service `weekly-memo` (v1 -> v2)" and holds
  `locked: false -> true (you may no longer revise the playbook)` (`F1/lock/owner-note.md`).

H-LOCK before the lock is ok (no owner playbook version), and the lock held after turn 3.

**What I checked:**
- **The design says nothing about the sender.** It says only that "the owner gets today's quiet note 'locked: false -> true (you may no longer
  revise the playbook)'" (18.2; `services/_amend.py`). `from: root` is the harness's assumption, written into protocol 1.1 (3) as "the
  owner's quiet note from root". The product's contract-change note is sent by the runtime on root's behalf, and its body names root.
- **The frozen harness disagrees with itself.** `probe.sh`'s check 3 passed in attempt 2 on the same note form (note `...-runtime-d35b.md`, lock
  checks 3 of 3).
- **Nothing downstream reads the hook's STOP line.** `finish_stream.sh`'s H-LOCK re-check reads `lock/hook.txt`'s `lead=`, the lock version and
  every later contract version. That is the rule's substance.
- **The protocol gives a reason for the rule** (8): "A failed hook check is H-LOCK too (the arm was not set up)". Here the arm was set up: the
  contract is v2 `locked: true`, the owner was told with `wake: false`, and the lock held.

**Ruling: (a). F1 is VALID. Continue it from turn 4. There is no replacement, and the frozen harness is NOT changed.** This is a reading of
a validity check, made by ruling, as section 5 provides. It changes no measure, no Lena line and no table row.

**Standing rule for every arm-F stream (F1, F2, F3).** Check 3 reads as passed when ALL of these hold for the note the hook found:
- it is in the lead's inbox;
- it has `type: note` and `wake: false`;
- its body holds the exact text `locked: false -> true (you may no longer revise the playbook)`;
- its sender is `root` or `runtime`.

**What the stream step does on that STOP:**
1. Check the four facts on the file.
2. Write `<stream>/lock/check3-ruling.txt`: the facts, the note's path, its md5, and this file's name.
3. Continue the stream. Do not stop it.

On any other failing clause, or if check 1 or check 2 fails, it stops with a warning, as frozen.

**For the scorer.** `validity.json` reads H-LOCK as ok for a stream whose only hook failure is the `from:` clause and that has a
`check3-ruling.txt`, provided `h-lock-before.txt`, `lock-held.txt` and `h-lock-after.txt` are ok. Cite this file. The scorer reports the
pause in F1 (from the end of turn 3 to turn 4) as a gap in `turn-times.txt`. It is not a validity issue: the team's work goes on between turns
in every stream.

**Turn 1's display record.** `F1/turn-01.txt`'s LENA section is blank because the prompt path was relative. The line sent is in
`turn-01.prompt.txt` and `turn-01.cmd.txt`, and `lena-lines.txt` records H1. Nothing a measure reads is lost.
- Do not edit `turn-01.txt`. Add `F1/harness-failures/turn-01-display.txt` with those facts.
- Use absolute prompt-file paths for every remaining turn of every stream.

**Backlog (study harnesses).** The probe and the hook test the same lock with different check code. A harness must use one function for one
check. Add this to the H-A1 lesson.
