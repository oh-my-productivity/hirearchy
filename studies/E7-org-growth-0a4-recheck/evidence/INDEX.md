# E7 evidence index (the preflight and stream steps add their files; facts only, no scoring)

Times are local unless marked UTC (WET = UTC + 0 h since 2026-10-25T01:00Z; E6's were WEST = UTC + 1 h); org clocks and file names are UTC. Product: `main` = `18a4531`. Protocol
`protocol.md` md5 in `protocol.md5`.

## Study level, written by the pre-registration step (step 1 of 9, workflow `wf_31a4e82c906df7ea`)
| File | What it is |
|---|---|
| `protocol.md`, `protocol.md5`, `freeze.txt` | The pre-registered protocol (E6's, amended only by the E7 brief's step 1 items 1-10), its md5, and the freeze record (UTC time, HEAD, the empty freeze diff, the skill, harness, injection-script and source md5s, the C1 tools' md5s, the state at freeze). |
| `harness/` (`MD5SUMS`, `CHANGES.md` and 16 files) | E6's harness with paths, names and the product sha changed, `run_turn.sh`'s tool-call boundary (`; sleep 20` after the chat in the same command list), and the new read-only `ambient_snapshot.sh` (per-turn snapshots); `CHANGES.md` has every change against E6 with its diff. |
| `notes/`, `answer-key.md` | E2's three notes files and the private answer key, byte-identical to E6's (protocol 4.6). |

## Stream s1 (step 3 of 9; facts only, not scored): `evidence/s1/`
Sandbox `/tmp/hirearchy-e7-s1-1792911600`; profile `hirearchy-study-e7-s1-assistant` (deleted after the stream); 11 user turns; 41 org runs (5 in the injection window).
| File or folder | What it is |
|---|---|
| `run-log.md`, `setup.txt`, `lena-lines.txt`, `ambient-context.txt`, `skill-check.txt`, `model-checks.txt` | Gates and freeze (before and after), Lena's line and its facts for every turn, the ambient check, the skill check and stratum, the model checks. |
| `profiles/` | The assistant profile (copy), the org scheduler profile (copy), `creations.txt`, `deletions.txt`. |
| `safety-before.txt`, `safety-after.txt`, `safety-diff.txt`, `ambient/` | Stream safety snapshots and their diff; `ambient/` holds `setup.txt`, `turn-NN-before.txt`, `turn-NN-after.txt` (NN = 01-11) and `end.txt` (E7 item 4's per-turn snapshots). |
| `turn-NN.prompt.txt`, `.cmd.txt`, `.txt`, `.raw.txt`, `.stderr.txt`, `turn-times.txt`, `session-turn-times-utc.txt`, `assistant-tool-calls.txt`, `assistant-session*.json*` | The conversation and the assistant session store. |
| `PLAN-FOR-YOU-product-proposal1.txt`, `blueprint-proposal1.yaml`, `blueprint.yaml`, `apply_org-result.txt` | The one propose_org call and the applied blueprint. |
| `injection/` | The injection: log, request args, `window.txt`, `memo1-identification.txt`, `text-identity.txt`, `window-runs.txt`, script stdout and stderr. |
| `run-counts.txt`, `run-counts-by-turn.txt`, `run-logs/`, `msgs/`, `service/`, `playbook/`, `reflect-sections/`, `regression-list/`, `events/`, `scheduler.log`, `org-files/`, `memos/` (with `versions/`), `org-kiro-sessions/`, `run-session-map.txt`, `org-git-log.txt`, `observe-check.txt`, `observe-traces.txt`, `final-services-progress-status-health.txt` | The org, copied read-only; `run-counts-by-turn.txt` also holds the per-turn scheduler, signal and throttle records. |
| `client-questions.txt`, `contract-loop.txt`, `deliverables-log.txt`, `shell-writes.txt`, `revise-playbook-attempts.txt`, `cost.txt`, `lead-prompt-sizes.txt` | Mechanical extracts (facts). |
| `scheduler-survival.txt` | D-SURVIVE and D-SIGNAL extract (0 `scheduler.signal`, 9 schedulers, all ended by their own exit). |
| `harness/` | Adapted copies: `extract_mechanical.py` (service folder, reviewer glob) and `scheduler_survival.py` (adds the signal listing), each with its diff. |
| `prompts/` | The Lena prompt files `t01`-`t11` and the facilitator's `after_turn.sh`. |

## Stream s2 (step 4 of 9; facts only, not scored): `evidence/s2/`
Sandbox `/tmp/hirearchy-e7-s2-1792914064`; profile `hirearchy-study-e7-s2-assistant` (deleted after the stream); 12 user turns; 34 org runs (5 in the injection window).
| File or folder | What it is |
|---|---|
| `run-log.md`, `setup.txt`, `lena-lines.txt`, `ambient-context.txt`, `skill-check.txt`, `model-checks.txt` | Gates and freeze (before and after), Lena's line and its facts for every turn, the ambient check, the skill check and stratum, the model checks. |
| `profiles/` | The assistant profile (copy), the org scheduler profile (copy), `creations.txt`, `deletions.txt`. |
| `safety-before.txt`, `safety-after.txt`, `safety-diff.txt`, `ambient/` | Stream safety snapshots and their diff; `ambient/` holds `setup.txt`, `turn-NN-before.txt`, `turn-NN-after.txt` (NN = 01-12) and `end.txt` (E7 item 4's per-turn snapshots). |
| `turn-NN.prompt.txt`, `.cmd.txt`, `.txt`, `.raw.txt`, `.stderr.txt`, `turn-times.txt`, `session-turn-times-utc.txt`, `assistant-tool-calls.txt`, `assistant-session*.json*` | The conversation and the assistant session store. |
| `PLAN-FOR-YOU-product-proposal1.txt`, `blueprint-proposal1.yaml`, `blueprint.yaml`, `apply_org-result.txt` | The one propose_org call and the applied blueprint. |
| `injection/` | The injection: log, request args, `window.txt`, `memo1-identification.txt`, `text-identity.txt`, `window-runs.txt`, script stdout and stderr. |
| `run-counts.txt`, `run-counts-by-turn.txt`, `run-logs/`, `msgs/`, `service/`, `playbook/`, `reflect-sections/`, `regression-list/`, `events/`, `scheduler.log`, `org-files/`, `memos/` (with `versions/`), `org-kiro-sessions/`, `run-session-map.txt`, `org-git-log.txt`, `observe-check.txt`, `observe-traces.txt`, `final-services-progress-status-health.txt` | The org, copied read-only; `run-counts-by-turn.txt` also holds the per-turn scheduler, signal and throttle records. |
| `client-questions.txt`, `contract-loop.txt`, `deliverables-log.txt`, `shell-writes.txt`, `revise-playbook-attempts.txt`, `cost.txt`, `lead-prompt-sizes.txt` | Mechanical extracts (facts). |
| `scheduler-survival.txt` | D-SURVIVE and D-SIGNAL extract (0 `scheduler.signal`, 6 schedulers, all ended by their own exit). |
| `harness/` | `extract_mechanical.py` (the frozen `extract_mechanical_s2.py`, unchanged), `scheduler_survival.py` (s1's, s2 names; with its diff) and `injection_files.py` (writes the injection's text-identity and window-runs files; read-only). |
| `prompts/` | The Lena prompt files `t01`-`t12` and the facilitator's `after_turn.sh`. |

## Stream s3 (step 5 of 9; facts only, not scored): `evidence/s3/`
Sandbox `/tmp/hirearchy-e7-s3-1792916437`; profile `hirearchy-study-e7-s3-assistant` (deleted after the stream); 13 user turns; 40 org runs (5 in the injection window).
| File or folder | What it is |
|---|---|
| `run-log.md`, `setup.txt`, `lena-lines.txt`, `ambient-context.txt`, `skill-check.txt`, `model-checks.txt` | Gates and freeze (before and after), Lena's line and its facts for every turn, the ambient check, the skill check and stratum, the model checks. |
| `profiles/` | The assistant profile (copy), the org scheduler profile (copy), `creations.txt`, `deletions.txt`. |
| `safety-before.txt`, `safety-after.txt`, `safety-diff.txt`, `ambient/` | Stream safety snapshots and their diff; `ambient/` holds `setup.txt`, `turn-NN-before.txt`, `turn-NN-after.txt` (NN = 01-13) and `end.txt` (E7 item 4's per-turn snapshots). |
| `turn-NN.prompt.txt`, `.cmd.txt`, `.txt`, `.raw.txt`, `.stderr.txt`, `turn-times.txt`, `session-turn-times-utc.txt`, `assistant-tool-calls.txt`, `assistant-session*.json*` | The conversation and the assistant session store. |
| `PLAN-FOR-YOU-product-proposal1.txt`, `blueprint-proposal1.yaml`, `blueprint.yaml`, `apply_org-result.txt` | The one propose_org call and the applied blueprint. |
| `injection/` | The injection: log, request args, `window.txt`, `memo1-identification.txt`, `text-identity.txt`, `window-runs.txt`, script stdout and stderr. |
| `run-counts.txt`, `run-counts-by-turn.txt`, `run-logs/`, `msgs/`, `service/`, `playbook/`, `reflect-sections/`, `regression-list/`, `events/`, `scheduler.log`, `org-files/`, `memos/` (with `versions/`), `org-kiro-sessions/`, `run-session-map.txt`, `org-git-log.txt`, `observe-check.txt`, `observe-traces.txt`, `final-services-progress-status-health.txt` | The org, copied read-only; `run-counts-by-turn.txt` also holds the per-turn scheduler, signal and throttle records. |
| `client-questions.txt`, `contract-loop.txt`, `deliverables-log.txt`, `shell-writes.txt`, `revise-playbook-attempts.txt`, `cost.txt`, `lead-prompt-sizes.txt` | Mechanical extracts (facts). |
| `scheduler-survival.txt` | D-SURVIVE and D-SIGNAL extract (0 `scheduler.signal`, 8 schedulers, all ended by their own exit). |
| `harness/` | `extract_mechanical.py` (the frozen `extract_mechanical_s2.py`, unchanged), `scheduler_survival.py` (s2's, s3 names) and `injection_files.py` (s2's, s3 name; read-only). |
| `harness-failures/` | `note-turn03-combined-call.txt` (turn 3's prompt copy, lena-lines entry and run_turn.sh ran in one tool call; no boundary failure). |
| `prompts/` | The Lena prompt files `t01`-`t13` and the facilitator's `after_turn.sh`. |
