# E6 evidence index (the preflight and stream steps add their files; facts only, no scoring)

Times are local (WEST = UTC + 1 h) unless marked UTC; org clocks and file names are UTC. Product: `main` = `18c4ffb`. Protocol `protocol.md`
md5 in `protocol.md5`.

## Study level, written by the pre-registration step (step 1 of 9, workflow `wf_25265920a47bd720`)
| File | What it is |
|---|---|
| `protocol.md`, `protocol.md5`, `freeze.txt` | The pre-registered protocol (E5's, amended only by the E6 brief's step 1 items 1-8), its md5, and the freeze record (UTC time, HEAD, the empty freeze diff, the skill, harness and injection-script md5s, the state at freeze). |
| `harness/` (`MD5SUMS`, `CHANGES.md` and 15 files) | E5's harness with paths, names and the product sha changed; `CHANGES.md` has every change against E5 with its diff. |
| `notes/`, `answer-key.md` | E2's three notes files and the private answer key, byte-identical to E5's (protocol 4.6). |

## Stream s1 (written by the s1 stream step, step 3 of 9; sandbox `/tmp/hirearchy-e6-s1-1792855848`; apparently VALID; 12 of 12 user turns; 39 counted org runs of 45 (+5 injection-window runs); 0 throttles; memo 3 delivered in turn 12, not judged because of the cap; no scheduler running at any turn end; not scored)
| File | What it is |
|---|---|
| `s1/run-log.md` | Facts: gates and setup, turn table, org runs, injection, contract/playbook/flag facts, ambient context, skill, model checks, throttling, validity (section 11), harness notes, cleanup and safety. |
| `s1/setup.txt` (incl. "AFTER the last turn"), `s1/epoch.txt`, `s1/sandbox-path.txt`, `s1/stream-start-utc.txt`, `s1/skill-check.txt`, `s1/ambient-context.txt`, `s1/model-checks.txt`, `s1/safety-before.txt`, `s1/safety-after.txt`, `s1/safety-diff.txt` | Per-stream setup, the freeze checks before and after, skill, ambient context, model checks and safety snapshots. |
| `s1/profiles/` | The assistant profile copy, `creations.txt`, `deletions.txt`, and the org's scheduler profile copy (`org-kiro-home--*.json`). |
| `s1/lena-lines.txt`, `s1/prompts/` (`t01..t12.txt`, `after_turn.sh`), `s1/turn-01..12.txt` (+ `.prompt`, `.cmd`, `.raw`, `.stderr`), `s1/turn-times.txt`, `s1/session-turn-times-utc.txt` | The conversation (12 user turns) and the facilitator's helper. |
| `s1/harness-failures/turn-01-relative-prompt-path.txt` | The facilitator's turn-1 slip (relative prompt path; the prompt was sent verbatim; only the echo in `turn-01.txt` is empty). |
| `s1/assistant-tool-calls.txt`, `s1/assistant-session-messages.jsonl`, `s1/assistant-session.json` | Assistant tool-call transcript (73 calls) and the raw session store. |
| `s1/PLAN-FOR-YOU-product-proposal1.txt`, `s1/PLAN-FOR-YOU-product-proposal2.txt`, `s1/blueprint-proposal1.yaml`, `s1/blueprint-proposal2.yaml`, `s1/blueprint.yaml`, `s1/apply_org-result.txt` | The two `propose_org` results (12 and 16 runs per request), the proposed and applied blueprints, the `apply_org` result. |
| `s1/injection/` | `injection-log.txt`, `request-args.json`, `text-identity.txt`, `window-runs.txt`, `window.txt`, `memo1-identification.txt`, marker. |
| `s1/msgs/`, `s1/run-logs/`, `s1/events/`, `s1/org-files/`, `s1/service/`, `s1/playbook/`, `s1/scheduler.log`, `s1/org-git-log.txt`, `s1/observe-traces.txt`, `s1/observe-check.txt`, `s1/final-services-progress-status-health.txt`, `s1/copy_org_evidence-output.txt` | The org copied read-only after the stream. |
| `s1/org-kiro-sessions/`, `s1/run-session-map.txt` | The org agents' kiro sessions and the run-to-session map. |
| `s1/memos/` (final memos), `s1/memos/versions/` | Deliverables at the end and every committed version of each work file. |
| `s1/run-counts-by-turn.txt` (with the per-turn scheduler records and throttle scans), `s1/run-counts.txt`, `s1/cost.txt` | Run counts and cost (assistant credits 23.0746; org-run credits 44.6186; 44 org runs). |
| `s1/scheduler-survival.txt`, `s1/harness/scheduler_survival.py` | D-SURVIVE facts (8 schedulers; 0 running at a turn end; 0 kills) and the read-only extract that wrote them. |
| `s1/contract-loop.txt`, `s1/client-questions.txt`, `s1/deliverables-log.txt`, `s1/shell-writes.txt`, `s1/revise-playbook-attempts.txt`, `s1/lead-prompt-sizes.txt`, `s1/reflect-sections/`, `s1/regression-list/`, `s1/extract_mechanical-output.txt` | Mechanical extracts (facts, not scoring; indexes only). |
| `s1/harness/extract_mechanical.py`, `s1/harness/extract_mechanical.diff` | The per-stream adapted copy of the extract script (reviewer glob only; md5 `a64a05b5...` = frozen `extract_mechanical_s3.py`) and its diff. |

