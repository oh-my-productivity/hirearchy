# Standing rules for every remaining stream step: I2, F2, F3, I3 (the manager, 2026-10-27)

These rules come from the manager's stage-1 rulings, which are listed at the end. Read this file before the stream's first turn and follow it
for every turn, together with the frozen protocol. Where this file and a frozen file differ, this file wins, because each rule here is a
ruling under protocol 5. Each rule changes how the step works, not what any measure is.

1. **Turn, then snapshot.** Run `run_turn.sh` and `after_turn.sh` as SEPARATE tool calls, one after the other, and never in one tool block.
   - After each turn, check that `after_turn.sh`'s first snapshot (`quality/calls.txt`) starts after the turn's end plus the 20-s boundary
     (`turn-times.txt`).
   - Record `after_turn sequential: checked` in that turn's facts.
2. **Absolute prompt-file paths** for every turn.
3. **The owner form.** Before sending a Lena line, write its owner names in the form in force (4.1: N, then I from L-PLANT, N from L-MIND, N+J
   from L-GAP).
   - In form I, no key owner's full name may appear as an owner. In form N, no bare initial may.
   - Record `owner form <X>: checked`.
4. **The `lena-lines.txt` line form,** exactly: `turn <n> | rules <ids> | table rows ... | facts: ...`.
   - After writing each line, check it with the frozen parser (`python3 -B`, importing `harness/guarantees.py`'s line parser, read-only; no
     file written). It must return the turn and its rules.
   - Fix an unread line before the next turn.
5. **Arm F, lock check 3.** If the hook stops only because the owner's note is `from: runtime`, do not stop.
   - Check the four facts: the note is in the lead's inbox; it is `type: note` with `wake: false`; it holds the exact text
     `locked: false -> true (you may no longer revise the playbook)`; its sender is `root` or `runtime`.
   - Write `<stream>/lock/check3-ruling.txt` with the facts, the note's path, its md5, and `manager-decision-lock-check3.md`. Then continue.
   - Any other failing clause, or a failed check 1 or check 2, stops the step with a warning.
6. **The questions mapped in I1's turn 1** map the same way in every stream. Record each as `K<n> (by ruling, manager-decision-row-I1-t1.md)`.
   - Who may be named -> K20 `Use the words from the notes.`
   - Whether the memo should be in English -> K3, with no added text.
   - An "open items from earlier weeks" section, default no -> K3, with no added text (not K25).
   - If the English or open-items question is asked again in a stream, send K3's `The rest of your defaults are fine, the deliverables
     folder too.`. A third time, stop with a warning.
   - **Any other question the table does not hold:** stop before the next Lena line, with a warning that quotes the question verbatim and names
     the two or three closest rows. Never improvise.
7. **Memories.**
   - Before and after the stream: the `memories.db` md5, as frozen. A change stops the study before the next stream.
   - At the stream's end, also record whether the assistant session's `session_start` holds a `<memories>` block, and its length, in
     `<stream>/memories-block.txt`.
8. **Credits.** In stage 2, a stream over 185 credits (`credits.txt`) sends a warning before the next stream starts, and waits.
9. **Report every slip.** Report a facilitator slip as soon as you find it, with a file under `<stream>/harness-failures/`, and wait for a
   ruling only when it could have changed the course. Never edit, retry or delete evidence.

Rulings this collects: `manager-decision-probe-define.md`, `manager-decision-lock-check3.md`, `manager-decision-f1-owner-form.md`,
`manager-decision-f1-after-turn-timing.md`, `manager-decision-row-I1-t1.md`, `manager-decision-stage-1-gate.md`.

10. **The memo input's name** (added 2026-10-27, `manager-decision-memo-input-name.md`). The team may name its memo input anything
    (`meeting_file` in I2). Read every live trigger that the protocol takes from `requests-by-turn.txt` from root's sent mail instead: a
    request whose `## Request` block gives the memo's notes file under any input name. Record each reading as
    `memo <n> request read from sent mail: <message id> (<input name>: <file>)`. Never edit `requests-by-turn.txt`.

11. **A self-referential criterion** (added 2026-10-27; REVISED, `manager-decision-row-I2-t7-revised.md`). A question asking whether to count,
    waive or treat as met a criterion about the reviewer's own report (for example "C7 ... the reviewer won't certify that one ... Should I
    count C7 as met?") maps to **K29's `Yes.`**, recorded `K29 (by ruling, manager-decision-row-I2-t7-revised.md)`, every time it is asked.
    It is **not** K33's `Ok.`: the assistant does not take that as a yes. A contract item on that criterion is K30, read as follows:
    - reword it to exclude itself and keep the review: `Yes, add it.`;
    - remove the review: `No.`;
    - anything else: stop and quote it.

12. **"One bullet or two?" for a key decision kept as one bullet** (added 2026-10-27, `manager-decision-row-I2-t12.md`). Answer with K14c's
    `Yes, that's a decision.`, recorded by ruling. If the draft has split a key decision and asks whether that is fine, stop and quote the
    question.

13. **An extra-part question before memo 1's H6 answer** (added 2026-10-27, `manager-decision-row-F2-t4.md`). This means a header, footer,
    attendee, "Present", "Next meeting" or source line, or any other extra part.
    - If contract v1 has a criterion that limits the memo's parts ("exactly", "nothing else", "only"), stop and quote the question.
    - Otherwise, answer K32 `Keep it as it is.` by ruling.
    - From H6's answer on, an extra-part question maps to K25 as frozen.
14. **The memo input's value may be a path** (added 2026-10-27; addendum to `manager-decision-memo-input-name.md`). For example
    `notes_file: /tmp/.../notes/2026-10-05.md`. Read the memo from the `YYYY-MM-DD` date in the value's file name, whatever its path or input
    name. Record it as in item 10.

15. **A title above the Summary line** (added 2026-10-28, `manager-decision-row-F2-t10.md`). After H6's answer, a question about whether a title
    may come before the Summary line ("title or no title?", because a criterion says the first line must be "Summary:") maps to K25's line,
    verbatim.
    - A yes/no item that allows a one-line title before the Summary is K30, answered `Yes, add it.`.
    - An item that drops the title or keeps the stricter criterion is K30, answered `No.`.
    - The same "which do you want?" question asked again after that turn stops the step: quote it.

16. **Initials-only owners asked before memo 5** (added 2026-10-28, `manager-decision-row-I3-t1.md`). This covers a question at elicitation,
    or before memo 5, about owners given only by initials, or about the notes' line that says to leave such items out. Answer K17b
    `No, JD's row counts.`, then K23 `Use the words from the notes.`, by ruling. Never accept a default cell form for them through H2's
    "rest of your defaults".
