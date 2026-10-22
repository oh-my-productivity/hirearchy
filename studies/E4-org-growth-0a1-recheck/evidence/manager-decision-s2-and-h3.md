# Manager rulings: s2 (H8 candidate) and s1r (H3 question)

Date: 2026-10-22. Author: project manager. The owner has delegated execution decisions. These rulings are recorded before s2r turn 1.
`protocol.md` (584b6cc7…) and `protocol-amendment-1.md` (1ec9e658…) are not edited.

## Ruling 1: s2 is INVALID (H8). Replacement s2r approved.

**Why H8 applies, not the "not invalid" list.**
- **The failure matches H8 exactly.** The failed org run `lead/reviewer@20261022T202454859379` ended with a model-service error (`ModelThrottleError`,
  `THROTTLING`, "Claude Sonnet 4.6 is experiencing high traffic"). That is H8's named example, and a task stalled because of it.
- **Its cause is not product behaviour.**
  - The section 11 "Not invalid" list is headed "product or assistant behaviour". Its entry "the injected rework blocking or stalling" covers
    stalls that the product or the assistant cause, for example a refusal or the team's own blocked report.
  - This stall was caused by the model service, so the specific, named rule (H8) governs.
- **It changed the stream's course.**
  - The infrastructure failure left an unread budget request from the lead in root's inbox and a paused reviewer.
  - Turn 6 onward would start from a state that infrastructure created, not the protocol.

**Consequences (section 11).**
- **s2 stays in the evidence as INVALID.**
- **Observations before the failure stand.**
  - Any rule FAIL observed in s2's turns 1 to 5 or in its injection window counts for the gate.
  - This includes a revise_playbook attempt admitted on relayed, single-case or unconfirmed evidence, if one happened.
  - The scorer checks s2 for these from raw evidence.
- **s2r replaces it.** It gets a fresh sandbox `/tmp/hirearchy-e4-s2r-<epoch>`, a fresh org, session and profile, and the same protocol and amendment.
  s3 follows as planned.

**Harness hygiene for s2r and s3.** It adds no protocol change: the product, the pass rules and what is injected are untouched.
- **Model check before turn 1 and before the injection.** Run one cheap availability check of each org-agent model the protocol fixes
  (claude-sonnet-4.6 and claude-haiku-4.5).
  - Use the prep profile: `kiro-cli chat --v3 --no-interactive --agent <prep> --model <m> "Reply with OK."`.
  - Require a successful reply.
  - On a throttle or service error, wait 10 minutes and retry, up to 6 times. If it still fails, stop with severity "warning".
  - Record every check in `<stream>/model-checks.txt`.
- **If an org run fails on a model-service error anyway,** handle it exactly as s2 was handled: stop, record, escalate, and start no replacement
  without the manager.

**Product findings for STUDY.md.** These are not stream verdicts; they are things the study observed about hirearchy.
- **F-E4-infra-1.** A run that fails on a model-service error before any tool effect is charged as a used run. With a delegation budget of 1,
  the reviewer is then paused for budget, and the task stalls behind a budget request to root. Candidate fix, to be decided later: do not
  charge, or retry once, a run whose kiro error is a model-service throttle (`retryErrorType: THROTTLING`).
- **F-E4-harness-1.** The frozen injection script polled `progress(wait_seconds=300)` 36,513 times in 7 minutes once the reply was "Not waiting:
  nothing can progress without you". The calls are read-only and changed nothing in the org, so the script stays frozen for comparability.
  Two things are recorded:
  - it is a harness defect;
  - a product observation: `progress(wait_seconds)` returns at once in that state, which is correct, so a client must not loop on it.

## Ruling 2: s1r is VALID; it is not H3.

- **The specific 4.5 test is not met.** The operative per-stream invalidity rule in 4.5 is "a memory or steering block present when the probe
  removed it, or a settings file with a different md5". Neither occurred: the settings md5 matches, and no block is present where the probe
  removed one.
- **The difference reduces confounds.** The difference found is a memory index ABSENT where the probe found it present. H3 exists to keep
  extra or uncontrolled ambient context from confounding streams. Absence moves toward 4.5's preferred state, a removed memory index. Its cause
  lies outside the study: `memories.db` and `cli.json` are unchanged, and the facilitator made no change. It is not a facilitator action.
- **The same reading applies to every stream.**
  - A stream whose `session_start` shows either the probe's composition (memories present) or no memory index is valid on 4.5 and H3, as
    long as the settings md5 matches and no steering block appears.
  - Memory presence is recorded per stream in `ambient-context.txt`.
  - The scorer reports it as a covariate in STUDY.md and notes any rule outcome that differs with it.
