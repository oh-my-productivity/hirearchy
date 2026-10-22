# H8 candidate: an org run failed with a model-service error and the injected task stalled (facts only)

Found 2026-10-22T20:41Z, after the injection script returned and before Lena's turn 6 (not sent). Protocol section 11 H8: "Org runs failed for engine or infrastructure reasons (authentication, model-service errors, ...), and those failures changed the course: a task failed, blocked or stalled because of them."

## The failed run
- Run `lead/reviewer@20261022T202454859379` (claude-sonnet-4.6), started 2026-10-22T20:24:54Z, `# exit 1 after 127s`. It is the only org run of s2 without `[run finished] success (end_turn)` (18 of 19 finished; `run-logs/lead-reviewer/20261022T202454859379.log`).
- Run log (after `# kiro: run started (engine v3)`): `org_read` and a notes read succeeded; then `[tool failed] Tool Call {"tool_id":"hirearchy::write","arguments":{"path":"lead/reviewer/work/review-2026-10-05-recheck3.md", ...` followed by:

    [run error] prompt: Claude Sonnet 4.6 is experiencing high traffic. Try again, or select another model. (Request ID: 0edca39b-cfdd-4141-84f5-b7d31afe92ea) (code -32000): {"errorType":"ModelThrottleError","retryErrorType":"THROTTLING","requestId":"0edca39b-cfdd-4141-84f5-b7d31afe92ea"}

- No `# kiro:` launcher failure line; the error is the model service's (`ModelThrottleError`, `THROTTLING`).
- The run belonged to the injected task: its message was `20261022T202453586412-lead-2200` (trace `20261022T195928156602-root-2ab8`, `revises 20261022T201623767323-lead-3386`, budget 1), delegated by the lead while working on injected task `20261022T202052658793-root-7da0`.

## What followed (scheduler.log of the injection window, pid 41796)
```
# --- scheduler started 2026-10-22 20:20:52Z: /Volumes/workspace/hirearchy/.venv/bin/hirearchy --root /private/tmp/hirearchy-e4-s2-1792698851/org run --until-done
org: /private/tmp/hirearchy-e4-s2-1792698851/org
lead: started run (1 message(s))
lead/writer: started run (1 message(s))
lead: run finished in 123s
lead: started run (1 message(s))
lead/writer: run finished in 83s
lead/reviewer: started run (1 message(s))
lead: run finished in 85s
lead/reviewer: run failed (1 in a row), log: /private/tmp/hirearchy-e4-s2-1792698851/org/lead/reviewer/runs/20261022T202454859379.log
lead/reviewer: out of budget, paused, parent notified
lead: started run (1 message(s))
lead: run finished in 117s
waiting on you: "Rework memo 2026-10-05: unclear due dates" needs budget (lead/reviewer out of runs). Exiting in 300s unless something changes
scheduler exiting: waiting on you: "Rework memo 2026-10-05: unclear due dates" needs budget (lead/reviewer out of runs)
```
- `scheduler.exit`: `waiting on you: "Rework memo 2026-10-05: unclear due dates" needs budget (lead/reviewer out of runs)`
- The failed run used the reviewer's only run (budget 1): "lead/reviewer: out of budget, paused, parent notified". The lead then wrote to root (message `20261022T202827043470-lead-d0c7`, unread in `inbox/`): "Budget needed: 1 run to process reviewer result ... granting lead/reviewer budget=1 now"; the reviewer's inbox still holds the unprocessed re-check message.
- The injection script's last `progress` / `status` (window end 2026-10-22T20:40:52Z): injected task `20261022T202052658793-root-7da0` "waiting on lead/reviewer (paused: budget). runs 5 of 6"; `scheduler: stopped (waiting on you: ... needs budget (lead/reviewer out of runs))`; root status `reviewer [Independent Reviewer] paused(budget) budget=0 open=1 unread=1`; the case total reads "19 runs used of 36 handed down (contract: 15 per request). This case now exceeds the per-request budget of 15: tell the user."
- So the injected task did not reach done / failed / blocked: it stalled at the reviewer's re-check, after a run that failed on a model-service error.

## Other facts relevant to H8 (all from this stream)
- Other org runs: 18 of 18 finished `success (end_turn)`, `# exit 0`; no readiness refusal (`scheduler.log`, 3 scheduler starts, all `run` `cli.command` events ok).
- Lena's chain (memo 1: `20261022T195928156602-root-2ab8` and its human rework `20261022T201253989822-root-2139`) had finished before the failure; memo 1 was copied to `deliverables/memo-2026-10-05.md` at 20:19:27Z (turn 5). The failed run is in the injection window; it is not counted toward the 45-run cap.
- The injection script (frozen, md5 `c80e25d65fe58cdb97d7faa758d59484`) kept calling `progress(task_id, wait_seconds=300)` without waiting once the reply was "Not waiting: nothing can progress without you" (its loop only ends on done/failed/blocked + scheduler stopped, or 20 minutes): 36513 read-only `progress` calls between 20:33:27Z and 20:40:52Z (events file `mcp-41795-1792700452653.jsonl`, 36,516 `tool.call` events, all by actor root). They changed nothing in the org. The script exited 0 at the 20-minute cap ("window cap: 20 minutes passed"); its calls are otherwise the five of protocol 5.3.

## Facilitator's reading and handling (no scoring)
- The failure is a model-service error in an org run, and a task (the injected rework) stalled because of it: that matches H8's wording. Whether a stall of the facilitator's injected task counts as "changed the course" (section 11 lists "the injected rework blocking or stalling" as not invalid when it is product behaviour) is for the manager.
- Handling (section 11): the stream is stopped here (after the injection, before Lena's turn 6); evidence copied; assistant profile copied and deleted; escalated with `send_message` warning. No replacement stream was started. The sandbox, the assistant session and the org are left in place.
