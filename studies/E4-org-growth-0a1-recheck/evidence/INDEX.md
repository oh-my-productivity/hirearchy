# E4 evidence index (started by the harness-setup step; the run steps add their streams)

Facts only; no scoring. Times are local (WEST); the org clock and file names are UTC (= local - 1 h). Product: `main` = `d85cc13`.
Streams: see the stream sections below (s1 INVALID, s1r, s2 INVALID, s2r, s3). Sandbox of each: `/tmp/hirearchy-e4-s<N>-<epoch>` (created by its run step).

## Protocol and harness
| File | What it is |
|---|---|
| `protocol.md` | Pre-registered E4 protocol (frozen: md5 `584b6cc71e3d073d10d45c1c2e64325e` at setup; `protocol.md5` is written by the s1 step). Never edited. |
| `setup.md` | Harness-preparation record: safety-before, skill copy and md5s, prep profile and load check, ambient-context pre-flight, injection mechanism, model availability. |
| `harness/safety-snapshot.sh` | Read-only snapshot script (protocol 4.8 content), reused by the run steps for `safety-before/after`. |
| `harness/inject_root_rework.py` | Facilitator's root-injection script for clause 1 (protocol section 5). md5 `c80e25d65fe58cdb97d7faa758d59484` at setup; not yet run against any org; frozen at the first successful `request`. |
| `harness/staging/.kiro/skills/hirearchy/SKILL.md` | Byte-identical copy of the repo skill (md5 `573495bb613f19f7c07ce86508ebae4f`), to be `cp`-ed into each `S/.kiro/skills/hirearchy/`. |
| `harness/staging/.kiro/settings/cli.json` | The protocol's candidate workspace settings (md5 `c100733e0277c92b4703e9ae74a54f81`). NOT the final `harness/workspace-cli.json`; the s1 probe decides. |
| `harness/staging/hirearchy-study-e4-prep-1792639838.json` | Copy of the prep assistant profile (V3 schema; md5 `0f711c96814a3d67a51609f02f111605`). Not used by any stream. |
| `setup-preflight/` | The pre-flight of setup.md section 3-4: `preflight-call.stdout.txt` / `.stderr.txt`, `preflight-session.json`, `preflight-session-messages.jsonl` (raw session store), `preflight-ambient-context.txt`, `settings-list.txt`, `models-list.txt`, `global-cli-md5-before.txt`, `preflight-call-start-epoch.txt`. Not the protocol probe (that is `probe/`, written by s1). |

## Safety
| File | What it is |
|---|---|
| `safety-before.md` | Snapshot taken by the setup step (04:30 local) before any E4 profile, sandbox or probe: git HEAD/status, md5 of `~/.kiro/settings/*`, global skill, `memories.db`, agents list and md5s, `ls ~/.kiro/skills` and steering, `/Users/aminalizadeh/organization` listing, file count, newest mtime and tree digest, other orgs, protocol md5. |
| `safety-before.txt`, `safety-after.txt` | Study level. `safety-before.txt` was written by the s1 step (before the probe); `safety-after.txt` by the s3 step (the last stream, after its cleanup), with notes on the settings md5 differences (they predate s1r). |

## To be added by the run steps (protocol section 7)
`protocol.md5`, `answer-key.md`, `notes/`, `models.txt`, `deterministic/pytest-e2e-org-growth.txt`, `probe/`, `harness/workspace-cli.json`, and per stream `s<N>/` (E3's evidence structure plus `setup.txt`,
`lena-lines.txt`, `ambient-context.txt`, `skill-check.txt`, `injection/` and the mechanical extracts). The scoring and gate steps add their own files.


