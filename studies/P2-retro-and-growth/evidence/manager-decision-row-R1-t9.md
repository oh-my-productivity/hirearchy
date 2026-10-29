# Manager decision: R1 turn 9, the errored chat call, and memories.db changing during the stream (2026-10-29)

## 1. Turn 9's chat call ended with a transient engine error: CONTINUE with K34 (by ruling)
**Facts.**
- `turn.sh` exited 1 after 299 s. The last stderr line was `ClientNetworkError`, `retryErrorType: TRANSIENT`.
- The assistant produced no reply text. Before the error it ran these tool calls:
  - `feedback`, accepting memo 2;
  - `delegate`, which created the one-off root-cabf, "One-page ops action list for the 2026-10-12 meeting";
  - `start`;
  - `progress`.
- The lead's run finished. The list was not copied to `deliverables/`, and Lena received nothing.

**Ruling: (b), continue.** The next Lena line is **K34, L-WAIT `I'll wait.`**, recorded `K34 (by ruling)` with this file.
- K34's condition holds literally: "the assistant returns control with no question while the memo or list she asked for is not
  delivered". An errored turn returns control with no question, and the 2026-10-12 list is not delivered.
- No line is added, so this is ruling (a)'s form: an existing row named by the manager.
- Repeating turn 9's line is refused. It would send a second ACT-REQ@2026-10-12 and open a second one-off window.
- It counts as one L-WAIT for the frozen "two L-WAIT in a row" end rule. That rule is unchanged.

**Ruling (a), ending the stream under H8 now, is refused.** H8 needs a failure that changed the course. The work the turn had started is
intact in the org: the accept is recorded, and the one-off exists in the ACT-REQ@2026-10-12 window and has finished. Only the copy and the
reply were lost. Ending R1 would discard 36 credits and use arm R's one replacement for a failure that may have changed nothing.

**The H8 reading, pre-registered now, before the outcome is known.** The turn-9 error changed the course, and R1 is invalid from turn 9
under H8, if after the K34 line ANY of these happens:
1. a second root task without a `service:` header is created in the ACT-REQ@2026-10-12 window, so the window holds two one-offs;
2. a second human-tier verdict is recorded for memo 2's delivery;
3. a delivery of the 2026-10-12 list, by copy, is never made before Lena's next line that judges a list or requests the next memo.

Otherwise R1 stays valid. The error is recorded in `validity.json` as `engine_error_turns: [9]`, and step 12 reports it.

**What the stream step does:**
- Send turn 10 with exactly `I'll wait.`, recorded `turn 10 | rules L-WAIT | table rows K34 (by ruling) | facts: turn 9 ended with a
  transient engine error (ClientNetworkError), no reply; root-cabf created and finished; list not copied`, citing this file.
- **If turn 10 also ends with an engine error, or with no reply,** stop with a warning and do not retry. That is a degraded service, and
  the brief forbids continuing on one.
- **If (1) or (2) shows in turn 10's reply or its org state,** stop with a warning before turn 11, so that no more credits are spent
  before I rule.
- Otherwise continue under the frozen protocol and amendment 1.

## 2. memories.db changed during turn 8: the writer is the owner's own, unrelated Kiro session
**Facts, checked by the manager.**
- The file's mtime is 12:31:23Z, and its size went from 155648 to 159744 bytes.
- The only session written at that time is `sess_e1ee9b77-aa4d-46f1-86b8-082887906d28`, in a different sessions folder
  (`c180816ccebda8ac`). Its title is "Create Minimal Projects With Jenkinsfiles And Containers", its memory setting is `read_write` with
  reflection, and it is not a workflow step.
  - Its turn ended at 12:30:14Z.
  - It wrote a `memoryExtractionWatermark` at 12:31:26Z.
  - So it is the owner's own work outside the study.
- The assistant session reads its `<memories>` block once at start. R1's block (6903 characters, md5 `2a977c30...`) was taken before the
  change and checked clean after turn 1. R1 is not affected.

**Correction of my earlier record.** The 11:46Z change before R1 (`manager-decision-memories-before-R1.md`) was also written by an owner
session, not by my amendment passes. `sess_ce38cb49-9ca4-48b3-a97e-af15d9e4b9c5`, "Mobile roguelite game build", wrote a
`memoryExtractionWatermark` at 11:46:06Z. My rule against direct subagent passes during streams stays as a precaution.

**Ruling: R1 stays valid** (P1's rule: "The stream that changed it stays valid").

**A standing ruling for the rest of the study.** The owner's own Kiro sessions can change `memories.db` at any time, and the study must
not interfere with them. So:
- **A change between streams or during one** is recorded, not a stop, when ALL of these hold:
  - (a) exactly one session outside the study wrote a `memoryExtractionWatermark` within 10 s of the file's new mtime;
  - (b) that session is not a workflow step of this run and not one of the study's assistant or org sessions (its `session.json` has no
    `workflow` meta for `wf_8ee5197e04b8ee7c` and is not under the sandbox);
  - (c) the next stream's turn-1 `<memories>` contamination check passes.
- When (a) and (b) hold, the stream step may write `manager-decision-memories-before-<label>.md` itself, citing this section, with the
  session id, its title, the watermark time and the md5s. That satisfies the frozen gate.
- **Any other change is a stop with a warning,** as before: the writer unidentified, a study session as the writer, or a failed
  contamination check.
- The `<memories>` block is recorded per stream (P1's rule). The assistant-layer contrast is read only for pairs whose blocks match.
