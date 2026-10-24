# E5 evidence index (the stream steps add their streams; facts only, no scoring)

Times are local (WEST = UTC + 1 h) unless marked UTC; org clocks and file names are UTC. Product: `main` = `6618c0d`. Protocol `protocol.md` md5 `afd437c103407ec5899e4993b465cf25`.
(Study-level files written by the pre-registration and preflight steps: `protocol.md`, `protocol.md5`, `freeze.txt`, `answer-key.md`, `notes/`, `harness/`, `preflight.md`, `preflight/`, `probe/`, `deterministic/`, `preflight-safety-*.txt`.)

## Stream s1 (sandbox `/tmp/hirearchy-e5-s1-1792811051`; VALID; 12 of 12 user turns; 25 counted org runs of 45 (+5 injection-window runs); 0 throttles)
| File | What it is |
|---|---|
| `s1/run-log.md` | Facts: gates and setup, turn table, org runs, injection, contract/playbook facts, ambient context, model checks, throttling, validity (section 11), harness notes, cleanup and safety. |
| `s1/setup.txt` (incl. "AFTER the last turn"), `s1/epoch.txt`, `s1/sandbox-path.txt`, `s1/stream-start-utc.txt`, `s1/skill-check.txt`, `s1/ambient-context.txt`, `s1/model-checks.txt`, `s1/safety-before.txt`, `s1/safety-after.txt`, `s1/safety-diff.txt` | Per-stream setup, gate and check records. |
| `s1/profiles/` | The assistant profile copy, `creations.txt`, `deletions.txt`, and the org's scheduler profile copy (`org-kiro-home--*.json`). |
| `s1/lena-lines.txt`, `s1/prompts/` (`t01..t12.txt`, `after_turn.sh`), `s1/turn-01..12.txt` (+ `.prompt`, `.cmd`, `.raw`, `.stderr`), `s1/turn-times.txt`, `s1/session-turn-times-utc.txt` | The conversation (12 user turns) and the facilitator's lines with their rule ids and deciding facts. |
| `s1/assistant-tool-calls.txt`, `s1/assistant-session-messages.jsonl`, `s1/assistant-session.json` | Assistant tool-call transcript (59 calls) and the raw session store. |
| `s1/PLAN-FOR-YOU-product-proposal1.txt`, `s1/blueprint-proposal1.yaml`, `s1/blueprint.yaml`, `s1/apply_org-result.txt` | The `propose_org` result, the proposed and applied blueprint, the `apply_org` result. |
| `s1/injection/` | `injection-log.txt`, `request-args.json`, `text-identity.txt`, `window-runs.txt`, `window.txt`, `memo1-identification.txt`, marker. |
| `s1/msgs/`, `s1/run-logs/`, `s1/events/`, `s1/org-files/`, `s1/service/`, `s1/playbook/`, `s1/scheduler.log`, `s1/org-git-log.txt`, `s1/observe-traces.txt`, `s1/observe-check.txt`, `s1/final-services-progress-status-health.txt`, `s1/copy_org_evidence-output.txt` | The org (copied by `harness/copy_org_evidence.sh`, read-only) and the post-stream read-only CLI output. |
| `s1/org-kiro-sessions/`, `s1/run-session-map.txt` | The org agents' kiro sessions and the run-to-session map. |
| `s1/memos/` (final memos), `s1/memos/versions/` | Deliverables at the end and every committed version of each work file. |
| `s1/run-counts-by-turn.txt`, `s1/run-counts.txt`, `s1/cost.txt` | Run counts and cost (assistant credits 18.5058; org-run credits 26.8487; 30 org runs). |
| `s1/contract-loop.txt`, `s1/client-questions.txt`, `s1/deliverables-log.txt`, `s1/shell-writes.txt`, `s1/revise-playbook-attempts.txt`, `s1/lead-prompt-sizes.txt`, `s1/reflect-sections/`, `s1/regression-list/` | Mechanical extracts (facts, not scoring; indexes only, the raw files decide). |
| `s1/harness/extract_mechanical.py`, `s1/harness/extract_mechanical.diff` | The per-stream adapted copy of the extract script (service folder and reviewer glob only; md5 `6a1f0a6e...` = frozen `extract_mechanical_s2.py`) and its diff. |

