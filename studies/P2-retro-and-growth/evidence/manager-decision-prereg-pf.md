# Manager decision: the pre-registration's product findings PF-0 and PF-1 (2026-10-29, before the freeze)

Asked by step 1a (`preregister`, iteration 2) of workflow `wf_8ee5197e04b8ee7c`, with a `warning`: "Shall I close the step with these two
carried to step 12 as product findings? Yes or no." Answered by the manager (the workflow's parent session), verbatim:

> Yes. Close the step with PF-0 and PF-1 carried to step 12 as product findings; neither is fixed in the harness. Record:
> /Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence/manager-decision-prereg-pf.md. Before you close, write into
> protocol.md:
> (1) For each finding, every pass rule or check that reads the affected output (P2-X3, P2-B, P2-E and P2-S at least), whether it can
> change that verdict in this script, and why.
> (2) The pre-registered reading. X3's edit count is the harness's git re-derivation. A PF-0-signature label on a change the
> re-derivation does not count as an unprompted edit is reported as PF-0 under P2-E, not as an X3 or P2-B failure. On a change the
> re-derivation does count, X3 fails as written.
> (3) A P2-E mismatch matching PF-1's exact signature (a create-and-retire pair in one window, missing from D8) is reported as PF-1.
> Every other mismatch is a new finding. Write each signature as a mechanical test over named files, with self-check cases for PF-0, for
> PF-1, and for a near miss that must be classified as neither. Re-run the self-check.
> (4) Both are counted per stream in the report.
> Then signal success.

## The findings (as recorded in `harness-selfcheck/SELFCHECK.md`)
- **PF-0 (LOW):** the product reads the event log's horizon from MCP-path records only, so a nested charter change whose window the log
  covers with CLI records only is labelled `by {parent}, or outside the tools (the event log does not reach back)`, where design 4.5 gives
  `outside the tools (a hand edit or the terminal)`. Reproduced on the arm-R product in the dry run (`harness-selfcheck/dryrun-R/pf0-*`).
- **PF-1 (LOW):** the product's D8 omits the creation of an agent or a service that was retired in the same window, which design 4.3 and
  4.5 list. Reproduced in the dry run (`harness-selfcheck/dryrun-R/labels-*`).

## Where it is carried out
- `protocol.md` 12.6 (items (1)-(4): the readers table, the reading for X3 and P2-B, the signatures as mechanical tests over named files,
  the counts per stream), 12.1 P2-X3, 12.2 P2-E, 12.4, 13.2 reading 1, 16 item 33.
- `harness/extract_p2.py` (`pf0_signature`, `classify_d8`, `e_check`, `x3`), `harness/aggregate.py` (the counts per stream),
  `harness/rederive_p2.py` (each charter pair's commit times; each product line's text).
- Self-check: constructed cases for PF-0, PF-1 and their near misses, the X3 reading both ways and P2-E's counts
  (`selfcheck_cases.py`), the aggregate's count line, and both findings classified on the product's own output in the arm-R dry run.
- Neither finding is fixed or imitated in the harness: the re-derivation keeps the design's labels.

## Addendum (2026-10-29, iteration 3): PF-0's mechanism corrected; the signature is KEPT

- **The observed mechanism.** The product shows `by lead, or outside the tools (the event log does not reach back)` exactly when the event
  log's earliest record lies in the same whole second as the older commit, but later in microseconds. One second earlier, it shows the
  design's `outside the tools`. So the cause is a comparison of microseconds against whole seconds, not iteration 1's "MCP-path records
  only". It is the same whole-seconds issue that design 22.3 records.
- **Decision: yes, keep the pre-registered signature.**
  - It matches every PF-0 the throwaway builds produce, and the dry run now checks both timings.
  - PF-0 cannot arise in a stream under this script.
  - A same-second PF-0 that came after an MCP record would be classified `new` and reported. That errs toward reporting, not hiding, and
    no pass rule reads it.
  - Reading (2), X3's count from the git re-derivation, is unchanged.
- **2b backlog:** the fix is to compare the event-log horizon at whole seconds, the commit's precision. Add a test at the same-second
  boundary.