## Stream s2 (written by the s2 stream step, step 4 of 9; sandbox `/tmp/hirearchy-e6-s2-1792859296`; apparently VALID; 12 of 12 user turns; 25 counted org runs of 45 (+5 injection-window runs); 0 throttles; one H1 event in turn 3 (transient network error, one retry completed); memo 1 closed with L-ASIS, memo 2 delivered in turn 12 and not judged because of the cap, memo 3 not requested; no scheduler running at any turn end; not scored)
| File | What it is |
|---|---|
| `s2/run-log.md` | Facts: gates and setup, turn table, org runs, injection, contract/playbook/flag facts, ambient context, skill, model checks, throttling, validity (section 11), harness notes, cleanup and safety. |
| `s2/setup.txt` (incl. "AFTER the last turn"), `s2/epoch.txt`, `s2/sandbox-path.txt`, `s2/stream-start-utc.txt`, `s2/skill-check.txt`, `s2/ambient-context.txt`, `s2/model-checks.txt`, `s2/safety-before.txt`, `s2/safety-after.txt`, `s2/safety-diff.txt` | Per-stream setup, the freeze checks before and after, skill, ambient context, model checks and safety snapshots. |
| `s2/profiles/` | The assistant profile copy, `creations.txt`, `deletions.txt`, and the org's scheduler profile copy (`org-kiro-home--*.json`). |
| `s2/lena-lines.txt`, `s2/prompts/` (`t01..t12.txt`, `after_turn.sh`), `s2/turn-01..12.txt` (+ `.prompt`, `.cmd`, `.raw`, `.stderr`; turn 3 is the retry), `s2/turn-times.txt` (turn 3 has two lines), `s2/session-turn-times-utc.txt`, `s2/session-turn-mapping.txt` | The conversation (12 user turns) and the facilitator's helper; the mapping of session turns to user turns. |
| `s2/harness-failures/turn-03-h1-network-error.txt`, `s2/harness-failures/turn-03-attempt1/` | The H1 event of turn 3 (attempt 1's turn files, org state and session copy). |
| `s2/assistant-tool-calls.txt`, `s2/assistant-session-messages.jsonl`, `s2/assistant-session.json` | Assistant tool-call transcript (53 calls; session turn numbers) and the raw session store. |
| `s2/PLAN-FOR-YOU-product-proposal1.txt`, `s2/PLAN-FOR-YOU-product-proposal2.txt`, `s2/blueprint-proposal1.yaml`, `s2/blueprint-proposal2.yaml`, `s2/blueprint.yaml`, `s2/apply_org-result.txt` | The two `propose_org` results, the proposed and applied blueprints, the `apply_org` result. |
| `s2/injection/` | `injection-log.txt`, `request-args.json`, `text-identity.txt`, `window-runs.txt`, `window.txt`, `memo1-identification.txt`, pre/post-window model checks, marker. `s2/injection-stdout.txt` is the script's console output. |
| `s2/msgs/`, `s2/run-logs/`, `s2/events/`, `s2/org-files/`, `s2/service/`, `s2/playbook/`, `s2/scheduler.log`, `s2/org-git-log.txt`, `s2/observe-traces.txt`, `s2/observe-check.txt`, `s2/final-services-progress-status-health.txt`, `s2/copy_org_evidence-output.txt` | The org copied read-only after the stream. |
| `s2/org-kiro-sessions/`, `s2/run-session-map.txt` | The org agents' kiro sessions and the run-to-session map. |
| `s2/memos/` (final memos), `s2/memos/versions/` | Deliverables at the end and every committed version of each work file. |
| `s2/run-counts-by-turn.txt` (with the per-turn scheduler records and throttle scans), `s2/run-counts.txt`, `s2/cost.txt` | Run counts and cost (assistant credits 22.7056 incl. the failed attempt; org-run credits 29.6844; 30 org runs). |
| `s2/scheduler-survival.txt`, `s2/harness/scheduler_survival.py` | D-SURVIVE facts (6 schedulers; 0 running at a turn end; 0 kills) and the read-only extract that wrote them. |
| `s2/contract-loop.txt`, `s2/client-questions.txt`, `s2/deliverables-log.txt`, `s2/shell-writes.txt`, `s2/revise-playbook-attempts.txt`, `s2/lead-prompt-sizes.txt`, `s2/reflect-sections/`, `s2/regression-list/`, `s2/extract_mechanical-output.txt` | Mechanical extracts (facts, not scoring; indexes only). |
| `s2/harness/extract_mechanical.py`, `s2/harness/extract_mechanical.diff` | The per-stream adapted copy of the extract script (reviewer glob only; md5 `a64a05b5...` = frozen `extract_mechanical_s3.py`) and its diff. |

## Stream s3 (written by the s3 stream step, step 5 of 9; sandbox `/tmp/hirearchy-e6-s3-1792861552`; apparently VALID; 12 of 12 user turns; 26 counted org runs of 45 (+5 injection-window runs); 0 throttles; no H1 event; memo 1 delivered in turn 5, rejected once (H6) and accepted in turn 10 after its rework; memo 2 delivered in turn 11 and accepted in turn 12; memo 3 requested in turn 12, written and reviewed but not copied (3 questions to Lena, no turn left); the turn-5 scheduler (pid 9756) and its in-flight lead run were gone at the turn's end with no `scheduler.exit` (M-C-2 fact, see `s3/scheduler-survival.txt`); not scored)
| File | What it is |
|---|---|
| `s3/run-log.md` | Facts: gates and setup, turn table, org runs, scheduler, injection, contract/playbook/flag facts, ambient context, skill, model checks, throttling, validity (section 11), harness notes, cleanup and safety. |
| `s3/setup.txt` (incl. "AFTER the last turn"), `s3/epoch.txt`, `s3/sandbox-path.txt`, `s3/stream-start-utc.txt`, `s3/skill-check.txt`, `s3/ambient-context.txt`, `s3/model-checks.txt`, `s3/safety-before.txt`, `s3/safety-after.txt`, `s3/safety-diff.txt` | Per-stream setup, the freeze checks before and after, skill, ambient context, model checks and safety snapshots. |
| `s3/profiles/` | The assistant profile copy, `creations.txt`, `deletions.txt`, and the org's scheduler profile copies (`org-kiro-home--*.json`). |
| `s3/lena-lines.txt`, `s3/prompts/` (`t01..t12.txt`, `after_turn.sh`), `s3/turn-01..12.txt` (+ `.prompt`, `.cmd`, `.raw`, `.stderr`), `s3/turn-times.txt`, `s3/session-turn-times-utc.txt` | The conversation (12 user turns; session turns equal user turns) and the facilitator's helper. |
| `s3/assistant-tool-calls.txt`, `s3/assistant-session-messages.jsonl`, `s3/assistant-session.json` | Assistant tool-call transcript (58 calls) and the raw session store. |
| `s3/PLAN-FOR-YOU-product-proposal1.txt`, `s3/PLAN-FOR-YOU-product-proposal2.txt`, `s3/blueprint-proposal1.yaml`, `s3/blueprint-proposal2.yaml`, `s3/blueprint.yaml`, `s3/apply_org-result.txt` | The two `propose_org` results (12 and 16 runs per request), the proposed and applied blueprints, the `apply_org` result. |
| `s3/injection/` | `injection-log.txt`, `request-args.json`, `text-identity.txt` (+ `text-identity-check.txt`), `window-runs.txt` (+ `window-runs-facilitator.txt`), `window.txt`, `memo1-identification.txt`, `pre-injection-state.txt` (the dead scheduler's state before the injection), pre/post-window model checks, marker. `s3/injection-stdout.txt` is the script's console output. |
| `s3/msgs/`, `s3/run-logs/`, `s3/events/`, `s3/org-files/`, `s3/service/`, `s3/playbook/`, `s3/scheduler.log`, `s3/org-git-log.txt`, `s3/observe-traces.txt`, `s3/observe-check.txt`, `s3/final-services-progress-status-health.txt`, `s3/copy_org_evidence-output.txt` | The org copied read-only after the stream. |
| `s3/org-kiro-sessions/`, `s3/run-session-map.txt` | The org agents' kiro sessions and the run-to-session map (30 of 31 runs matched; the killed run has no session). |
| `s3/memos/` (final memos), `s3/memos/versions/` | Deliverables at the end and every committed version of each work file (memo 3's team version is only in `versions/`). |
| `s3/run-counts-by-turn.txt` (with the per-turn scheduler records and throttle scans), `s3/run-counts.txt`, `s3/cost.txt` | Run counts and cost (assistant credits 20.0276; org-run credits 31.1209; 31 org runs). |
| `s3/scheduler-survival.txt`, `s3/harness/scheduler_survival.py` | D-SURVIVE facts (6 schedulers; one, pid 9756, running past its turn's end and gone with a run in flight; 1 `run.orphan`; 0 kills) with the facilitator's added `ps` facts, and the read-only extract that wrote the listing. |
| `s3/contract-loop.txt`, `s3/client-questions.txt`, `s3/deliverables-log.txt`, `s3/shell-writes.txt`, `s3/revise-playbook-attempts.txt`, `s3/lead-prompt-sizes.txt`, `s3/reflect-sections/`, `s3/regression-list/`, `s3/extract_mechanical-output.txt` | Mechanical extracts (facts, not scoring; indexes only). |
| `s3/harness/extract_mechanical.py`, `s3/harness/extract_mechanical.diff` | The per-stream adapted copy of the extract script (reviewer glob only; md5 `a64a05b5...` = frozen `extract_mechanical_s3.py`) and its diff. |