## Stream s1 (sandbox `/tmp/hirearchy-e4-s1-1792640562`; STOPPED at turn 4: org runs had no hirearchy tools, protocol 11 H8 candidate; escalated)
| File | What it is |
|---|---|
| `s1/run-log.md` | Facts: setup, turn table, org runs, the failure, cleanup and safety. |
| `s1/harness-failures/H8-org-runs-had-no-hirearchy-tools.md` (+ `diag-*`) | What the two lead runs showed, comparison with E3, the 4 diagnostic calls with a throwaway profile. |
| `s1/setup.txt`, `s1/skill-check.txt`, `s1/ambient-context.txt`, `s1/safety-before.txt`, `s1/safety-after.txt`, `s1/profiles/` | Per-stream setup records; profiles copied before deletion (`deletions.txt`). |
| `s1/lena-lines.txt`, `s1/prompts/`, `s1/turn-01..04.txt` (+ `.raw`, `.stderr`, `.prompt`), `s1/turn-times.txt`, `s1/session-turn-times-utc.txt` | The conversation (4 user turns). |
| `s1/assistant-tool-calls.txt`, `s1/assistant-session-messages.jsonl`, `s1/assistant-session.json` | Assistant tool-call transcript (32 calls) and the raw session store. |
| `s1/PLAN-FOR-YOU-product-proposal1..3.txt`, `s1/blueprint-proposal1..3.yaml`, `s1/blueprint.yaml` | The three `propose_org` results/blueprints; the applied blueprint. |
| `s1/msgs/`, `s1/run-logs/`, `s1/events/`, `s1/org-files/`, `s1/service/`, `s1/playbook/`, `s1/scheduler.log`, `s1/org-git-log.txt`, `s1/observe-traces.txt`, `s1/final-services-progress-status-health.txt` | The org (copied by `harness/copy_org_evidence.sh`). |
| `s1/run-counts-by-turn.txt`, `s1/run-counts.txt`, `s1/cost.txt` | Run counts and cost (assistant credits 8.2310; 2 org runs). |

## Study-level files added by the s1 step
`protocol.md5`, `answer-key.md`, `notes/`, `models.txt`, `safety-before.txt`, `deterministic/pytest-e2e-org-growth.txt`, `probe/` (`PROBE-RESULT.md`), `harness/workspace-cli.json` (+ `.md5`), `harness/run_turn.sh`, `harness/org_state.py`, `harness/ambient_context.py`, `harness/extract_tool_calls.py`, `harness/copy_org_evidence.sh`.

## Restart after the kiro runtime fix (product `main` = `7d86c31`)
s1 stays INVALID (H8) and `s1/` is unchanged. The replacement stream is `s1r`, followed by `s2` and `s3`. The study needs 3 valid streams: `s1r`, `s2` and `s3`.
| File | What it is |
|---|---|
| `manager-decision-restart.md` | The manager's binding decision: replacement stream `s1r`, what amendment 1 may change, the harness preflight before `s1r`. |
| `protocol-amendment-1.md` | Protocol amendment 1, pre-registered before `s1r` turn 1. It contains: product `7d86c31` (4.1 diff against `7d86c31`; skill md5 `573495bb613f19f7c07ce86508ebae4f`); the streams `s1r`/`s2`/`s3`; section 10 methods re-validated against the V3 run-log and event formats, with real examples; the readiness-refusal rule (H8-type); the agent-visible changes since `d85cc13`, listed as context. Pass rules, models, injection, caps, Lena's lines, ambient-context and safety rules are unchanged. Frozen; never edited. |
| `protocol-amendment-1.md5` | md5 of the amendment: `1ec9e658e3bd59ab9d9f785986a26c19`. The `s1r`, `s2` and `s3` run steps check it, together with `protocol.md5` (`584b6cc71e3d073d10d45c1c2e64325e`, re-verified after the freeze), before their turn 1. |
| `deterministic/at-7d86c31/SUMMARY.md` | The deterministic part (4.9) at `7d86c31`: both commands exit 0, 12 passed and 0 failed each; `test_3`, `test_7`, `test_11` and `test_12` PASSED. |
| `deterministic/at-7d86c31/pytest-e2e-org-growth.txt` | Raw output of protocol 4.9's command, verbatim: `uv run pytest -p no:cacheprovider -v tests/e2e/test_org_growth_0a.py`. |
| `deterministic/at-7d86c31/pytest-q-e2e-org-growth.txt` | Raw output of `uv run pytest -q tests/e2e/test_org_growth_0a.py`. |

`deterministic/pytest-e2e-org-growth.txt` (run at `d85cc13` by the s1 step) is kept unchanged as the record of that run.


