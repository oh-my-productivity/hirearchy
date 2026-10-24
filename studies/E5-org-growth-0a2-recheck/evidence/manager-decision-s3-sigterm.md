# Manager decision: s3's killed writer run, and restarting the scoring (2026-10-24)

## Context
- Workflow `wf_a0d2c6f21a51f12c` completed these steps: preregister, preflight, run-s1, run-s2, run-s3 and teardown.
- It then failed in its score step with "Usage limit reached", before `STUDY.md` existed.
- The model service's usage limit has nothing to do with the study, and no stream ran after the limit was hit. The score, gate and commit steps are restarted in a new workflow, with no change to the protocol or the evidence.

## The point the s3 facilitator raised for the manager
- **What happened.** In turn 4, the `lead/writer` run `20261024T041458746130` was killed by SIGTERM (exit 143), about 23 s after it started.
  - It was killed when the turn-4 assistant call (kiro-cli) returned at 04:15:21Z. The scheduler that call started (pid 24167) was still running.
  - The writer's task `bed1` stayed open with writer budget 0, and the lead reported `blocked` (d8cc).
  - Lena was asked for 2 more runs. Memo 1's case ended at 13 of 12 runs, before the injection.
- **The facilitator's judgement.** Not H8. No H8 reason shows in any run log, and the kill followed from the assistant ending a turn with the scheduler running.

## Ruling (provisional; the scoring step applies the frozen protocol)
1. **s3 is scored as VALID**, as the facilitator judged.
   - The scoring step checks this against the exact text of protocol section 11, including H8 and "Not invalid".
   - If that text requires otherwise, the scorer may rule s3 INVALID, giving the reason. It must say so explicitly.
2. **The gate's robustness table shows the verdict both with s3 and without it**, as E4's gate did for its rulings.
3. **The kill is recorded as a finding, F-E5-n, with its mechanism** established from the raw evidence: run logs, `.runtime/events`, pids and process groups where recorded.
   - The open question: does an org agent's run, started by the scheduler under root's MCP server, die when the assistant's kiro-cli call exits?
   - It is classified as either:
     - a **product** defect: agent runs not detached from the starter's process group or session, which a real user hits by closing their kiro chat;
     - or a **harness** artefact of per-turn non-interactive calls.
   - Check whether the same pattern occurred in s1, s2 or E4's streams.