## Stream s2 (sandbox `/tmp/hirearchy-e5-s2-1792812864`; VALID; 12 of 12 user turns; 29 counted org runs of 45 (+5 injection-window runs); 0 throttles; memo 3 requested in turn 12 but not delivered or judged at the cap)
| File | What it is |
|---|---|
| `s2/run-log.md` | Facts: gates and setup, turn table, org runs, injection, contract/playbook/flag facts, ambient context, skill, model checks, throttling, validity (section 11), harness notes, cleanup and safety. |
| `s2/setup.txt` (incl. "AFTER the last turn"), `s2/epoch.txt`, `s2/sandbox-path.txt`, `s2/stream-start-utc.txt`, `s2/skill-check.txt`, `s2/ambient-context.txt`, `s2/model-checks.txt`, `s2/safety-before.txt`, `s2/safety-after.txt`, `s2/safety-diff.txt` | Per-stream setup, gate and check records. |
| `s2/profiles/` | The assistant profile copy, `creations.txt`, `deletions.txt`, and the org's scheduler profile copy (`org-kiro-home--*.json`). |
| `s2/lena-lines.txt`, `s2/prompts/` (`t01..t12.txt`, `after_turn.sh`, `skill_check.py`), `s2/turn-01..12.txt` (+ `.prompt`, `.cmd`, `.raw`, `.stderr`), `s2/turn-times.txt`, `s2/session-turn-times-utc.txt` | The conversation (12 user turns) and the facilitator's lines with their rule ids and deciding facts. |
| `s2/assistant-tool-calls.txt`, `s2/assistant-session-messages.jsonl`, `s2/assistant-session.json` | Assistant tool-call transcript (58 calls) and the raw session store. |
| `s2/PLAN-FOR-YOU-product-proposal1.txt`, `s2/blueprint-proposal1.yaml`, `s2/blueprint.yaml`, `s2/apply_org-result.txt` | The `propose_org` result, the proposed and applied blueprint, the `apply_org` result. |
| `s2/injection/`, `s2/injection-stdout.txt` | `injection-log.txt`, `request-args.json`, `text-identity.txt`, `window-runs.txt`, `window.txt`, `memo1-identification.txt`, marker; the script's console output. |
| `s2/msgs/`, `s2/run-logs/`, `s2/events/`, `s2/org-files/`, `s2/service/`, `s2/playbook/`, `s2/scheduler.log`, `s2/org-git-log.txt`, `s2/observe-traces.txt`, `s2/observe-check.txt`, `s2/final-services-progress-status-health.txt`, `s2/copy_org_evidence-output.txt` | The org (copied by `harness/copy_org_evidence.sh`, read-only) and the post-stream read-only CLI output. |
| `s2/org-kiro-sessions/`, `s2/run-session-map.txt` | The org agents' kiro sessions and the run-to-session map. |
| `s2/memos/` (final memos), `s2/memos/versions/` | Deliverables at the end (memos 1 and 2) and every committed version of each work file (memo 3's team version included). |
| `s2/run-counts-by-turn.txt`, `s2/run-counts.txt`, `s2/cost.txt` | Run counts and cost (assistant credits 16.4039; org-run credits 31.3814; 34 org runs). |
| `s2/contract-loop.txt`, `s2/client-questions.txt`, `s2/deliverables-log.txt`, `s2/shell-writes.txt`, `s2/revise-playbook-attempts.txt`, `s2/lead-prompt-sizes.txt`, `s2/reflect-sections/`, `s2/regression-list/`, `s2/extract_mechanical-stdout.txt` | Mechanical extracts (facts, not scoring; indexes only, the raw files decide), from the frozen `harness/extract_mechanical_s2.py` run unchanged (no `s2/harness/`). |

## Stream s3 (sandbox `/tmp/hirearchy-e5-s3-1792814736`; VALID; 12 of 12 user turns; 28 counted org runs of 45 (+5 injection-window runs); 0 throttles; memo 3 requested in turn 12 but not delivered or judged at the cap; one writer run killed by SIGTERM at the end of turn 4, see `s3/run-log.md` "Validity")
| File | What it is |
|---|---|
| `s3/run-log.md` | Facts: gates and setup, turn table, org runs, injection, contract/playbook/flag facts, ambient context, model checks, throttling, validity (section 11, with the H8 point for the manager), harness notes, cleanup and safety. |
| `s3/setup.txt` (incl. "AFTER the last turn"), `s3/epoch.txt`, `s3/sandbox-path.txt`, `s3/stream-start-utc.txt`, `s3/skill-check.txt`, `s3/ambient-context.txt`, `s3/model-checks.txt`, `s3/safety-before.txt`, `s3/safety-after.txt`, `s3/safety-diff.txt`, `s3/post-stream-times.txt` | Per-stream setup, gate and check records. |
| `s3/profiles/` | The assistant profile copy, `creations.txt`, `deletions.txt`, and the org's scheduler profile copy (`org-kiro-home--*.json`). |
| `s3/lena-lines.txt`, `s3/prompts/` (`t01..t12.txt`, `after_turn.sh`), `s3/turn-01..12.txt` (+ `.prompt`, `.cmd`, `.raw`, `.stderr`), `s3/turn-times.txt`, `s3/session-turn-times-utc.txt` | The conversation (12 user turns) and the facilitator's lines with their rule ids and deciding facts. |
| `s3/assistant-tool-calls.txt`, `s3/assistant-session-messages.jsonl`, `s3/assistant-session.json` | Assistant tool-call transcript (76 calls) and the raw session store. |
| `s3/PLAN-FOR-YOU-product-proposal1.txt`, `s3/PLAN-FOR-YOU-product-proposal2.txt`, `s3/blueprint-proposal1.yaml`, `s3/blueprint-proposal2.yaml`, `s3/blueprint.yaml`, `s3/apply_org-result.txt` | The two `propose_org` calls (the first failed: tool not loaded), the proposed and applied blueprint, the `apply_org` result. |
| `s3/injection/` | `injection-log.txt`, `request-args.json`, `text-identity.txt`, `window-runs.txt`, `window.txt`, `memo1-identification.txt`, `facts.txt`, `script-stdout.txt`, `run-wrapper.txt`, marker; facilitator copies `text-identity-facilitator.txt`, `window-runs-facilitator.txt` and the generator `make_window_runs.py`. |
| `s3/msgs/`, `s3/run-logs/`, `s3/events/`, `s3/org-files/`, `s3/service/`, `s3/playbook/`, `s3/scheduler.log`, `s3/org-git-log.txt`, `s3/observe-traces.txt`, `s3/observe-check.txt`, `s3/final-services-progress-status-health.txt`, `s3/copy_org_evidence-output.txt` | The org (copied by `harness/copy_org_evidence.sh`, read-only) and the post-stream read-only CLI output. |
| `s3/org-kiro-sessions/`, `s3/run-session-map.txt` | The org agents' kiro sessions and the run-to-session map (32 of 33 runs matched; the killed run is the unmatched one). |
| `s3/memos/` (final memos), `s3/memos/versions/` | Deliverables at the end and every committed version of each work file. |
| `s3/run-counts-by-turn.txt`, `s3/run-counts.txt`, `s3/cost.txt` | Run counts and cost (assistant credits 21.7869; org-run credits 33.3261; 33 org runs). |
| `s3/contract-loop.txt`, `s3/client-questions.txt`, `s3/deliverables-log.txt`, `s3/shell-writes.txt`, `s3/revise-playbook-attempts.txt`, `s3/lead-prompt-sizes.txt`, `s3/reflect-sections/`, `s3/regression-list/`, `s3/extract_mechanical-output.txt` | Mechanical extracts (facts, not scoring; indexes only, the raw files decide). The frozen `harness/extract_mechanical_s2.py` was run unchanged (no `s3/harness/`). |