## Stream s1r (replacement for the INVALID s1; product `main` = `7d86c31`; sandbox `/tmp/hirearchy-e4-s1r-1792693447`; org kiro home `~/Library/Application Support/hirearchy/kiro-home/hirearchy-e4-s1r-1792693-bfcddd47e6ecb16c/`; status: complete, 12 of 12 user turns, 34 org runs outside the injection window + 5 inside; run 2026-10-22 18:24-19:49Z; facts only, not scored)
| File | What it is |
|---|---|
| `s1r/run-log.md` | Facts: gates, setup, turn table, org runs, injection, contract/playbook facts, ambient context (memories block absent: open question for the manager on H3), cleanup and safety. |
| `s1r/setup.txt`, `s1r/skill-check.txt`, `s1r/ambient-context.txt`, `s1r/models-list.txt`, `s1r/safety-before.txt`, `s1r/safety-after.txt`, `s1r/epoch.txt`, `s1r/sandbox-path.txt`, `s1r/stream-start-utc.txt` | Per-stream setup records (4.1 checks before and after the last turn, profile diff against s1, md5 gates, skill/ambient checks, safety snapshots). |
| `s1r/profiles/` | The assistant profile (copied, verified, deleted: `deletions.txt`) and copies of the org's two scheduler profiles from the org kiro home (`org-kiro-home--*`; not deleted, amendment A3.2). |
| `s1r/lena-lines.txt`, `s1r/prompts/`, `s1r/turn-01..12.txt` (+ `.raw`, `.stderr`, `.prompt`), `s1r/turn-times.txt`, `s1r/session-turn-times-utc.txt` | The conversation (12 user turns): Lena's line with the rule ids and deciding facts, and the assistant's output. |
| `s1r/assistant-tool-calls.txt`, `s1r/assistant-session-messages.jsonl`, `s1r/assistant-session.json` | Assistant tool-call transcript (54 calls) and the raw session store. |
| `s1r/injection/` | `injection-log.txt` (script md5, every call verbatim), `request-args.json`, `text-identity.txt`, `window-runs.txt`, `FREEZE.txt` (script frozen at md5 `c80e25d65fe58cdb97d7faa758d59484`), `memo1-identification.txt`, `window.txt`, script stdout/stderr. |
| `s1r/msgs/`, `s1r/run-logs/`, `s1r/events/`, `s1r/org-files/`, `s1r/service/`, `s1r/playbook/`, `s1r/scheduler.log`, `s1r/org-git-log.txt`, `s1r/observe-traces.txt`, `s1r/final-services-progress-status-health.txt` | The org (copied by `harness/copy_org_evidence.sh`); `service/history--*` and `playbook/history--*`, `current-*` are from the org's `history/` dirs (uncommitted versions). |
| `s1r/org-kiro-sessions/<hash>/<session id>/`, `s1r/run-session-map.txt` | Amendment A3.2: the 39 org-run kiro sessions (`session.json`, `messages.jsonl`) and the run-to-session match (39 of 39). |
| `s1r/revise-playbook-attempts.txt`, `s1r/contract-loop.txt`, `s1r/client-questions.txt`, `s1r/deliverables-log.txt`, `s1r/shell-writes.txt`, `s1r/lead-prompt-sizes.txt`, `s1r/reflect-sections/`, `s1r/regression-list/` | Mechanical extracts (protocol 7.2). |
| `s1r/memos/` (+ `versions/`), `s1r/run-counts-by-turn.txt`, `s1r/run-counts.txt`, `s1r/cost.txt` | Final memos and org-git versions; run counts per turn and final; assistant and org-run credits (org-run credits read from the kiro sessions, A3.3 10.6). |
| `harness/extract_mechanical.py` | Added by the s1r step: the mechanical-extract script (md5 `ec2d7db51fd06233f182c0153ecd6957`), reusable for s2 and s3 (`uv --directory /Volumes/workspace/hirearchy run python extract_mechanical.py <stream>`). |


## Stream s2 (product `main` = `7d86c31`; sandbox `/tmp/hirearchy-e4-s2-1792698851`; org kiro home `~/Library/Application Support/hirearchy/kiro-home/hirearchy-e4-s2-17926988-212f59b7daf49c3f/`; status: **INVALID (H8)**, ruled by the manager in `manager-decision-s2-and-h3.md` ruling 1; STOPPED after the injection, before user turn 6 (a model-service error failed an injection-window org run and the injected task stalled); replacement stream `s2r`; observations before the failure stand; 5 of 12 user turns; 14 org runs outside the injection window + 5 inside; run 2026-10-22 19:54-20:44Z; facts only, not scored)
| File | What it is |
|---|---|
| `s2/run-log.md` | Facts: gates, setup, turn table, org runs, injection, the stop, contract/client-question facts, ambient context, cleanup and safety. |
| `s2/harness-failures/H8-candidate-org-run-model-throttle-stalled-injected-task.md` (ruled H8 by the manager) | The failed run (`lead/reviewer@20261022T202454859379`, `ModelThrottleError`), the scheduler lines, the stalled injected task, the script's `progress` loop, and the handling. |
| `s2/setup.txt`, `s2/skill-check.txt`, `s2/ambient-context.txt`, `s2/models-list.txt`, `s2/safety-before.txt`, `s2/safety-after.txt`, `s2/epoch.txt`, `s2/sandbox-path.txt`, `s2/stream-start-utc.txt` | Per-stream setup records (4.1 checks before and after, profile diff against s1r, md5 gates, skill/ambient checks, safety snapshots). |
| `s2/profiles/` | The assistant profile (copied, verified, deleted: `deletions.txt`) and the copy of the org's scheduler profile from the org kiro home (`org-kiro-home--*`; not deleted, amendment A3.2). |
| `s2/lena-lines.txt`, `s2/prompts/`, `s2/turn-01..05.txt` (+ `.raw`, `.stderr`, `.prompt`), `s2/turn-times.txt`, `s2/session-turn-times-utc.txt` | The conversation (5 user turns): Lena's line with the rule ids and deciding facts; turn 6 recorded as not sent. |
| `s2/assistant-tool-calls.txt`, `s2/assistant-session-messages.jsonl`, `s2/assistant-session.json` | Assistant tool-call transcript (27 calls) and the raw session store. |
| `s2/PLAN-FOR-YOU-product-proposal1..2.txt`, `s2/blueprint-proposal1..2.yaml`, `s2/blueprint.yaml`, `s2/apply_org-result.txt` | The two `propose_org` results/blueprints; the applied blueprint and the `apply_org` reply. |
| `s2/injection/` | `injection-log.txt` (script md5, every call verbatim), `request-args.json`, `text-identity.txt`, `window-runs.txt`, `FREEZE.txt` (script md5 `c80e25d65fe58cdb97d7faa758d59484`, as frozen by s1r), `memo1-identification.txt`, `window.txt`, script stdout/stderr. |
| `s2/msgs/`, `s2/run-logs/`, `s2/events/`, `s2/org-files/`, `s2/service/`, `s2/playbook/`, `s2/scheduler.log`, `s2/org-git-log.txt`, `s2/observe-traces.txt`, `s2/final-services-progress-status-health.txt` | The org (copied by `harness/copy_org_evidence.sh`). `events/` holds 36,516 `tool.call` events of the injection script's server (`mcp-41795-*.jsonl`). |
| `s2/org-kiro-sessions/<hash>/<session id>/`, `s2/run-session-map.txt` | Amendment A3.2: the 19 org-run kiro sessions and the run-to-session match (19 of 19). |
| `s2/revise-playbook-attempts.txt`, `s2/contract-loop.txt`, `s2/client-questions.txt`, `s2/deliverables-log.txt`, `s2/shell-writes.txt`, `s2/lead-prompt-sizes.txt`, `s2/reflect-sections/`, `s2/regression-list/` | Mechanical extracts (protocol 7.2). |
| `s2/memos/` (+ `versions/`), `s2/run-counts-by-turn.txt`, `s2/run-counts.txt`, `s2/cost.txt` | Memo 1 as delivered and its org-git versions; run counts per turn and final; assistant and org-run credits. |
| `harness/extract_mechanical_s2.py` | Added by the s2 step: a copy of `extract_mechanical.py` (unchanged, md5 `ec2d7db51fd06233f182c0153ecd6957`) with s2's service name `weekly-meeting-memo` and its `reviewer` message folder (md5 `bbb2d83520f3a7537f447c0f817ff3e2`). |


## Manager rulings after s2 (`manager-decision-s2-and-h3.md`)
| File | What it is |
|---|---|
| `manager-decision-s2-and-h3.md` | Ruling 1: s2 is INVALID (H8: a `ModelThrottleError` in an org run stalled a task; the "injected rework stalling" item of the not-invalid list covers stalls caused by the product or the assistant); s2 stays in the evidence, observations before the failure stand; replacement `s2r` approved; harness model check before turn 1 and before the injection for s2r and s3 (record in `<stream>/model-checks.txt`); product findings F-E4-infra-1 and F-E4-harness-1 for STUDY.md. Ruling 2: s1r is VALID, not H3 (a memory index absent where the probe found it present does not meet 4.5's invalidity test; memory presence is a covariate recorded per stream). Frozen; never edited. |

## Stream s2r (replacement for the INVALID s2; product `main` = `7d86c31`; sandbox `/tmp/hirearchy-e4-s2r-1792702135`; org kiro home `~/Library/Application Support/hirearchy/kiro-home/hirearchy-e4-s2r-1792702-b0c5db682e7e6ab7/`; status: complete, 12 of 12 user turns (also the second consecutive L-WAIT use), 14 org runs outside the injection window + 5 inside, no model-service error; run 2026-10-22 20:48-21:33Z; facts only, not scored)
| File | What it is |
|---|---|
| `s2r/run-log.md` | Facts: gates, setup, model checks, turn table, org runs, injection, contract/playbook facts, ambient context, cleanup and safety. |
| `s2r/model-checks.txt` | The harness model check of ruling 1: each org-agent model (claude-sonnet-4.6, claude-haiku-4.5) with the prep profile and "Reply with OK.", before turn 1 and before the injection; every attempt with time, exit code and reply (all four succeeded on attempt 1). |
| `s2r/setup.txt`, `s2r/skill-check.txt`, `s2r/ambient-context.txt`, `s2r/models-list.txt`, `s2r/safety-before.txt`, `s2r/safety-after.txt`, `s2r/epoch.txt`, `s2r/sandbox-path.txt`, `s2r/stream-start-utc.txt` | Per-stream setup records (4.1 checks before and after, profile diff against s1r, md5 gates, skill/ambient checks, safety snapshots). |
| `s2r/profiles/` | The assistant profile (copied, verified, deleted: `deletions.txt`) and the copy of the org's scheduler profile from the org kiro home (`org-kiro-home--*`; not deleted, amendment A3.2). |
| `s2r/lena-lines.txt`, `s2r/prompts/`, `s2r/turn-01..12.txt` (+ `.raw`, `.stderr`, `.prompt`), `s2r/turn-times.txt`, `s2r/session-turn-times-utc.txt` | The conversation (12 user turns): Lena's line with the rule ids and deciding facts. |
| `s2r/assistant-tool-calls.txt`, `s2r/assistant-session-messages.jsonl`, `s2r/assistant-session.json` | Assistant tool-call transcript (43 calls) and the raw session store. |
| `s2r/PLAN-FOR-YOU-product-proposal1..2.txt`, `s2r/blueprint-proposal1..2.yaml`, `s2r/blueprint.yaml`, `s2r/apply_org-result.txt` | The two successful `propose_org` results/blueprints; the applied blueprint and the `apply_org` reply. |
| `s2r/injection/` | `injection-log.txt` (script md5, every call verbatim), `request-args.json`, `text-identity.txt`, `window-runs.txt`, `FREEZE.txt` (script md5 `c80e25d65fe58cdb97d7faa758d59484`), `memo1-identification.txt`, `window.txt`, script stdout/stderr. |
| `s2r/msgs/`, `s2r/run-logs/`, `s2r/events/`, `s2r/org-files/`, `s2r/service/`, `s2r/playbook/`, `s2r/scheduler.log`, `s2r/org-git-log.txt`, `s2r/observe-traces.txt`, `s2r/final-services-progress-status-health.txt` | The org (copied by `harness/copy_org_evidence.sh`); `service/history--*` and `playbook/history--*`, `current-*` are from the org's `history/` dirs. |
| `s2r/org-kiro-sessions/<hash>/<session id>/`, `s2r/run-session-map.txt` | Amendment A3.2: the 19 org-run kiro sessions and the run-to-session match (19 of 19). |
| `s2r/revise-playbook-attempts.txt`, `s2r/contract-loop.txt`, `s2r/client-questions.txt`, `s2r/deliverables-log.txt`, `s2r/shell-writes.txt`, `s2r/lead-prompt-sizes.txt`, `s2r/reflect-sections/`, `s2r/regression-list/` | Mechanical extracts (protocol 7.2), from `harness/extract_mechanical_s2.py`. |
| `s2r/memos/` (+ `versions/`), `s2r/run-counts-by-turn.txt`, `s2r/run-counts.txt`, `s2r/cost.txt` | The final memo 1 and its four org-git versions; run counts per turn and final; assistant and org-run credits. |


## Stream s3 (product `main` = `7d86c31`; sandbox `/tmp/hirearchy-e4-s3-1792705005`; org kiro home `~/Library/Application Support/hirearchy/kiro-home/hirearchy-e4-s3-17927050-8f0c59d32ad49337/`; status: complete, 12 of 12 user turns, all three memos requested, delivered and judged; 41 org runs outside the injection window + 5 inside (46 in total, one interrupted by the assistant's `stop`); no model-service error; run 2026-10-22 21:36-22:34Z; facts only, not scored)
| File | What it is |
|---|---|
| `s3/run-log.md` | Facts: gates, setup, model checks, turn table, org runs, injection, contract/playbook facts, ambient context (memories block present: covariate), cleanup and safety. |
| `s3/model-checks.txt` | The harness model check of ruling 1: claude-sonnet-4.6 and claude-haiku-4.5 with the prep profile and "Reply with OK.", before turn 1 and before the injection; all four succeeded on attempt 1. |
| `s3/setup.txt`, `s3/skill-check.txt`, `s3/ambient-context.txt`, `s3/models-list.txt`, `s3/safety-before.txt`, `s3/safety-after.txt`, `s3/epoch.txt`, `s3/sandbox-path.txt`, `s3/stream-start-utc.txt` | Per-stream setup records (4.1 checks before and after, profile diff against s1r, md5 gates, skill/ambient checks, safety snapshots). |
| `s3/profiles/` | The assistant profile and the preflight/prep profile (copied, verified, deleted: `deletions.txt`) and the copies of the org's two scheduler profiles from the org kiro home (`org-kiro-home--*`; not deleted, amendment A3.2). |
| `s3/lena-lines.txt`, `s3/prompts/`, `s3/turn-01..12.txt` (+ `.raw`, `.stderr`, `.prompt`), `s3/turn-times.txt`, `s3/session-turn-times-utc.txt` | The conversation (12 user turns): Lena's line with the rule ids and deciding facts. |
| `s3/assistant-tool-calls.txt`, `s3/assistant-session-messages.jsonl`, `s3/assistant-session.json` | Assistant tool-call transcript (88 calls) and the raw session store. |
| `s3/PLAN-FOR-YOU-product-proposal1..2.txt`, `s3/blueprint-proposal1..2.yaml`, `s3/blueprint.yaml`, `s3/apply_org-result.txt` | The two `propose_org` results/blueprints; the applied blueprint and the `apply_org` reply (from `harness/extract_proposals.py`). |
| `s3/injection/` | `injection-log.txt` (script md5, every call verbatim), `request-args.json`, `text-identity.txt`, `window-runs.txt`, `FREEZE.txt` (script md5 `c80e25d65fe58cdb97d7faa758d59484`), `memo1-identification.txt` (the memo-1 task is the assistant's human rework 4510), `window.txt`, script stdout/stderr. |
| `s3/msgs/`, `s3/run-logs/`, `s3/events/`, `s3/org-files/`, `s3/service/`, `s3/playbook/`, `s3/scheduler.log`, `s3/org-git-log.txt`, `s3/observe-traces.txt`, `s3/final-services-progress-status-health.txt` | The org (copied by `harness/copy_org_evidence.sh`); `service/history--*` and `playbook/history--*`, `current-*` are from the org's `history/` dirs. |
| `s3/org-kiro-sessions/<hash>/<session id>/`, `s3/run-session-map.txt` | Amendment A3.2: the 45 org-run kiro sessions and the run-to-session match (45 of 46 runs; the unmatched run was interrupted by the assistant's `stop`). |
| `s3/revise-playbook-attempts.txt`, `s3/contract-loop.txt`, `s3/client-questions.txt`, `s3/deliverables-log.txt`, `s3/shell-writes.txt`, `s3/lead-prompt-sizes.txt`, `s3/reflect-sections/`, `s3/regression-list/` | Mechanical extracts (protocol 7.2), from `harness/extract_mechanical_s3.py`. |
| `s3/memos/` (+ `versions/`), `s3/run-counts-by-turn.txt`, `s3/run-counts.txt`, `s3/cost.txt` | The three final memos and their org-git versions; run counts per turn and final; assistant and org-run credits. |
| `harness/extract_mechanical_s3.py`, `harness/extract_proposals.py` | Added by the s3 step: `extract_mechanical.py` with the reviewer message folder `*reviewer*` (md5 `b88031528b72cc6915228ad9302ce309`), and the proposal/blueprint extractor (md5 `41f317d85f10cd0da284dc10398dd138`). |
| `harness/model_check.sh` | Model-availability check script of ruling 1 (md5 `07ffec85c836e77735fd43050de25858`), used by the s3 step; its output path is s3's. |
| `safety-after.txt` (study level) | Written by the s3 step after its cleanup, with notes. |
