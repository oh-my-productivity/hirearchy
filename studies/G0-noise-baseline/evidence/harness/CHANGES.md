# G0 harness: every file against E7's harness (protocol 10)

Built by the pre-registration step (step 1 of 11, workflow `wf_c415acfac4f09f84`) from E7's harness (`studies/E7-org-growth-0a4-recheck/evidence/harness/`, 17-line `MD5SUMS` md5 `d1f24687c9cd1587466d24db42ce59d0`) and E7's per-stream copies, read-only. No E7 file was changed. `MD5SUMS` freezes every file listed here, the tests and the self-check's expected values.

## Files

| File | md5 | From E7 | Change |
|---|---|---|---|
| `inject_root_rework.py` | `1c4e7824e448a3a34e24a7b759a59fcd` | `harness/inject_root_rework.py` (`1c4e7824e448a3a34e24a7b759a59fcd`) | byte-identical (protocol 2.2) |
| `test_poll_loop.py` | `0b269d00bcd8ce4e7c4498e270960c30` | `harness/test_poll_loop.py` (`0b269d00bcd8ce4e7c4498e270960c30`) | byte-identical |
| `workspace-cli.json` | `05d30ccbfd35530747c8a542eb67985c` | `harness/workspace-cli.json` (`05d30ccbfd35530747c8a542eb67985c`) | byte-identical (md5 05d30ccb...) |
| `ambient_context.py` | `c40d05929771b0fcbc7f0491df79d195` | `harness/ambient_context.py` (`c40d05929771b0fcbc7f0491df79d195`) | byte-identical |
| `extract_tool_calls.py` | `da57d91e9beea0f1947ffb126ea92c88` | `harness/extract_tool_calls.py` (`da57d91e9beea0f1947ffb126ea92c88`) | byte-identical |
| `extract_proposals.py` | `41f317d85f10cd0da284dc10398dd138` | `harness/extract_proposals.py` (`41f317d85f10cd0da284dc10398dd138`) | byte-identical |
| `profile-template.json` | `77b010c9a82cbbd6f6cec7d89630bcc7` | `harness/profile-template.json` (`5e5bf3caebb5d94871cb7601340af0e9`) | `name`, `description`, `ORG_ROOT` only (protocol 6) |
| `org_state.py` | `b045f0fcad4cb15032c84a61b92d2d4c` | `harness/org_state.py` (`26dc50455fab906f9fe51be7af75ec82`) | docstring only (it matches the sandbox by `S.name`) |
| `run_turn.sh` | `34a9d042dfc27b55bf46033c00c385e3` | `harness/run_turn.sh` (`8732cf2818e3f2f73163d356d7c610a1`) | takes a label; the chat runs under the arm's kiro home (`env -u KIRO_HOME` for M1, `env KIRO_HOME=<M0H>/.kiro` for M0, read from `m0-home-path.txt`, refused without it); the snapshots get the M0 home; **the boundary line (`...; sleep 20`) and the `turn-times.txt` line are E7's byte for byte** |
| `ambient_snapshot.sh` | `54c9e87b891fb5f378db19acaecced2c` | `harness/ambient_snapshot.sh` (`fc35ed74c92424cf8f41c7eeac83f050`) | an optional second argument appends the dedicated kiro home's skills (find -P, -L) and memories listings with their md5s; without it the output is E7's |
| `model_check.sh` | `c13ce0f05067eb6d5feb43a698d3831f` | `harness/model_check.sh` (`0561300ab330445a09c80ebbd4fc30e5`) | labels, G0 paths and profile name; the profile is also looked for in the M0 home |
| `safety-snapshot.sh` | `a87d3756e6432d0539188a3920299a52` | `harness/safety-snapshot.sh` (`36ac1f04c1f852f837e29ca52d732df2`) | G0's protocol path and freeze diff (`3c841bb9`); lists `hirearchy-study-g0-*` profiles and `/tmp/hirearchy-g0-*` names |
| `copy_org_evidence.sh` | `fb349f415af275e6f5f47b414f7a8cc5` | `harness/copy_org_evidence.sh` (`c3d359327648749509caccef9683a898`) | labels and G0 paths; `memos/versions/` is left to `extract_mechanical.py` (protocol 15 item 14) |
| `after_turn.sh` | `1c80dd4ef84aa9392ff227cd2bfba2b8` | `s1/prompts/after_turn.sh` (`03aadf44a56326d05b1d7d2f7c4368ee`) | E7's per-stream facilitator helper made one frozen script for any label; the session is found in the arm's kiro home; `quality_snapshot.sh` runs last (protocol 10) |
| `extract_mechanical.py` | `a2d7130618140dbc67ba17190947679e` | `harness/extract_mechanical.py` (`9b1b8e25139dda21fc63ffd3f74df702`) | one script for every stream (E7 needed `_s2`/`_s3` and per-stream copies): it finds the service folder, the owner and the final-check seat itself; with `-` instead of a sandbox it reads the stream dir only; same extract files and formats as E7's (byte-identical on E7's s1-s3, `harness-selfcheck/e7-s*/extract-diff.txt`); it still imports the product's client-question parser read-only, as E7's did (`--product-src`), with bytecode writing off |
| `scheduler_survival.py` | `d25f514da4ebd6e361230df61037070c` | `s1/harness/scheduler_survival.py` (`6a7758112ee8f52f349a62d016ac40c8`) | generalized from E7 s1's per-stream extract: D-SURVIVE, D-SIGNAL and M-C-8; the starter rule of E7 STUDY Interpretation 18 with correction 9's header fixed; JSON output with `--out` |
| `injection_files.py` | `d0726c316b3325a9d79549fdcc42d175` | `s2/harness/injection_files.py` (`dfdbcbb49581cb63808b477f8058dafe`) | generalized from E7 s2's per-stream extract; writes `text-identity.txt` and `window-runs.txt` in the format of E7's committed files |
| `rederive_quality.py` | `567d9ce98f538d81d76d94343e778f23` | new | the independent re-derivation of `quality --json` (design 20.2, 21) by the design's rules (protocol 3.5); `--compare` lists mismatches and F-G0-1 lines; `--selfcheck` |
| `score_memos.py` | `428c324dc3b764245774127f52c150e1` | new | answer-key score of every version and final memo (D15-D18; frozen keyword sets) and the reviewer's verdict per version (protocol 12 A2, A3's reading of D21); `--selfcheck` |
| `ambiguity_recall.py` | `92b67f74a38c04895402803e9388e718` | new | reviewer ambiguity recall (E5's D21 as protocol 12 A3 reads it, the literal timing beside it); `--pool`; `--selfcheck` |
| `prompt_sizes.py` | `1faad9255523d37a86795838a006e6dc` | new | owner prompt bytes per run and Reflect words (design 20.4 A); `--selfcheck` |
| `playbook_attempts.py` | `6aa21eb5c9ffb11bb0aed9cd420fcd26` | new | `revise_playbook` attempts, refusals and admissions (design 20.4 A); `--selfcheck` |
| `assistant_facts.py` | `61f51c012dfff9305836990bef47cf4d` | new | design 20.4 B's mechanical facts per stream; `--selfcheck` runs the whole extract chain on E7 |
| `aggregate.py` | `aa1526c3589472d232a7335bbfe009f5` | new | `baseline.md` (design 20.5) |
| `judged-template.json` | `e2b6ec1122b9a708d3c1ac81a41bb4d3` | new | the judged measures' keys for `<label>/measures/judged.json` |
| `skill_check.py` | `df7bd77dd2b7fc9eb6681e677b6c7e7c` | new | the skill's first `disclose_context`, its md5 and the stratum (E7 4.4.1); `--selfcheck` |
| `skill_check.sh` | `e06b2e3db851819e88a0e0a098e52993` | new | design 20.1's skill rule in both arms -> `skill-check.txt` / `.json` |
| `quality_snapshot.sh` | `0b56c112c83719a98f5b1eff1d815cfe` | new | `quality --json` after a turn or at the end, skipped before `ORG.md` exists, with its `cli.command` event file recorded (protocol 10) |
| `setup_stream.sh` | `f919910cc1e6fd6359cf69687c161633` | new | protocol 6 item 1 for G0: the gates, then the sandbox, the M0 home, the profile, setup records; `--dry-run` |
| `run_arm.sh` | `537bffe5076c2ab064e468b7d2114881` | new | `run_arm.sh <arm> <k>`: the arm's next labels and their command sequence; `--setup` sets up the next stream |
| `finish_stream.sh` | `1b89caf0e942b2033032d78decda786e` | new | protocol 6 item 5 for G0: stop, copy, `check`, `quality --json` end, every extract and measure, the profile cleanup, safety after |
| `prepare_m0_home.sh` | `68851319b65a472db1dabc66e10c72e4` | new | the dedicated M0 kiro home (protocol 6); labels `m0-s<n>[r..]` and `preflight`; prefix guard; `--dry-run` |
| `selfcheck.sh` | `4b1a1755f2904310ddd11dfb5cd0d090` | new | the harness self-check on E7's raw evidence (protocol 10) |
| `tests/` | see `MD5SUMS` | new | unit and E7 integration tests of every script (`selfcheck.sh` runs them) |
| `selfcheck/e7-expected-*.json` | see `MD5SUMS` | new | the self-check's expected values, transcribed (protocol 10, 15 item 18); amended entries keep their published value and name `manager-decision-selfcheck.md` |

## Decisions recorded while building

1. **`run_turn.sh`'s variables.** `EV` stays the stream folder, as in E7, so the boundary line is E7's byte for byte; the evidence root is `EVROOT`.
2. **`memos/versions/` has one writer**, `extract_mechanical.py`, with E7's rule (protocol 15 item 14).
3. **`finish_stream.sh`** records every step's exit code in `finish-steps.txt` (failures also in `finish-failures.txt`), copies the sandbox's `injection/` into the stream folder before the extracts, writes `safety-diff.txt`, and counts a profile that changed during the stream as a failure (its creation copy is kept).
4. **`setup_stream.sh`** checks, before it creates anything: the protocol and `MD5SUMS` gates, HEAD and the freeze diff, claude-sonnet-5.5 listed, and the skill md5 rule; it refuses a label already set up or an existing M1 profile file; `--dry-run` creates nothing.
5. **`skill_check.sh`** reads the global SKILL.md with `md5 -q` only.
6. **The checked version and the reviewed version** are read at the first org-git commit that holds the result's or the review task's sent copy (protocol 3.5, 12 A3); on E7's evidence the checked-version rule changes no re-derived value, and the review rule maps only E7 s2's `...-lead-1414` differently from D21's literal timing (to `2cd5611`).
7. **Not verifiable before the preflight** (this step creates no kiro home and runs no chat): that `kiro-cli chat` under `KIRO_HOME=<M0H>/.kiro` authenticates, finds the profile in `<M0H>/.kiro/agents/`, keeps its session in `<M0H>/.kiro/sessions/` and has no memories index. The preflight checks it (protocol 11).

## Diffs against E7 (`diff -u <E7 file> <G0 file>`; byte-identical files have none)

### `profile-template.json` (from `harness/profile-template.json`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/profile-template.json	2026-10-25 06:14:43
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/profile-template.json	2026-10-26 03:37:03
@@ -1,11 +1,11 @@
 {
-  "name": "hirearchy-study-e7-s<N>-assistant",
-  "description": "internal: hirearchy usability study E7 stream s<N> assistant; deleted after the stream",
+  "name": "hirearchy-study-g0-<LABEL>-assistant",
+  "description": "internal: hirearchy usability study G0 stream <LABEL> assistant; deleted after the stream",
   "mcpServers": {
     "hirearchy": {
       "command": "uv",
       "args": ["--directory", "/Volumes/workspace/hirearchy", "run", "hirearchy", "mcp"],
-      "env": { "ORG_ROOT": "/tmp/hirearchy-e7-s<N>-<epoch>/org" }
+      "env": { "ORG_ROOT": "/tmp/hirearchy-g0-<LABEL>-<epoch>/org" }
     }
   },
   "tools": ["*"],
```

### `org_state.py` (from `harness/org_state.py`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/org_state.py	2026-10-25 06:14:43
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/org_state.py	2026-10-26 03:37:03
@@ -1,5 +1,5 @@
 #!/usr/bin/env python3
-"""E7 read-only org state snapshot (file listings only; no MCP/CLI call against the org).
+"""G0 read-only org state snapshot (file listings only; no MCP/CLI call against the org).
 Usage: org_state.py <S> <label>   -> prints a block for run-counts-by-turn.txt
 Lists every run log (agent, model, start from the file name = UTC, duration from the exit line, flagged if inside the
 injection window recorded in <S>/injection/window.txt as 'start_utc end_utc'), open items (message files in inboxes and
```

### `run_turn.sh` (from `harness/run_turn.sh`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/run_turn.sh	2026-10-25 06:14:43
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/run_turn.sh	2026-10-26 03:40:42
@@ -1,16 +1,36 @@
 #!/bin/zsh
-# E7 per-turn driver. Usage: run_turn.sh <S> <stream N> <turn number> <prompt file>
+# G0 per-turn driver (E7's). Usage: run_turn.sh <S> <label> <turn number> <prompt file>      (label = m0-s1, m1-s2, m0-s1r, ...)
 # Sends the prompt file's text verbatim as Lena's line. Turn 1 = new session; turns >= 2 add --resume. cwd = S.
 # Every call carries --effort high (protocol 4.2, 4.3). The exact argv is written to turn-NN.cmd.txt (model_check.sh reads it).
-# Writes into <evidence>/s<N>/: turn-NN.prompt.txt (copy), turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI
+# Writes into <evidence>/<label>/: turn-NN.prompt.txt (copy), turn-NN.cmd.txt (argv), turn-NN.txt (header + prompt + stdout, ANSI
 # stripped), turn-NN.raw.txt (raw stdout), turn-NN.stderr.txt, and appends a line to turn-times.txt. No MCP/CLI call against the org.
 # E7 (protocol 4.2.1, E7 item 4, D-E6-7; C1's D-HARN form): the kiro-cli chat command is never the last command of its tool call: the
 # exit code and the end times are taken, then `; sleep 20` follows in the same command list, so the call stays open 20 s after the return.
 # E7 (protocol 4.5.1): ambient_snapshot.sh is taken right before the chat (ambient/turn-NN-before.txt) and after the sleep
 # (ambient/turn-NN-after.txt). turn-times.txt keeps E6's format and appends the time the sleep ended.
-S="$1"; N="$2"; T="$3"; PF="$4"
-EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s$N
-H=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness
+# G0 (design 20.1, arms): the chat runs under the arm's kiro home. Arm M1 (the owner's ambient memories): `env -u KIRO_HOME`, so an inherited
+# KIRO_HOME cannot redirect it, and kiro uses the owner's default home. Arm M0 (no memories index): `env KIRO_HOME=<M0H>/.kiro`, <M0H> read from
+# <evidence>/<label>/m0-home-path.txt (the run is refused if that file is missing); HOME is unchanged and authentication comes from the
+# inherited environment. The env prefix is the first part of the CMD array, so turn-NN.cmd.txt shows it. For arm M0 the ambient snapshots
+# also list the dedicated home's skills and memories (ambient_snapshot.sh's second argument).
+# The variable EV below is the STREAM's evidence folder, as in E7 (EVROOT is the study's evidence root).
+S="$1"; LABEL="$2"; T="$3"; PF="$4"
+REPO=/Volumes/workspace/hirearchy
+ST=$REPO/studies/G0-noise-baseline
+EVROOT=$ST/evidence
+H=$EVROOT/harness
+EV=$EVROOT/$LABEL
+[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && -n "$S" && "$T" =~ '^[1-9][0-9]*$' && -f "$PF" ]] || { echo "usage: run_turn.sh <S> <label> <turn> <prompt file>" >&2; exit 2; }
+ARM=${LABEL%%-*}
+KIRO_ENV=(env -u KIRO_HOME)
+KH=""
+if [[ "$ARM" == m0 ]]; then
+  [[ -s "$EV/m0-home-path.txt" ]] || { echo "REFUSED: $EV/m0-home-path.txt is missing: arm m0 needs its dedicated kiro home (prepare_m0_home.sh)" >&2; exit 91; }
+  M0H="$(cat "$EV/m0-home-path.txt")"
+  [[ -d "$M0H/.kiro" ]] || { echo "REFUSED: $M0H/.kiro does not exist" >&2; exit 91; }
+  KH="$M0H/.kiro"
+  KIRO_ENV=(env KIRO_HOME="$KH")
+fi
 NN=$(printf '%02d' "$T")
 mkdir -p "$EV"
 cp "$PF" "$EV/turn-$NN.prompt.txt"
@@ -18,14 +38,14 @@
 RESUME=""
 [[ "$T" -ge 2 ]] && RESUME="--resume"
 cd "$S" || exit 90
-CMD=(kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-e7-s$N-assistant "$PROMPT")
+CMD=(${KIRO_ENV[@]} kiro-cli chat --v3 --no-interactive --trust-all-tools $RESUME --effort high --agent hirearchy-study-g0-$LABEL-assistant "$PROMPT")
 print -r -- "${(q-)CMD[@]}" > "$EV/turn-$NN.cmd.txt"
 mkdir -p "$EV/ambient"
-zsh "$H/ambient_snapshot.sh" "s$N before turn $T" > "$EV/ambient/turn-$NN-before.txt" 2>&1
+zsh "$H/ambient_snapshot.sh" "$LABEL before turn $T" $KH > "$EV/ambient/turn-$NN-before.txt" 2>&1
 start=$(date +%s); startl=$(date +%H:%M:%S); startu=$(date -u +%FT%TZ)
 "${CMD[@]}" > "$EV/turn-$NN.raw.txt" 2> "$EV/turn-$NN.stderr.txt"; rc=$?; end=$(date +%s); endl=$(date +%H:%M:%S); endu=$(date -u +%FT%TZ); sleep 20
 slept=$(date -u +%FT%TZ)
-zsh "$H/ambient_snapshot.sh" "s$N after turn $T" > "$EV/ambient/turn-$NN-after.txt" 2>&1
+zsh "$H/ambient_snapshot.sh" "$LABEL after turn $T" $KH > "$EV/ambient/turn-$NN-after.txt" 2>&1
 {
   echo "######## TURN $T  start $startl  end $endl  elapsed $((end-start))s  (local, $(date +%F); UTC wall-clock start $startu end $endu; exit code $rc)"
   echo "######## LENA (prompt sent verbatim):"
```

### `ambient_snapshot.sh` (from `harness/ambient_snapshot.sh`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/ambient_snapshot.sh	2026-10-25 06:14:12
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/ambient_snapshot.sh	2026-10-26 03:38:03
@@ -1,12 +1,17 @@
 #!/bin/zsh
-# E7 ambient snapshot (read-only). Usage: ambient_snapshot.sh <label>   -> prints to stdout
-# Protocol 4.5.1 (E7 item 4, D-E6-7): before and after every turn, the user's global skills and memories database, metadata only.
+# G0 ambient snapshot (read-only). Usage: ambient_snapshot.sh <label> [<kiro home>]   -> prints to stdout
+# E7's snapshot (protocol 4.5.1; E7 item 4, D-E6-7), unchanged for the owner's ~/.kiro: before and after every turn, the user's global skills and
+# memories database, metadata only.
 # 1. every entry under ~/.kiro/skills, links not followed (find -P): mtime (epoch and UTC), type, size, path, and a symlink's target;
 # 2. every entry reached through the links (find -L): mtime, type, size and path (the skill catalog's content, metadata only);
 # 3. ~/.kiro/memories: each entry's mtime, type, size and name, and the md5 of memories.db.
 # It never opens, parses, queries or prints the database's contents (md5 -q digests its bytes and prints the digest only), writes nothing
 # but its stdout, and changes nothing it lists. Each listing is followed by its own md5, so two snapshots compare line by line.
+# G0 (arm M0): with a second argument <kiro home> (the dedicated home's .kiro directory), the same three sections are appended for
+# <kiro home>/skills (find -P and find -L) and <kiro home>/memories (expected absent: the listing is the single line "(absent)"), each with
+# its listing md5 (lines "home skills listing md5", "home skills-through-links listing md5", "home memories listing md5").
 label="${1:-snapshot}"
+KH="$2"
 SK=$HOME/.kiro/skills
 MEM=$HOME/.kiro/memories
 FMT='%m|%Sm|%HT|%z|%N|%Y'
@@ -25,3 +30,27 @@
 print -r -- "$M"
 echo "memories listing md5: $(print -r -- "$M" | md5 -q)"
 echo "memories.db md5 (a digest only; its contents are never read): $(md5 -q "$MEM/memories.db" 2>&1)"
+if [[ -n "$KH" ]]; then
+  HSK=$KH/skills
+  HMEM=$KH/memories
+  if [[ -d "$HSK" ]]; then
+    HP=$(TZ=UTC find -P "$HSK" -exec stat -t '%Y-%m-%dT%H:%M:%SZ' -f "$FMT" {} + 2>&1 | sort -t'|' -k5,5)
+    HL=$(TZ=UTC find -L "$HSK" -exec stat -L -t '%Y-%m-%dT%H:%M:%SZ' -f '%m|%Sm|%HT|%z|%N' {} + 2>&1 | sort -t'|' -k5,5)
+  else
+    HP="(absent)"; HL="(absent)"
+  fi
+  if [[ -d "$HMEM" ]]; then
+    HM=$(TZ=UTC find -P "$HMEM" -maxdepth 1 -exec stat -t '%Y-%m-%dT%H:%M:%SZ' -f "$FMT" {} + 2>&1 | sort -t'|' -k5,5)
+  else
+    HM="(absent)"
+  fi
+  echo "== $HSK, links not followed (find -P): mtime_epoch|mtime_utc|type|size|path|link target ($(print -r -- "$HP" | wc -l | tr -d ' ') entries)"
+  print -r -- "$HP"
+  echo "home skills listing md5: $(print -r -- "$HP" | md5 -q)"
+  echo "== $HSK through the links (find -L): mtime_epoch|mtime_utc|type|size|path ($(print -r -- "$HL" | wc -l | tr -d ' ') entries)"
+  print -r -- "$HL"
+  echo "home skills-through-links listing md5: $(print -r -- "$HL" | md5 -q)"
+  echo "== $HMEM, metadata only (expected absent): mtime_epoch|mtime_utc|type|size|path|link target"
+  print -r -- "$HM"
+  echo "home memories listing md5: $(print -r -- "$HM" | md5 -q)"
+fi
```

### `model_check.sh` (from `harness/model_check.sh`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/model_check.sh	2026-10-25 06:14:43
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/model_check.sh	2026-10-26 03:39:42
@@ -1,24 +1,25 @@
 #!/bin/zsh
-# E7 model and effort check (protocol 4.3, 11 H4). Read-only: it lists, reads and greps; it writes only model-checks.txt.
+# G0 model and effort check (E7's; protocol 4.3, 11 H4). Read-only: it lists, reads and greps; it writes only model-checks.txt.
 # The set is one seat value: claude-sonnet-5.5 at effort high, for the assistant and for every org agent (D-E4-8, D-E4-9).
 # Usage:
-#   model_check.sh listed    <N>       "kiro-cli chat --list-models" lists claude-sonnet-5.5 (stream start; there is no substitution)
-#   model_check.sh org       <N> <S>   every org run log under S/org has one "# cmd:" line with exactly one "--model claude-sonnet-5.5"
+#   model_check.sh listed    <label>       "kiro-cli chat --list-models" lists claude-sonnet-5.5 (stream start; there is no substitution)
+#   model_check.sh org       <label> <S>   every org run log under S/org has one "# cmd:" line with exactly one "--model claude-sonnet-5.5"
 #                                      and exactly one "--effort high"
-#   model_check.sh assistant <N> <S>   the stream's profile has "model": "claude-sonnet-5.5"; every turn-NN.cmd.txt has "--effort high"
-#                                      once, the stream's --agent, and no --model other than claude-sonnet-5.5; the session copy
-#                                      s<N>/assistant-session.json has modelId claude-sonnet-5.5 and effortLevel high (or none recorded);
-#                                      every reasoningModelId in s<N>/assistant-session-messages.jsonl is [qdev::]claude-sonnet-5.5
-#   model_check.sh all       <N> <S>   org, then assistant
-# <N> is the stream label (1, 2, 3, 1r, ...), or "preflight" for the preflight's scratch org (protocol 4.14; output in
-# evidence/preflight/). Appends a block to evidence/s<N>/model-checks.txt and prints its RESULT line.
+#   model_check.sh assistant <label> <S>   the stream's profile has "model": "claude-sonnet-5.5"; every turn-NN.cmd.txt has "--effort high"
+#                                      once, the stream's --agent (the arm's `env ...` prefix is skipped), and no --model other than claude-sonnet-5.5; the session copy
+#                                      <label>/assistant-session.json has modelId claude-sonnet-5.5 and effortLevel high (or none recorded);
+#                                      every reasoningModelId in <label>/assistant-session-messages.jsonl is [qdev::]claude-sonnet-5.5
+#   model_check.sh all       <label> <S>   org, then assistant
+# <label> is the G0 stream label (m0-s1, m1-s2, m0-s1r, ...), or "preflight" for a scratch org (output in evidence/preflight/). Appends a block
+# to evidence/<label>/model-checks.txt and prints its RESULT line. The assistant's profile is looked for in ~/.kiro/agents, in the arm M0's
+# dedicated home (<label>/m0-home-path.txt) and in <label>/profiles/.
 # Exit 0: every seat checked is in the set (or, for listed, the model is listed). Exit 1: a seat outside the set (stream-invalidating,
 # H4), or claude-sonnet-5.5 not listed (the stream does not start). Exit 2: usage error, or nothing to check yet (never a pass).
 MODE="$1"; N="$2"; S="$3"
-[[ -n "$MODE" && -n "$N" ]] || { echo "usage: model_check.sh listed|org|assistant|all <N> [<S>]" >&2; exit 2; }
-[[ "$MODE" == listed || -n "$S" ]] || { echo "usage: model_check.sh $MODE <N> <S>" >&2; exit 2; }
-EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s$N
-[[ "$N" == preflight ]] && EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/preflight
+[[ -n "$MODE" && -n "$N" ]] || { echo "usage: model_check.sh listed|org|assistant|all <label> [<S>]" >&2; exit 2; }
+[[ "$MODE" == listed || -n "$S" ]] || { echo "usage: model_check.sh $MODE <label> <S>" >&2; exit 2; }
+EV=/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/$N
+[[ "$N" == preflight ]] && EV=/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/preflight
 mkdir -p "$EV"
 OUT="$EV/model-checks.txt"
 LISTING=""
@@ -43,7 +44,7 @@
     return [tokens[i + 1] for i, t in enumerate(tokens[:-1]) if t == name]
 
 
-print(f"## model check {mode} s{n} at {now()} (set: {MODEL} at effort {EFFORT})")
+print(f"## model check {mode} {n} at {now()} (set: {MODEL} at effort {EFFORT})")
 bad, nothing = [], []
 
 
@@ -80,15 +81,20 @@
 
 
 def assistant():
-    name = f"hirearchy-study-e7-s{n}-assistant"
-    prof = [p for p in (os.path.expanduser(f"~/.kiro/agents/{name}.json"), os.path.join(ev, "profiles", f"{name}.json")) if os.path.isfile(p)]
+    name = f"hirearchy-study-g0-{n}-assistant"
+    cands = [os.path.expanduser(f"~/.kiro/agents/{name}.json")]
+    m0p = os.path.join(ev, "m0-home-path.txt")
+    if os.path.isfile(m0p):  # arm M0: the profile lives in the dedicated home
+        cands.append(os.path.join(open(m0p).read().strip(), ".kiro", "agents", f"{name}.json"))
+    cands.append(os.path.join(ev, "profiles", f"{name}.json"))
+    prof = [p for p in cands if os.path.isfile(p)]
     if prof:
         m = json.load(open(prof[0])).get("model")
         print(f"  profile {prof[0]}: model {m!r}")
         if m != MODEL:
             bad.append(f"assistant profile model {m!r}")
     else:
-        nothing.append(f"profile {name}.json not found in ~/.kiro/agents or s{n}/profiles")
+        nothing.append(f"profile {name}.json not found in ~/.kiro/agents, the M0 home or {n}/profiles")
     cmds = sorted(glob.glob(os.path.join(ev, "turn-*.cmd.txt")))
     if not cmds:
         nothing.append("no turn-NN.cmd.txt yet")
@@ -109,7 +115,7 @@
         if eff not in (None, "", EFFORT):
             bad.append(f"assistant session effortLevel {eff!r}")
     else:
-        nothing.append(f"no session copy s{n}/assistant-session.json yet")
+        nothing.append(f"no session copy {n}/assistant-session.json yet")
     mj = os.path.join(ev, "assistant-session-messages.jsonl")
     if os.path.isfile(mj):
         vals = {}
@@ -123,7 +129,7 @@
             if v.split("::")[-1] != MODEL:
                 bad.append(f"assistant reasoningModelId {v!r} (x{k})")
     else:
-        nothing.append(f"no session copy s{n}/assistant-session-messages.jsonl yet")
+        nothing.append(f"no session copy {n}/assistant-session-messages.jsonl yet")
 
 
 steps = {"listed": [listed], "org": [org], "assistant": [assistant], "all": [org, assistant]}
@@ -142,7 +148,7 @@
     res = "INCOMPLETE (nothing to check yet; not a pass)"
 else:
     res = "OK"
-print(f"RESULT: s{n} {mode}: {res} ({now()})")
+print(f"RESULT: {n} {mode}: {res} ({now()})")
 sys.exit(1 if bad else (2 if nothing else 0))
 EOF
 rc=$?
```

### `safety-snapshot.sh` (from `harness/safety-snapshot.sh`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/safety-snapshot.sh	2026-10-25 06:14:43
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/safety-snapshot.sh	2026-10-26 03:40:00
@@ -1,9 +1,9 @@
 #!/bin/zsh
-# E7 safety snapshot (read-only). Usage: safety-snapshot.sh <label>   -> prints to stdout
-# Content per protocol.md 4.8 (E3's snapshot + E4 additions). Never modifies anything it lists.
+# G0 safety snapshot (E7's; read-only). Usage: safety-snapshot.sh <label>   -> prints to stdout
+# Content per protocol.md 4.8 (E3's snapshot + E4 additions; G0: the product sha 3c841bb9, G0's protocol path, the /tmp/hirearchy-g0-* listing). Never modifies anything it lists.
 label="${1:-snapshot}"
 REPO=/Volumes/workspace/hirearchy
-PROTO=$REPO/studies/E7-org-growth-0a4-recheck/evidence/protocol.md
+PROTO=$REPO/studies/G0-noise-baseline/evidence/protocol.md
 echo "label: $label"
 echo "date: $(date)"
 echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)  epoch: $(date +%s)"
@@ -19,7 +19,7 @@
 ls -la ~/.kiro/agents
 echo "== md5 ~/.kiro/agents/*"
 for f in ~/.kiro/agents/*(.N); do md5 "$f"; done
-echo "== hirearchy-* profiles in ~/.kiro/agents (pre-existing vs generated by E7)"
+echo "== hirearchy-* profiles in ~/.kiro/agents (pre-existing vs generated by G0: hirearchy-study-g0-*)"
 ls -1 ~/.kiro/agents | grep '^hirearchy-' || echo "(none)"
 echo "== ls ~/.kiro/skills"
 ls ~/.kiro/skills
@@ -36,10 +36,13 @@
 git -C $REPO status --porcelain
 echo "== git HEAD"
 git -C $REPO rev-parse HEAD
-echo "== git diff --stat 18a4531 HEAD -- src skills pyproject.toml uv.lock"
-git -C $REPO diff --stat 18a4531 HEAD -- src skills pyproject.toml uv.lock
+echo "== git diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock"
+git -C $REPO diff --stat 3c841bb9 HEAD -- src skills pyproject.toml uv.lock
 echo "== md5 protocol.md"
 md5 $PROTO
 echo "== other orgs"
 ls -d /Volumes/workspace/orgs
 ls -la /Volumes/workspace/orgs
+echo "== /tmp/hirearchy-g0-* (sandboxes and dedicated kiro homes; names only)"
+g0dirs=(/tmp/hirearchy-g0-*(N))
+if (( ${#g0dirs} )); then print -rl -- ${g0dirs:t}; else echo "(none)"; fi
```

### `copy_org_evidence.sh` (from `harness/copy_org_evidence.sh`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/copy_org_evidence.sh	2026-10-25 06:14:43
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/copy_org_evidence.sh	2026-10-26 04:31:26
@@ -1,9 +1,9 @@
 #!/bin/zsh
-# E7: read-only copy of a stream's org into the evidence folder (protocol 7.2 "The org"), after the stream ended.
-# Usage: copy_org_evidence.sh <S> <stream N>
+# G0: read-only copy of a stream's org into the evidence folder (protocol 7.2 "The org"), after the stream ended (E7's, plus memos/versions/).
+# Usage: copy_org_evidence.sh <S> <label>
 # Uses only file copies and the read-only CLI commands of protocol 4.8 (services | progress | status | health, obs trace).
 S="$1"; N="$2"
-EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s$N
+EV=/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/$N
 ORG="$S/org"
 HIR="uv --directory /Volumes/workspace/hirearchy run hirearchy"
 mkdir -p $EV/msgs $EV/run-logs $EV/events $EV/org-files $EV/service $EV/playbook
@@ -34,6 +34,9 @@
 git -C $ORG log --reverse --format='%h %cI' -- '*PLAYBOOK.md' | while read h t; do f=$(git -C $ORG ls-files -- '*PLAYBOOK.md' | head -1); git -C $ORG show $h:$f > $EV/playbook/PLAYBOOK.$h.md 2>/dev/null; echo "$h $t" >> $EV/playbook/versions.txt; done
 # deliverables
 [[ -d $S/deliverables ]] && { mkdir -p $EV/memos; cp -p $S/deliverables/* $EV/memos/ 2>/dev/null; }
+# memos/versions/ is NOT written here: extract_mechanical.py writes it (E7's rule: every .md under the owner's */work/ folders except the
+# final-check seat's, every committed version, and INDEX.txt), from the sandbox org's git, when finish_stream.sh runs it after this script.
+# One writer only, so the index keeps E7's rule (protocol 15 item 14; a draft of this script also indexed the reviewer's work files).
 # read-only CLI after the stream
 {
   for c in services progress status health; do echo "######## hirearchy --root $ORG $c"; ${=HIR} --root $ORG $c 2>&1; echo; done
```

### `after_turn.sh` (from `s1/prompts/after_turn.sh`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s1/prompts/after_turn.sh	2026-10-25 07:07:44
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/after_turn.sh	2026-10-26 03:41:10
@@ -1,19 +1,32 @@
 #!/bin/zsh
-# facilitator helper (E7 s1, protocol 6 item 3): usage after_turn.sh <turn n>   -- no MCP/CLI call against the org (file reads and ps only)
-# Adapted from E6 s1's prompts/after_turn.sh: paths and names E7's; adds the signal record (D-SIGNAL) and the ambient comparison (4.5.1).
-N=1; T="$1"
-EV=/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence
-D=$EV/s$N; S=$(cat $D/sandbox-path.txt)
+# G0 facilitator helper (protocol 6 item 3), frozen with the harness: usage after_turn.sh <label> <turn n>
+# -- no MCP/CLI call against the org (file reads, ps and the read-only quality snapshot at the very end).
+# E7's s<N>/prompts/after_turn.sh (E6 s1's helper, with the signal record fixed to read events/<date>/*.jsonl), generalized from a per-stream
+# copy to any G0 label. The assistant's session store is searched in the ARM's kiro home: M1 ~/.kiro, M0 <M0H>/.kiro (<label>/m0-home-path.txt).
+# Steps, in order: org state; the assistant session copy; the scheduler record (D-SURVIVE); the signal record (D-SIGNAL); model_check org and
+# assistant; the throttle scan; the ambient comparison (the md5 lines of the previous after-snapshot or setup, and this turn's before and
+# after: the owner's four lines and, for M0, the dedicated home's three); then quality_snapshot.sh <label> turn-NN LAST (it reads the org
+# through the product's CLI only when ORG.md exists).
+LABEL="$1"; T="$2"
+REPO=/Volumes/workspace/hirearchy
+ST=$REPO/studies/G0-noise-baseline
+EV=$ST/evidence
+[[ "$LABEL" =~ '^(m0|m1)-s[1-9][0-9]*(r[0-9]*)?$' && "$T" =~ '^[1-9][0-9]*$' && $# -eq 2 ]] || { echo "usage: after_turn.sh <label> <turn n>" >&2; exit 2; }
+D=$EV/$LABEL; S=$(cat $D/sandbox-path.txt); SN=${S:t}
+ARM=${LABEL%%-*}
+KH=$HOME/.kiro
+[[ "$ARM" == m0 ]] && KH="$(cat $D/m0-home-path.txt)/.kiro"
+PROFILE=hirearchy-study-g0-$LABEL-assistant
 NN=$(printf '%02d' "$T")
 python3 $EV/harness/org_state.py $S "after turn $T" >> $D/run-counts-by-turn.txt 2>&1
-python3 - "$S" "$D" <<'PY'
+python3 - "$S" "$D" "$KH" "$PROFILE" <<'PY'
 import json,glob,os,sys,shutil
-S,D=sys.argv[1:3]; real=os.path.realpath(S)
+S,D,KH,PROFILE=sys.argv[1:5]; real=os.path.realpath(S)
 best=None; bt=0
-for p in glob.glob(os.path.expanduser('~/.kiro/sessions/*/sess_*/session.json')):
+for p in glob.glob(os.path.join(KH,'sessions/*/sess_*/session.json')):
     try: j=json.load(open(p))
     except Exception: continue
-    if j.get('agentMode')=='hirearchy-study-e7-s1-assistant' and (j.get('workspacePaths') or [''])[0] in (real,S):
+    if j.get('agentMode')==PROFILE and (j.get('workspacePaths') or [''])[0] in (real,S):
         m=os.path.getmtime(p)
         if m>=bt: best,bt=p,m
 if not best: print('NO SESSION FOUND'); sys.exit(1)
@@ -32,7 +45,7 @@
     echo "scheduler.pid: (no file)"
   fi
   echo "scheduler.exit: $( [[ -f $S/org/.runtime/scheduler.exit ]] && cat $S/org/.runtime/scheduler.exit | head -3 | tr '\n' ' ' || echo '(none)')"
-  echo "processes referencing the sandbox name:"; ps -axo pid,ppid,stat,etime,command | grep hirearchy-e7-s1 | grep -v grep || echo "(none)"
+  echo "processes referencing the sandbox name:"; ps -axo pid,ppid,stat,etime,command | grep -F "$SN" | grep -v grep || echo "(none)"
 } >> $D/run-counts-by-turn.txt 2>&1
 # signal record (E7 item 5; D-SIGNAL): every scheduler.signal line in events/ (file reading only)
 {
@@ -45,8 +58,8 @@
   else echo "(no events dir)"; fi
   echo "(turn $T end per turn-times.txt:)"; grep -E "^turn $T:" $D/turn-times.txt
 } >> $D/run-counts-by-turn.txt 2>&1
-zsh $EV/harness/model_check.sh org $N $S | tail -3
-zsh $EV/harness/model_check.sh assistant $N $S | tail -8
+zsh $EV/harness/model_check.sh org $LABEL $S | tail -3
+zsh $EV/harness/model_check.sh assistant $LABEL $S | tail -8
 # throttle marks / exit 75 among run logs
 echo "--- throttle/exit-75 scan after turn $T" >> $D/run-counts-by-turn.txt
 { [[ -d $S/org ]] && find $S/org -path '*/runs/*.log' -not -path '*/.git/*' -exec grep -lE '^# kiro: throttled by the model service|^# exit 75 ' {} + ; } >> $D/run-counts-by-turn.txt 2>/dev/null; echo "(end of scan)" >> $D/run-counts-by-turn.txt
@@ -55,3 +68,4 @@
 echo "--- ambient comparison turn $T (md5 lines)"
 for f in $PREV $D/ambient/turn-$NN-before.txt $D/ambient/turn-$NN-after.txt; do echo "## $(basename $f)"; grep -E 'listing md5|memories\.db' $f; done
 tail -45 $D/run-counts-by-turn.txt
+zsh $EV/harness/quality_snapshot.sh $LABEL turn-$NN
```

### `extract_mechanical.py` (from `harness/extract_mechanical.py`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/harness/extract_mechanical.py	2026-10-25 06:14:43
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/extract_mechanical.py	2026-10-26 03:46:53
@@ -1,12 +1,35 @@
 #!/usr/bin/env python3
-"""E7 mechanical extracts (protocol 7.2 "Mechanical extracts", amendment 1 A3). Facts only; no scoring. Read-only on the sandbox,
-the org and the kiro home (file copies only). Usage:
-    uv --directory /Volumes/workspace/hirearchy run python extract_mechanical.py <stream, e.g. 1r>
-Needs evidence/s<N>/ to hold sandbox-path.txt, assistant-session-messages.jsonl, events/, run-logs/, msgs/ (copy_org_evidence.sh).
-Writes into evidence/s<N>/: org-kiro-sessions/, profiles/ (org scheduler profiles, copied), run-session-map.txt,
-revise-playbook-attempts.txt, client-questions.txt, contract-loop.txt, deliverables-log.txt, shell-writes.txt,
-lead-prompt-sizes.txt, reflect-sections/, regression-list/, memos/versions/, injection/ (copy + text-identity + window-runs),
-cost.txt (credits parts), run-counts.txt."""
+"""G0 mechanical extracts (E7 protocol 7.2 "Mechanical extracts"; facts only, no scoring).
+
+ONE script for every stream. It is E7's `harness/extract_mechanical.py` (and E7's per-stream copies `s1|s2|s3/harness/extract_mechanical.py`
+and the frozen `extract_mechanical_s2.py`/`_s3.py`, which differed from it in exactly the service folder name, the final-check seat's message
+glob and prefix, and the sandbox-name patterns) with those per-stream choices detected instead of edited:
+  * the owner (the agent root's tasks go to) and the service folder name: from root's sent tasks (`to`, `service`) in the stream dir;
+  * the final-check seat: the agent below the owner whose name says review/check/..., else whose charter (`org-files/<agent>-AGENT.md`)
+    says review/check, else whose results carry `criteria met`; the regression-list file prefix is the seat's last address part
+    (`reviewer-task-<msg>.md` for E7's `lead/reviewer`);
+  * the sandbox-name patterns: from the stream's own `sandbox-path.txt` (and the generic `/tmp/hirearchy-<...>-<epoch>/org/` form).
+
+Usage:
+    python3 -B extract_mechanical.py <streamdir> <sandbox S or "-"> [--out DIR] [--product-src DIR]
+  <streamdir>  the stream's evidence dir (E7's layout: `s1/`, or G0's `m0-s1/`); never written unless it is also --out.
+  S            the sandbox path (E7's second input) or "-": with "-" (or when S is gone) every input comes from the stream dir only:
+               the org git history from `memos/versions/INDEX.txt`, `playbook/versions.txt` and `org-git-log.txt`; the org-run sessions from
+               `org-kiro-sessions/`; the deliverable folder listing from `memos/`.  With a sandbox that exists the script reads it as E7's did
+               (`git -C S/org`, the org's kiro home from the run logs' `# cwd:`, `S/deliverables`) and copies the org-run sessions, the org
+               profiles, the playbook/service history and `memos/versions/` into --out, as E7's did.
+  --out DIR    where the extracts are written (default: the stream dir, as E7's).
+
+Writes into --out: revise-playbook-attempts.txt, client-questions.txt, contract-loop.txt, deliverables-log.txt, shell-writes.txt,
+lead-prompt-sizes.txt, reflect-sections/, regression-list/, cost.txt, run-session-map.txt (and, with a sandbox: org-kiro-sessions/,
+profiles/, playbook/, service/, memos/versions/). Not written (E7 wrote them in the same script): `run-counts.txt` (its `final` block is
+org_state.py's time-stamped snapshot, so it cannot be reproduced) and `injection/` (injection_files.py writes it).
+
+PRODUCT IMPORT (read-only, stated): `client-questions.txt` lists the items by the PRODUCT's parser `hirearchy.kernel._text.client_questions`,
+exactly as E7's did (E7 inserted `/Volumes/workspace/hirearchy/src` into sys.path and imported it). That is the only product import in the
+harness: the build was told to keep it. It is read-only: `sys.dont_write_bytecode` is set before the import (no `__pycache__` appears under
+`src/`), nothing in the product is called but that pure function, and `--product-src` can point to another checkout. Every other script of
+the harness is stdlib-only and independent of the product (assistant_facts.py parses the items back out of `client-questions.txt`)."""
 import glob
 import hashlib
 import json
@@ -18,14 +41,11 @@
 from datetime import datetime, timezone
 from pathlib import Path
 
-EV = Path("/Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence")
-N = sys.argv[1]
-D = EV / f"s{N}"
-S = Path((D / "sandbox-path.txt").read_text().strip())
-ORG = S / "org"
-sys.path.insert(0, "/Volumes/workspace/hirearchy/src")
+sys.dont_write_bytecode = True
 
+PRODUCT_SRC = "/Volumes/workspace/hirearchy/src"
 
+
 def md5b(b: bytes) -> str:
     return hashlib.md5(b).hexdigest()
 
@@ -38,214 +58,11 @@
     return datetime.strptime(stamp[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
 
 
-def git(*a: str) -> str:
-    return subprocess.run(["git", "-C", str(ORG), *a], capture_output=True, text=True).stdout
-
-
 def payload(d):
     p = d["payload"]
     return json.loads(p) if isinstance(p, str) else p
 
 
-# ---------------------------------------------------------------- assistant session -> calls
-calls, turns = [], []
-turn_no = 0
-byid = {}
-for line in open(D / "assistant-session-messages.jsonl"):
-    d = json.loads(line)
-    p = payload(d)
-    ts = d.get("timestamp", "")
-    t = p.get("type")
-    if t == "user":
-        turn_no += 1
-        turns.append({"n": turn_no, "user_ts": ts})
-    elif t == "turn_start" and turns:
-        turns[-1]["start"] = ts
-    elif t == "turn_end" and turns:
-        turns[-1]["end"] = ts
-    elif t == "tool_call":
-        kiro = (p.get("_meta") or {}).get("kiro") or {}
-        args = p.get("args") or {}
-        name = p.get("toolName")
-        tool = args.get("tool_id") if name == "tool_call" else None
-        c = {"n": len(calls) + 1, "ts": ts, "turn": turn_no, "name": name, "tool": tool, "args": args,
-             "status": p.get("status"), "result": None, "rts": None, "id": p.get("toolCallId")}
-        calls.append(c)
-        byid[c["id"]] = c
-    elif t == "tool_result":
-        c = byid.get(p.get("toolCallId"))
-        if c:
-            content = p.get("content")
-            c["result"] = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
-            c["rts"] = ts
-            c["rstatus"] = p.get("status")
-
-tt = {}
-for ln in open(D / "turn-times.txt"):
-    m = re.match(r"turn (\d+): (\S+) - (\S+)\s+\S+\s+utc (\S+) - (\S+)\s+exit (\d+)", ln)
-    if m:
-        tt[int(m.group(1))] = {"utc_start": m.group(4), "utc_end": m.group(5), "exit": m.group(6)}
-for tr in turns:
-    tr.update(tt.get(tr["n"], {}))
-
-
-def hcalls(*names):
-    return [c for c in calls if c["tool"] and c["tool"].split("::")[-1] in names]
-
-
-# ---------------------------------------------------------------- events
-events = []
-for f in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
-    for line in open(f):
-        e = json.loads(line)
-        e["_file"] = Path(f).name
-        events.append(e)
-events.sort(key=lambda e: e["ts"])
-
-# ---------------------------------------------------------------- run logs
-runs = []
-for lg in sorted(glob.glob(str(D / "run-logs" / "*" / "*.log"))):
-    txt = Path(lg).read_text(errors="replace")
-    stamp = Path(lg).stem
-    agent_dir = Path(lg).parent.name
-    cwd = re.search(r"^# cwd: (.*)$", txt, re.M)
-    cmd = re.search(r"^# cmd: .*? --agent (\S+) --model (\S+)", txt, re.M)
-    ex = re.search(r"^# exit (\S+) after (\d+)s", txt, re.M)
-    runs.append({"stamp": stamp, "agent_dir": agent_dir, "path": lg, "cwd": cwd.group(1) if cwd else None,
-                 "agent_profile": cmd.group(1) if cmd else None, "model": cmd.group(2) if cmd else None,
-                 "exit": ex.group(1) if ex else None, "secs": int(ex.group(2)) if ex else None, "text": txt,
-                 "dt": stamp_to_dt(stamp)})
-runs.sort(key=lambda r: r["stamp"])
-for r in runs:
-    r["start_ev"] = next((e for e in events if e["kind"] == "run.start" and e.get("run", "").endswith("@" + r["stamp"])), None)
-    r["end_ev"] = next((e for e in events if e["kind"] == "run.end" and e.get("run", "").endswith("@" + r["stamp"])), None)
-    r["run_id"] = (r["start_ev"] or {}).get("run") or ("?@" + r["stamp"])
-
-# ---------------------------------------------------------------- org kiro home (A3.2)
-first_cwd = runs[0]["cwd"]
-m = re.match(r"(.*)/kiro-cwd/([^/]+)/[^/]+$", first_cwd)
-STATE, ORGID = Path(m.group(1)), m.group(2)
-KH = STATE / "kiro-home" / ORGID
-cwds = Counter(re.match(r"(.*/kiro-cwd/[^/]+)/", r["cwd"]).group(1) for r in runs)
-out = []
-out.append(f"# run-session map (amendment 1 A3.2)\nstate dir: {STATE}\nfirst run log # cwd: {first_cwd}\nkiro home: {KH}")
-out.append(f"every run log shows the same <state>/kiro-cwd/<org-id>/: {len(cwds) == 1} ({dict(cwds)})")
-sess = []
-for sj in sorted(glob.glob(str(KH / "sessions" / "*" / "sess_*" / "session.json"))):
-    sd = Path(sj).parent
-    j = json.load(open(sj))
-    credits = 0.0
-    tool_calls = Counter()
-    try:
-        for line in open(sd / "messages.jsonl"):
-            p = payload(json.loads(line))
-            if p.get("type") == "usage_summary":
-                for s in p.get("promptTurnSummaries") or []:
-                    credits += s.get("usage", 0) or 0
-            if p.get("type") == "tool_call":
-                a = p.get("args") or {}
-                tool_calls[a.get("tool_id") or p.get("toolName")] += 1
-    except FileNotFoundError:
-        pass
-    dst = D / "org-kiro-sessions" / sd.parent.name / sd.name
-    dst.mkdir(parents=True, exist_ok=True)
-    shutil.copy2(sj, dst / "session.json")
-    if (sd / "messages.jsonl").exists():
-        shutil.copy2(sd / "messages.jsonl", dst / "messages.jsonl")
-    sess.append({"id": j["id"], "hash": sd.parent.name, "cwd": (j.get("workspacePaths") or [None])[0], "mode": j.get("agentMode"),
-                 "model": j.get("modelId"), "created": j.get("createdAt"), "credits": credits, "dir": dst, "tools": tool_calls})
-out.append(f"org kiro sessions copied: {len(sess)} (to org-kiro-sessions/<hash>/<session id>/)")
-norm = lambda p: str(Path(p).resolve()) if p else p  # noqa: E731
-unmatched_runs, used = [], set()
-for r in runs:
-    cand = []
-    for s in sess:
-        if s["id"] in used:
-            continue
-        if norm(s["cwd"]) != norm(r["cwd"]) and s["cwd"] != r["cwd"]:
-            continue
-        if s["mode"] != r["agent_profile"] or s["model"] != r["model"]:
-            continue
-        a, b = r["start_ev"], r["end_ev"]
-        if a and b and not (parse_ts(a["ts"]) <= parse_ts(s["created"]) <= parse_ts(b["ts"])):
-            continue
-        cand.append(s)
-    if len(cand) == 1:
-        r["session"] = cand[0]
-        used.add(cand[0]["id"])
-    else:
-        r["session"] = None
-        unmatched_runs.append((r["stamp"], len(cand)))
-    out.append(f"run {r['run_id']:40s} {r['stamp']} model={r['model']} exit={r['exit']} secs={r['secs']} -> session "
-               f"{(r['session'] or {}).get('id', 'NOT MATCHED (%d candidates)' % len(cand))} credits "
-               f"{('%.6f' % r['session']['credits']) if r['session'] else 'not recorded'}")
-out.append(f"unmatched runs: {unmatched_runs}; sessions without a run: {[s['id'] for s in sess if s['id'] not in used]}")
-(D / "run-session-map.txt").write_text("\n".join(out) + "\n")
-
-# org scheduler profiles (copied, not deleted: A3.2)
-(D / "profiles").mkdir(exist_ok=True)
-for f in glob.glob(str(KH / "agents" / "hirearchy-*.json")):
-    shutil.copy2(f, D / "profiles" / ("org-kiro-home--" + Path(f).name))
-
-# ---------------------------------------------------------------- revise-playbook-attempts.txt
-o = ["# revise_playbook attempts (protocol 7.2; amendment 1 A3.3 10.1(c)); facts only", ""]
-rp = [e for e in events if e["kind"] == "tool.call" and e.get("tool") == "revise_playbook"]
-o.append(f"tool.call events with tool == revise_playbook: {len(rp)}")
-for e in rp:
-    o.append(f"- {e['ts']} actor={e.get('actor')} run={e.get('run')} trace={e.get('trace')} ok={e.get('ok')} error_type={e.get('error_type')}\n  error (verbatim): {e.get('error')}\n  args: {json.dumps(e.get('args'), ensure_ascii=False)}")
-o.append("")
-P1 = re.compile(r"^\[tool\] @hirearchy/revise_playbook(?= |$)", re.M)
-P2 = re.compile(r"^\[tool (?:ok|failed)\] @hirearchy/revise_playbook(?= |$)", re.M)
-P3 = re.compile(r"^\[tool\] @hirearchy/\w+", re.M)
-o.append("run-log patterns per run (after '# ---- output ----'): P1 revise_playbook call lines | P2 end lines | P3 all hirearchy call lines | tool.call events whose run is this run")
-for r in runs:
-    outp = r["text"].split("# ---- output ----", 1)[-1]
-    ev_n = sum(1 for e in events if e["kind"] == "tool.call" and e.get("run") == r["run_id"])
-    ev_rp = sum(1 for e in rp if e.get("run") == r["run_id"])
-    p1, p2, p3 = len(P1.findall(outp)), len(P2.findall(outp)), len(P3.findall(outp))
-    flag = "" if (p1 == ev_rp and p3 == ev_n) else "   <-- MISMATCH between run-log lines and events"
-    o.append(f"  {r['run_id']:44s} P1={p1} P2={p2} P3={p3} events(all)={ev_n} events(revise_playbook)={ev_rp}{flag}")
-    for ln in re.findall(r"^\[tool(?: ok| failed)?\] @hirearchy/revise_playbook.*$", outp, re.M):
-        o.append(f"      {ln[:400]}")
-o.append("")
-o.append("full arguments and result verbatim, from the org-run session (tool_call with args.tool_id == hirearchy::revise_playbook):")
-for r in runs:
-    s = r.get("session")
-    if not s:
-        continue
-    byc = {}
-    for line in open(s["dir"] / "messages.jsonl"):
-        p = payload(json.loads(line))
-        if p.get("type") == "tool_call" and (p.get("args") or {}).get("tool_id") == "hirearchy::revise_playbook":
-            byc[p["toolCallId"]] = {"args": p["args"], "res": None}
-            byc[p["toolCallId"]]["ts"] = json.loads(line).get("timestamp")
-        elif p.get("type") == "tool_result" and p.get("toolCallId") in byc:
-            c = p.get("content")
-            byc[p["toolCallId"]]["res"] = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
-    for cid, v in byc.items():
-        o.append(f"--- run {r['run_id']} session {s['id']} call {cid} at {v['ts']}\nARGUMENTS: {json.dumps(v['args'], ensure_ascii=False, indent=1)}\nRESULT: {v['res']}")
-o.append("")
-o.append("service.revise events:")
-for e in events:
-    if e["kind"] == "service.revise":
-        o.append(f"- {e['ts']} {json.dumps({k: v for k, v in e.items() if k not in ('v', 'seq', '_file')}, ensure_ascii=False)}")
-o.append("")
-o.append("PLAYBOOK versions (org git history of lead/services/weekly-memo/PLAYBOOK.md and history/):")
-o.append(git("log", "--reverse", "--format=%h %cI %s", "--", "lead/services/weekly-memo/PLAYBOOK.md", "lead/services/weekly-memo/history").strip())
-hist = sorted(glob.glob(str(ORG / "lead/services/weekly-memo/history/*")))
-o.append("history files now: " + ", ".join(Path(h).name for h in hist))
-for h in hist:
-    dst = D / "playbook" / ("history--" + Path(h).name)
-    shutil.copy2(h, dst)
-    for sub in ("service",):
-        pass
-for h in glob.glob(str(ORG / "lead/services/weekly-memo/history/SERVICE.v*.md")):
-    shutil.copy2(h, D / "service" / ("history--" + Path(h).name))
-shutil.copy2(ORG / "lead/services/weekly-memo/SERVICE.md", D / "service" / "current-SERVICE.md")
-shutil.copy2(ORG / "lead/services/weekly-memo/PLAYBOOK.md", D / "playbook" / "current-PLAYBOOK.md")
-(D / "revise-playbook-attempts.txt").write_text("\n".join(o) + "\n")
-
-# ---------------------------------------------------------------- messages (root's)
 def read_msg(path):
     txt = Path(path).read_text()
     m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
@@ -257,245 +74,583 @@
     return hdr, m.group(2), txt
 
 
-# ---------------------------------------------------------------- client-questions.txt
-from hirearchy.kernel._text import client_questions  # noqa: E402
+# ---------------------------------------------------------------- detection (replaces E7's per-stream edits)
+SEAT_NAME = re.compile(r"review|check|qa|verif|audit|inspect", re.I)
 
-o = ["# client questions (protocol 7.2); facts only", ""]
-o.append("Result messages root received (lead -> root), with the product parser's items (hirearchy.kernel._text.client_questions):")
-for d in ("inbox", "read"):
-    for f in sorted(glob.glob(str(D / "msgs" / d / "*.md"))):
-        hdr, body, raw = read_msg(f)
-        if hdr.get("to") != "root" or hdr.get("type") != "result":
-            continue
-        raw_q = ""
-        mm = re.search(r"(?im)^.*questions for the client.*$", body)
-        if mm:
-            raw_q = body[mm.start():]
-            raw_q = raw_q.split("\n## ", 1)[0]
-        items = client_questions(body)
-        o.append(f"- id {hdr.get('id')} folder={d} created={hdr.get('created')} answers(reply_to)={hdr.get('reply_to')} status={hdr.get('status')} from={hdr.get('from')}\n"
-                 f"  raw 'Questions for the client' text: {raw_q.strip() if raw_q else '(none)'}\n  parsed items ({len(items)}): {items}")
-o.append("")
-FLAG = "for the client: ask the user before you copy or deliver"
-o.append(f"progress replies the assistant received that contain {FLAG!r}:")
-n_flag = 0
-for c in calls:
-    if c["result"] and FLAG in c["result"]:
-        n_flag += 1
-        lines = [ln for ln in c["result"].splitlines() if FLAG in ln]
-        o.append(f"- call #{c['n']} {c['ts']} turn {c['turn']} {c['tool']}: {lines}")
-o.append(f"count: {n_flag}")
-(D / "client-questions.txt").write_text("\n".join(o) + "\n")
+
+def detect(D: Path) -> dict:
+    """Owner, service folder name and final-check seat of a stream, from the stream dir alone."""
+    D = Path(D)
+    owner = service = None
+    for f in sorted(glob.glob(str(D / "msgs" / "sent" / "*.md"))):
+        hdr, _, _ = read_msg(f)
+        if hdr.get("from") == "root" and hdr.get("type") == "task" and hdr.get("service") and hdr.get("to"):
+            owner, service = hdr["to"], hdr["service"]
+            break
+    agents = sorted(p.name for p in (D / "run-logs").iterdir() if p.is_dir()) if (D / "run-logs").is_dir() else []
+    if owner is None:
+        owner = min(agents, key=lambda a: (a.count("-"), a)).replace("-", "/") if agents else "lead"
+    owner_dir = owner.replace("/", "-")
+    if service is None:
+        for f in sorted(glob.glob(str(D / "org-files" / f"current-{owner_dir}-services-*-SERVICE.md"))):
+            service = Path(f).name[len(f"current-{owner_dir}-services-"):-len("-SERVICE.md")]
+            break
+    below = [a for a in agents if a.startswith(owner_dir + "-")]
+    seat = None
+    by_name = [a for a in below if SEAT_NAME.search(a[len(owner_dir) + 1:])]
+    if by_name:
+        seat = by_name[0]
+    if seat is None:
+        by_charter = []
+        for a in below:
+            ch = D / "org-files" / f"{a}-AGENT.md"
+            if ch.exists():
+                t = ch.read_text(errors="replace").lower()
+                if "review" in t or "check" in t:
+                    by_charter.append((0 if "review" in t else 1, a))
+        if by_charter:
+            seat = sorted(by_charter)[0][1]
+    if seat is None:
+        for a in below:
+            for f in glob.glob(str(D / "msgs" / f"{a}-sent" / "*.md")):
+                if re.search(r"criteria met", Path(f).read_text(errors="replace"), re.I):
+                    seat = a
+                    break
+            if seat:
+                break
+    return {"owner": owner, "owner_dir": owner_dir, "service": service, "seat_dir": seat,
+            "seat_short": seat[len(owner_dir) + 1:].split("-")[-1] if seat else None, "agents": agents}
 
-# ---------------------------------------------------------------- contract-loop.txt
-o = ["# contract loop (protocol 7.2); facts only, time order", ""]
-o.append("Lena reject turns (D1 candidates: turns whose line starts with 'No, not right yet' / 'Not right yet' / 'Almost'):")
-for tr in turns:
-    pass
-lena = {}
-for ln in (D / "lena-lines.txt").read_text().splitlines():
-    m = re.match(r"turn (\d+) \| (.*)", ln)
-    if m:
-        lena[int(m.group(1))] = m.group(2)
-for n in sorted(lena):
-    prompt = (D / f"turn-{n:02d}.prompt.txt").read_text()
-    if re.match(r"(No, not right yet|Not right yet|Almost)", prompt):
-        tr = turns[n - 1]
-        o.append(f"- turn {n}: script UTC {tr.get('utc_start')} - {tr.get('utc_end')}; session turn_start {tr.get('start')} turn_end {tr.get('end')}; line: {prompt}")
-o.append("")
-o.append("assistant calls to feedback, define_service, request, services (full arguments and replies):")
-for c in calls:
-    if c["tool"] and c["tool"].split("::")[-1] in ("feedback", "define_service", "request", "services"):
-        o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} {c['tool']} status={c['status']}\nARGS: {json.dumps(c['args'], ensure_ascii=False)}\nREPLY ({c['rts']}): {c['result']}\n")
-o.append("root notes in S/org/sent with a feedback: or criterion: header:")
-for f in sorted(glob.glob(str(D / "msgs" / "sent" / "*.md"))):
-    hdr, body, raw = read_msg(f)
-    if "feedback" in hdr or "criterion" in hdr:
-        o.append(f"--- {Path(f).name} id={hdr.get('id')} created={hdr.get('created')}\nheaders: {json.dumps(hdr, ensure_ascii=False)}\nbody:\n{body.strip()}\n")
-(D / "contract-loop.txt").write_text("\n".join(o) + "\n")
 
-# ---------------------------------------------------------------- deliverables-log.txt and shell-writes.txt
-DELIV = str(S / "deliverables")
-DELIV2 = DELIV.replace("/tmp/", "/private/tmp/", 1)
+def source_paths(cmd: str):
+    """Sandbox-org paths (absolute under any /tmp/hirearchy-<...>-<epoch>/org/, or relative org/...) a command names."""
+    return re.findall(r"((?:/private)?/tmp/hirearchy-[\w-]+?-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
 
 
-def writes_to(cmd: str, d_variants) -> bool:
-    if not any(v in cmd for v in d_variants) and "deliverables" not in cmd:
-        return False
-    return bool(re.search(r"\b(cp|mv|rsync|ditto|install|tee|write_text)\b|sed -i|open\(|\.write\(|>>?\s*\S*deliverables|>\s", cmd))
+def shell_flags(cmd: str, S, deliv_variants=None):
+    """The flags of one execute_bash command (E7's, with the sandbox taken from the stream, not from a study name).
+    Returns (flags, writes_into_the_deliverable_folder)."""
+    S = str(S)
+    ORG = S + "/org"
+    DELIV = S + "/deliverables"
+    variants = deliv_variants or (DELIV, DELIV.replace("/tmp/", "/private/tmp/", 1))
+    flags = []
+    wrote = False
+    if any(v in cmd for v in variants) or "deliverables" in cmd:
+        wrote = bool(re.search(r"\b(cp|mv|rsync|ditto|install|tee|write_text)\b|sed -i|open\(|\.write\(|>>?\s*\S*deliverables|>\s", cmd))
+    if wrote:
+        flags.append("writes into the deliverable folder")
+    if ORG in cmd or ORG.replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
+        flags.append("touches S/org")
+    if re.search(r"\bhirearchy\b(?!-(?:e7|g0)\b)", cmd.replace(S, "").replace("/Volumes/workspace/hirearchy", "")):
+        flags.append("mentions hirearchy")
+    if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
+        flags.append("runs hirearchy CLI")
+    if re.search(r"\b(sed -i|>>?\s|tee |cp |mv |rm |write_text|open\([^)]*['\"]w)", cmd) and not flags:
+        flags.append("writes elsewhere (possible)")
+    return flags, wrote
 
 
-o = ["# deliverables log (protocol 7.2, D6); facts only", ""]
-sw = ["# shell writes (protocol 7.2): every execute_bash call of the assistant; facts only", ""]
-variants = (DELIV, DELIV2)
-for c in calls:
-    nm = c["name"]
-    if nm == "execute_bash":
-        cmd = c["args"].get("command", "")
-        flags = []
-        if writes_to(cmd, variants):
-            flags.append("writes into the deliverable folder")
-        if str(ORG) in cmd or str(ORG).replace("/tmp/", "/private/tmp/", 1) in cmd or re.search(r"\borg/", cmd):
-            flags.append("touches S/org")
-        if re.search(r"\bhirearchy\b(?!-e7)", cmd.replace(str(S), "").replace("/Volumes/workspace/hirearchy", "")):
-            flags.append("mentions hirearchy")
-        if re.search(r"(^|[;&|]\s*)(uv run )?hirearchy\s", cmd):
-            flags.append("runs hirearchy CLI")
-        if re.search(r"\b(sed -i|>>?\s|tee |cp |mv |rm |write_text|open\([^)]*['\"]w)", cmd) and not flags:
-            flags.append("writes elsewhere (possible)")
-        sw.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} status={c['status']} flags={flags or ['none']}\nCOMMAND: {cmd}\nRESULT: {(c['result'] or '')[:1500]}\n")
-        if "writes into the deliverable folder" in flags:
-            src = re.findall(r"((?:/private)?/tmp/hirearchy-e7-s\w+-\d+/org/[\w/.\-]+\.md|org/[\w/.\-]+\.md)", cmd)
-            src_info = []
-            for sp in src:
-                rel = sp.split("/org/", 1)[-1] if "/org/" in sp else sp[len("org/"):]
-                g = git("log", f"--until={c['ts']}", "-1", "--format=%h %cI", "--", rel).strip()
-                src_info.append(f"{rel} -> org-git commit at that time: {g or '(none)'}")
-            o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} execute_bash\nCOMMAND: {cmd}\nsource file(s): {src_info or 'not found in the command'}\nresult: {(c['result'] or '')[:600]}\n")
-    elif nm and re.search(r"write|create|append|edit|replace", nm) and "hirearchy" not in (c.get("tool") or ""):
-        path = c["args"].get("path") or c["args"].get("file_path") or ""
-        if "deliverables" in str(path) or "deliverables" in json.dumps(c["args"]):
-            o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} {nm} (file-write tool) args={json.dumps(c['args'], ensure_ascii=False)[:800]}\n")
-o.append("any other write into the deliverable folder (not by the assistant): none can be seen from the assistant session; the folder holds:")
-for p in sorted((S / "deliverables").glob("*")):
-    st = p.stat()
-    o.append(f"  {p.name} size {st.st_size} mtime {datetime.fromtimestamp(st.st_mtime).strftime('%H:%M:%S')} local md5 {md5b(p.read_bytes())}")
-o.append("")
-o.append("final ls -la:\n" + subprocess.run(["ls", "-la", str(S / "deliverables")], capture_output=True, text=True).stdout)
-(D / "deliverables-log.txt").write_text("\n".join(o) + "\n")
-(D / "shell-writes.txt").write_text("\n".join(sw) + "\n")
+# ---------------------------------------------------------------- the assistant session (shared with assistant_facts.py)
+def load_session(D: Path):
+    """(calls, turns) of the assistant session copy `assistant-session-messages.jsonl`: calls are numbered like assistant-tool-calls.txt;
+    `tool` is the MCP tool id of a `tool_call` wrapper (None for built-in tools); `uri` is the disclosed context's uri (disclose_context)."""
+    calls, turns = [], []
+    turn_no = 0
+    byid = {}
+    for line in open(Path(D) / "assistant-session-messages.jsonl"):
+        d = json.loads(line)
+        p = payload(d)
+        ts = d.get("timestamp", "")
+        t = p.get("type")
+        if t == "user":
+            turn_no += 1
+            turns.append({"n": turn_no, "user_ts": ts})
+        elif t == "turn_start" and turns:
+            turns[-1]["start"] = ts
+        elif t == "turn_end" and turns:
+            turns[-1]["end"] = ts
+        elif t == "tool_call":
+            args = p.get("args") or {}
+            name = p.get("toolName")
+            tool = args.get("tool_id") if name == "tool_call" else None
+            kiro = (p.get("_meta") or {}).get("kiro") or {}
+            c = {"n": len(calls) + 1, "ts": ts, "turn": turn_no, "name": name, "tool": tool, "args": args,
+                 "status": p.get("status"), "result": None, "rts": None, "id": p.get("toolCallId"),
+                 "uri": (kiro.get("disclosedContext") or {}).get("uri")}
+            calls.append(c)
+            byid[c["id"]] = c
+        elif t == "tool_result":
+            c = byid.get(p.get("toolCallId"))
+            if c:
+                content = p.get("content")
+                c["result"] = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
+                c["rts"] = ts
+                c["rstatus"] = p.get("status")
+    return calls, turns
 
-# ---------------------------------------------------------------- lead-prompt-sizes, reflect-sections, regression-list
-(D / "reflect-sections").mkdir(exist_ok=True)
-(D / "regression-list").mkdir(exist_ok=True)
-o = ["# lead prompt sizes (protocol 7.2): bytes between '# ---- prompt ----' and '# ---- output ----'", ""]
-for r in runs:
-    if r["agent_dir"] != "lead":
-        continue
-    txt = r["text"]
-    pr = txt.split("# ---- prompt ----\n", 1)[1].split("# ---- output ----", 1)[0]
-    size = len(pr.encode())
-    refl = re.search(r"^# Reflect before you start:.*?(?=^# (?!Reflect)|\Z)", pr, re.M | re.S)
-    reg = re.search(r"^# Regression list:.*?(?=^# (?!Regression)|\Z)", pr, re.M | re.S)
-    words = len(refl.group(0).split()) if refl else 0
-    o.append(f"{r['run_id']:30s} bytes={size} reflect_section={'yes' if refl else 'no'} reflect_words={words} regression_list={'yes' if reg else 'no'}")
-    if refl:
-        (D / "reflect-sections" / f"lead-{r['stamp']}.txt").write_text(refl.group(0))
-    if reg:
-        (D / "regression-list" / f"lead-{r['stamp']}.txt").write_text(reg.group(0))
-# regression list inside delegated review tasks (reviewer task messages)
-for f in sorted(glob.glob(str(D / "msgs" / "*checker*" / "*.md"))):
-    hdr, body, raw = read_msg(f)
-    if "Regression list" in body:
-        i = body.index("Regression list")
-        (D / "regression-list" / f"checker-task-{Path(f).name}").write_text(body[i - 2:i + 3000])
-(D / "lead-prompt-sizes.txt").write_text("\n".join(o) + "\n")
 
-# ---------------------------------------------------------------- memos/versions
-(D / "memos" / "versions").mkdir(parents=True, exist_ok=True)
-files = [x for x in git("ls-files", "lead/writer/work").split() if x.endswith(".md")]
-vlog = []
-for fpath in files:
-    hs = git("log", "--reverse", "--format=%h %cI", "--", fpath).strip().splitlines()
-    for i, ln in enumerate(hs, 1):
-        h, t = ln.split(" ", 1)
-        body = git("show", f"{h}:{fpath}")
-        (D / "memos" / "versions" / f"{Path(fpath).stem}.v{i}.{h}.md").write_text(body)
-        vlog.append(f"{fpath} v{i} {h} {t} md5 {md5b(body.encode())}")
-    cur = ORG / fpath
-    if cur.exists():
-        vlog.append(f"{fpath} working tree md5 {md5b(cur.read_bytes())} (committed head: {md5b(git('show', 'HEAD:' + fpath).encode())})")
-(D / "memos" / "versions" / "INDEX.txt").write_text("\n".join(vlog) + "\n")
-
-# ---------------------------------------------------------------- injection/
-inj = D / "injection"
-inj.mkdir(exist_ok=True)
-for f in glob.glob(str(S / "injection" / "*")):
-    shutil.copy2(f, inj / Path(f).name)
-log = (inj / "injection-log.txt").read_text()
-iid = re.search(r"injected task id: (\S+)", log).group(1)
-mid = re.search(r"revised task file: .*/(\S+)\.md", log).group(1)
-hdr, body, raw = read_msg(D / "msgs" / "sent" / f"{iid}.md")
-note = body.split("## Note from the requester\n", 1)[1]
-note = note.split("\n## ", 1)[0].rstrip("\n")
-title = hdr.get("title")
-ti = [f"title as stored: {title!r} md5 {md5b(title.encode())} (protocol 5.1: 849fe21b104be883af9b3c06367d4445) match={md5b(title.encode()) == '849fe21b104be883af9b3c06367d4445'}",
-      f"note as stored: {len(note)} chars md5 {md5b(note.encode())} (protocol 5.1: 866 chars, 4cdbcb9b682f2f25dcb31c83d3743fec) match={len(note) == 866 and md5b(note.encode()) == '4cdbcb9b682f2f25dcb31c83d3743fec'}",
-      f"stored headers: {json.dumps(hdr, ensure_ascii=False)}"]
-(inj / "text-identity.txt").write_text("\n".join(ti) + "\n")
-w0, w1 = (S / "injection" / "window.txt").read_text().split()
-w0d, w1d = parse_ts(w0 + "Z"), parse_ts(w1 + "Z")
-o = [f"# window runs (protocol 5.4): runs that started in the injection window {w0}Z .. {w1}Z; injected task {iid}; revised (memo 1) task {mid}", ""]
-for r in runs:
-    if not (w0d <= r["dt"] <= w1d):
-        continue
-    se, ee = r["start_ev"], r["end_ev"]
-    o.append(f"## run {r['run_id']} agent={r['agent_dir']} model={r['model']} start={se and se['ts']} end={ee and ee['ts']} exit={r['exit']} secs={r['secs']} session={(r.get('session') or {}).get('id')}")
-    rpc = [e for e in rp if e.get("run") == r["run_id"]]
-    o.append(f"revise_playbook calls in this run (events): {len(rpc)}")
-    for e in rpc:
-        o.append(f"  {e['ts']} ok={e.get('ok')} error={e.get('error')} args={json.dumps(e.get('args'))}")
-    outp = r["text"].split("# ---- output ----", 1)[-1]
-    o.append(f"run-log P1 lines: {len(P1.findall(outp))}; P3 lines: {len(P3.findall(outp))}")
-    if r["agent_dir"] == "lead":
-        # lead's result messages sent in this run + its MEMORY.md change in this run's commit
-        t0, t1 = parse_ts(se["ts"]) if se else w0d, parse_ts(ee["ts"]) if ee else w1d
-        for f in sorted(glob.glob(str(D / "msgs" / "lead-sent" / "*.md"))):
-            h2, b2, _ = read_msg(f)
-            try:
-                cr = parse_ts(h2.get("created", ""))
-            except Exception:  # noqa: BLE001
+def hcalls(calls, *names):
+    """The assistant's MCP calls to hirearchy tools with these short names (e.g. 'feedback')."""
+    return [c for c in calls if c["tool"] and c["tool"].split("::")[-1] in names]
+
+
+# ---------------------------------------------------------------- the extract
+def run_extract(D: Path, S_arg: str, OUT: Path, product_src: str = PRODUCT_SRC) -> dict:
+    D = Path(D)
+    OUT = Path(OUT)
+    OUT.mkdir(parents=True, exist_ok=True)
+    S = Path(S_arg if S_arg != "-" else (D / "sandbox-path.txt").read_text().strip())
+    have_sandbox = S_arg != "-" and (S / "org").is_dir()
+    ORG = S / "org"
+    info = detect(D)
+    owner, owner_dir, service, seat_dir, seat_short = info["owner"], info["owner_dir"], info["service"], info["seat_dir"], info["seat_short"]
+    svc_dir = f"{owner}/services/{service}"
+    N = D.name
+
+    def git(*a: str) -> str:
+        if not have_sandbox:
+            return ""
+        return subprocess.run(["git", "-C", str(ORG), *a], capture_output=True, text=True).stdout
+
+    # ------------------------------------------------------------ assistant session -> calls
+    calls, turns = load_session(D)
+
+    tt = {}
+    for ln in open(D / "turn-times.txt"):
+        m = re.match(r"turn (\d+): (\S+) - (\S+)\s+\S+\s+utc (\S+) - (\S+)\s+exit (\d+)", ln)
+        if m:
+            tt[int(m.group(1))] = {"utc_start": m.group(4), "utc_end": m.group(5), "exit": m.group(6)}
+    for tr in turns:
+        tr.update(tt.get(tr["n"], {}))
+
+    # ------------------------------------------------------------ events
+    events = []
+    for f in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
+        for line in open(f):
+            e = json.loads(line)
+            e["_file"] = Path(f).name
+            events.append(e)
+    events.sort(key=lambda e: e["ts"])
+
+    # ------------------------------------------------------------ run logs
+    runs = []
+    for lg in sorted(glob.glob(str(D / "run-logs" / "*" / "*.log"))):
+        txt = Path(lg).read_text(errors="replace")
+        stamp = Path(lg).stem
+        agent_dir = Path(lg).parent.name
+        cwd = re.search(r"^# cwd: (.*)$", txt, re.M)
+        cmd = re.search(r"^# cmd: .*? --agent (\S+) --model (\S+)", txt, re.M)
+        ex = re.search(r"^# exit (\S+) after (\d+)s", txt, re.M)
+        runs.append({"stamp": stamp, "agent_dir": agent_dir, "path": lg, "cwd": cwd.group(1) if cwd else None,
+                     "agent_profile": cmd.group(1) if cmd else None, "model": cmd.group(2) if cmd else None,
+                     "exit": ex.group(1) if ex else None, "secs": int(ex.group(2)) if ex else None, "text": txt,
+                     "dt": stamp_to_dt(stamp)})
+    runs.sort(key=lambda r: r["stamp"])
+    for r in runs:
+        r["start_ev"] = next((e for e in events if e["kind"] == "run.start" and e.get("run", "").endswith("@" + r["stamp"])), None)
+        r["end_ev"] = next((e for e in events if e["kind"] == "run.end" and e.get("run", "").endswith("@" + r["stamp"])), None)
+        r["run_id"] = (r["start_ev"] or {}).get("run") or ("?@" + r["stamp"])
+
+    # ------------------------------------------------------------ org kiro home (A3.2)
+    first_cwd = runs[0]["cwd"] if runs else None
+    m = re.match(r"(.*)/kiro-cwd/([^/]+)/[^/]+$", first_cwd or "")
+    STATE, ORGID = (Path(m.group(1)), m.group(2)) if m else (None, None)
+    KH = STATE / "kiro-home" / ORGID if STATE else None
+    cwds = Counter(re.match(r"(.*/kiro-cwd/[^/]+)/", r["cwd"]).group(1) for r in runs if r["cwd"])
+    out = []
+    out.append(f"# run-session map (amendment 1 A3.2)\nstate dir: {STATE}\nfirst run log # cwd: {first_cwd}\nkiro home: {KH}")
+    out.append(f"every run log shows the same <state>/kiro-cwd/<org-id>/: {len(cwds) == 1} ({dict(cwds)})")
+    sess = []
+    kh_sessions = sorted(glob.glob(str(KH / "sessions" / "*" / "sess_*" / "session.json"))) if (KH and KH.is_dir()) else []
+    copied = bool(kh_sessions)
+    src_sessions = kh_sessions or sorted(glob.glob(str(D / "org-kiro-sessions" / "*" / "sess_*" / "session.json")))
+    for sj in src_sessions:
+        sd = Path(sj).parent
+        j = json.load(open(sj))
+        credits = 0.0
+        tool_calls = Counter()
+        try:
+            for line in open(sd / "messages.jsonl"):
+                p = payload(json.loads(line))
+                if p.get("type") == "usage_summary":
+                    for s in p.get("promptTurnSummaries") or []:
+                        credits += s.get("usage", 0) or 0
+                if p.get("type") == "tool_call":
+                    a = p.get("args") or {}
+                    tool_calls[a.get("tool_id") or p.get("toolName")] += 1
+        except FileNotFoundError:
+            pass
+        if copied:
+            dst = OUT / "org-kiro-sessions" / sd.parent.name / sd.name
+            dst.mkdir(parents=True, exist_ok=True)
+            shutil.copy2(sj, dst / "session.json")
+            if (sd / "messages.jsonl").exists():
+                shutil.copy2(sd / "messages.jsonl", dst / "messages.jsonl")
+        else:
+            dst = sd
+        sess.append({"id": j["id"], "hash": sd.parent.name, "cwd": (j.get("workspacePaths") or [None])[0], "mode": j.get("agentMode"),
+                     "model": j.get("modelId"), "created": j.get("createdAt"), "credits": credits, "dir": dst, "tools": tool_calls})
+    if copied:
+        out.append(f"org kiro sessions copied: {len(sess)} (to org-kiro-sessions/<hash>/<session id>/)")
+    else:
+        out.append(f"org kiro sessions read from the stream dir copy: {len(sess)} (org-kiro-sessions/<hash>/<session id>/)")
+    norm = lambda p: str(Path(p).resolve()) if p else p  # noqa: E731
+    unmatched_runs, used = [], set()
+    for r in runs:
+        cand = []
+        for s in sess:
+            if s["id"] in used:
                 continue
-            if t0 <= cr <= t1:
-                les = re.search(r"## Lessons\n(.*?)(?=\n## |\Z)", b2, re.S)
-                o.append(f"  lead message {h2.get('id')} to={h2.get('to')} type={h2.get('type')} status={h2.get('status')} created={h2.get('created')}\n  ## Lessons: {les.group(1).strip() if les else '(none)'}")
-        g = git("log", f"--grep={r['stamp']}", "--format=%h")
-        for h in g.split():
-            o.append(f"  org-git commit {h} MEMORY.md diff:\n" + "\n".join("    " + x for x in git("show", h, "--", "lead/MEMORY.md").splitlines()))
+            if norm(s["cwd"]) != norm(r["cwd"]) and s["cwd"] != r["cwd"]:
+                continue
+            if s["mode"] != r["agent_profile"] or s["model"] != r["model"]:
+                continue
+            a, b = r["start_ev"], r["end_ev"]
+            if a and b and not (parse_ts(a["ts"]) <= parse_ts(s["created"]) <= parse_ts(b["ts"])):
+                continue
+            cand.append(s)
+        if len(cand) == 1:
+            r["session"] = cand[0]
+            used.add(cand[0]["id"])
+        else:
+            r["session"] = None
+            unmatched_runs.append((r["stamp"], len(cand)))
+        out.append(f"run {r['run_id']:40s} {r['stamp']} model={r['model']} exit={r['exit']} secs={r['secs']} -> session "
+                   f"{(r['session'] or {}).get('id', 'NOT MATCHED (%d candidates)' % len(cand))} credits "
+                   f"{('%.6f' % r['session']['credits']) if r['session'] else 'not recorded'}")
+    out.append(f"unmatched runs: {unmatched_runs}; sessions without a run: {[s['id'] for s in sess if s['id'] not in used]}")
+    (OUT / "run-session-map.txt").write_text("\n".join(out) + "\n")
+
+    if have_sandbox and KH and KH.is_dir():  # org scheduler profiles (copied, not deleted: A3.2)
+        (OUT / "profiles").mkdir(exist_ok=True)
+        for f in glob.glob(str(KH / "agents" / "hirearchy-*.json")):
+            shutil.copy2(f, OUT / "profiles" / ("org-kiro-home--" + Path(f).name))
+
+    # ------------------------------------------------------------ revise-playbook-attempts.txt
+    o = ["# revise_playbook attempts (protocol 7.2; amendment 1 A3.3 10.1(c)); facts only", ""]
+    rp = [e for e in events if e["kind"] == "tool.call" and e.get("tool") == "revise_playbook"]
+    o.append(f"tool.call events with tool == revise_playbook: {len(rp)}")
+    for e in rp:
+        o.append(f"- {e['ts']} actor={e.get('actor')} run={e.get('run')} trace={e.get('trace')} ok={e.get('ok')} error_type={e.get('error_type')}\n  error (verbatim): {e.get('error')}\n  args: {json.dumps(e.get('args'), ensure_ascii=False)}")
     o.append("")
-(inj / "window-runs.txt").write_text("\n".join(o) + "\n")
+    P1 = re.compile(r"^\[tool\] @hirearchy/revise_playbook(?= |$)", re.M)
+    P2 = re.compile(r"^\[tool (?:ok|failed)\] @hirearchy/revise_playbook(?= |$)", re.M)
+    P3 = re.compile(r"^\[tool\] @hirearchy/\w+", re.M)
+    o.append("run-log patterns per run (after '# ---- output ----'): P1 revise_playbook call lines | P2 end lines | P3 all hirearchy call lines | tool.call events whose run is this run")
+    for r in runs:
+        outp = r["text"].split("# ---- output ----", 1)[-1]
+        ev_n = sum(1 for e in events if e["kind"] == "tool.call" and e.get("run") == r["run_id"])
+        ev_rp = sum(1 for e in rp if e.get("run") == r["run_id"])
+        p1, p2, p3 = len(P1.findall(outp)), len(P2.findall(outp)), len(P3.findall(outp))
+        flag = "" if (p1 == ev_rp and p3 == ev_n) else "   <-- MISMATCH between run-log lines and events"
+        o.append(f"  {r['run_id']:44s} P1={p1} P2={p2} P3={p3} events(all)={ev_n} events(revise_playbook)={ev_rp}{flag}")
+        for ln in re.findall(r"^\[tool(?: ok| failed)?\] @hirearchy/revise_playbook.*$", outp, re.M):
+            o.append(f"      {ln[:400]}")
+    o.append("")
+    o.append("full arguments and result verbatim, from the org-run session (tool_call with args.tool_id == hirearchy::revise_playbook):")
+    for r in runs:
+        s = r.get("session")
+        if not s:
+            continue
+        byc = {}
+        for line in open(s["dir"] / "messages.jsonl"):
+            p = payload(json.loads(line))
+            if p.get("type") == "tool_call" and (p.get("args") or {}).get("tool_id") == "hirearchy::revise_playbook":
+                byc[p["toolCallId"]] = {"args": p["args"], "res": None}
+                byc[p["toolCallId"]]["ts"] = json.loads(line).get("timestamp")
+            elif p.get("type") == "tool_result" and p.get("toolCallId") in byc:
+                c = p.get("content")
+                byc[p["toolCallId"]]["res"] = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
+        for cid, v in byc.items():
+            o.append(f"--- run {r['run_id']} session {s['id']} call {cid} at {v['ts']}\nARGUMENTS: {json.dumps(v['args'], ensure_ascii=False, indent=1)}\nRESULT: {v['res']}")
+    o.append("")
+    o.append("service.revise events:")
+    for e in events:
+        if e["kind"] == "service.revise":
+            o.append(f"- {e['ts']} {json.dumps({k: v for k, v in e.items() if k not in ('v', 'seq', '_file')}, ensure_ascii=False)}")
+    o.append("")
+    o.append(f"PLAYBOOK versions (org git history of {svc_dir}/PLAYBOOK.md and history/):")
+    if have_sandbox:
+        o.append(git("log", "--reverse", "--format=%h %cI %s", "--", f"{svc_dir}/PLAYBOOK.md", f"{svc_dir}/history").strip())
+        hist = sorted(glob.glob(str(ORG / svc_dir / "history" / "*")))
+        hist_names = [Path(h).name for h in hist]
+    else:
+        o.append(playbook_versions_from_evidence(D))
+        hist_names = sorted(Path(h).name[len("history--"):] for h in glob.glob(str(D / "playbook" / "history--*")))
+    o.append("history files now: " + ", ".join(hist_names))
+    if have_sandbox:
+        (OUT / "playbook").mkdir(exist_ok=True)
+        (OUT / "service").mkdir(exist_ok=True)
+        for h in hist:
+            shutil.copy2(h, OUT / "playbook" / ("history--" + Path(h).name))
+        for h in glob.glob(str(ORG / svc_dir / "history" / "SERVICE.v*.md")):
+            shutil.copy2(h, OUT / "service" / ("history--" + Path(h).name))
+        shutil.copy2(ORG / svc_dir / "SERVICE.md", OUT / "service" / "current-SERVICE.md")
+        shutil.copy2(ORG / svc_dir / "PLAYBOOK.md", OUT / "playbook" / "current-PLAYBOOK.md")
+    (OUT / "revise-playbook-attempts.txt").write_text("\n".join(o) + "\n")
 
-# ---------------------------------------------------------------- run-counts.txt and cost.txt
-rc = subprocess.run(["python3", str(EV / "harness" / "org_state.py"), str(S), "final"], capture_output=True, text=True).stdout
-per_turn = []
-for r in runs:
-    per_turn.append((r["stamp"], r["agent_dir"], r["model"], r["secs"]))
-o = [rc]
-o.append("\nruns per user-turn window (UTC turn_start .. next turn_start / end):")
-bounds = [(tr["n"], parse_ts(tr["utc_start"]) if tr.get("utc_start") else None) for tr in turns]
-cnt = defaultdict(list)
-for r in runs:
-    k = 0
-    for n, st in bounds:
-        if st and r["dt"] >= st:
-            k = n
-    cnt[k].append(r)
-for k in sorted(cnt):
-    o.append(f"  during/after turn {k} start: {len(cnt[k])} runs, " + ", ".join(sorted(f"{x['agent_dir']}={x['model']}" for x in cnt[k]))[:300])
-(D / "run-counts.txt").write_text("\n".join(o) + "\n")
+    # ------------------------------------------------------------ client-questions.txt
+    sys.dont_write_bytecode = True
+    if product_src not in sys.path:
+        sys.path.insert(0, product_src)
+    from hirearchy.kernel._text import client_questions  # noqa: E402  (the one product import: read-only, stated in the docstring)
 
-c = ["# s%s cost; facts only" % N, ""]
-tot = 0.0
-for ln in (D / "session-turn-times-utc.txt").read_text().splitlines():
-    c.append(ln)
-c.append("")
-c.append("Assistant seconds per turn (turn-times.txt wall clock):")
-c.append((D / "turn-times.txt").read_text())
-c.append("Org runs by agent and model; seconds from '# exit N after Ns'; injection window apart:")
-by = defaultdict(lambda: [0, 0, 0.0])
-byw = defaultdict(lambda: [0, 0, 0.0])
-for r in runs:
-    tgt = byw if (w0d <= r["dt"] <= w1d) else by
-    k = (r["agent_dir"], r["model"])
-    tgt[k][0] += 1
-    tgt[k][1] += r["secs"] or 0
-    tgt[k][2] += (r["session"]["credits"] if r.get("session") else 0.0)
-for label, dct in (("outside the injection window (counted toward the 45 cap)", by), ("injection window", byw)):
-    c.append(f"  {label}:")
-    for k, v in sorted(dct.items()):
-        c.append(f"    {k[0]:14s} {k[1]:20s} runs {v[0]:3d} secs {v[1]:5d} credits {v[2]:.4f}")
-    c.append(f"    total runs {sum(v[0] for v in dct.values())} secs {sum(v[1] for v in dct.values())} credits {sum(v[2] for v in dct.values()):.4f}")
-c.append(f"org-run credits are read from each run's kiro session (usage_summary); runs without a matched session: {len(unmatched_runs)}")
-c.append(f"  per-model credits (all runs): " + str({m: round(sum(r['session']['credits'] for r in runs if r.get('session') and r['model'] == m), 4) for m in sorted({r['model'] for r in runs})}))
-(D / "cost.txt").write_text("\n".join(c) + "\n")
-print(f"runs {len(runs)}, sessions {len(sess)}, matched {len(used)}, unmatched runs {len(unmatched_runs)}, revise_playbook events {len(rp)}, flags {n_flag}, calls {len(calls)}")
+    o = ["# client questions (protocol 7.2); facts only", ""]
+    o.append("Result messages root received (lead -> root), with the product parser's items (hirearchy.kernel._text.client_questions):")
+    for d in ("inbox", "read"):
+        for f in sorted(glob.glob(str(D / "msgs" / d / "*.md"))):
+            hdr, body, raw = read_msg(f)
+            if hdr.get("to") != "root" or hdr.get("type") != "result":
+                continue
+            raw_q = ""
+            mm = re.search(r"(?im)^.*questions for the client.*$", body)
+            if mm:
+                raw_q = body[mm.start():]
+                raw_q = raw_q.split("\n## ", 1)[0]
+            items = client_questions(body)
+            o.append(f"- id {hdr.get('id')} folder={d} created={hdr.get('created')} answers(reply_to)={hdr.get('reply_to')} status={hdr.get('status')} from={hdr.get('from')}\n"
+                     f"  raw 'Questions for the client' text: {raw_q.strip() if raw_q else '(none)'}\n  parsed items ({len(items)}): {items}")
+    o.append("")
+    FLAG = "for the client: ask the user before you copy or deliver"
+    o.append(f"progress replies the assistant received that contain {FLAG!r}:")
+    n_flag = 0
+    for c in calls:
+        if c["result"] and FLAG in c["result"]:
+            n_flag += 1
+            lines = [ln for ln in c["result"].splitlines() if FLAG in ln]
+            o.append(f"- call #{c['n']} {c['ts']} turn {c['turn']} {c['tool']}: {lines}")
+    o.append(f"count: {n_flag}")
+    (OUT / "client-questions.txt").write_text("\n".join(o) + "\n")
+
+    # ------------------------------------------------------------ contract-loop.txt
+    o = ["# contract loop (protocol 7.2); facts only, time order", ""]
+    o.append("Lena reject turns (D1 candidates: turns whose line starts with 'No, not right yet' / 'Not right yet' / 'Almost'):")
+    lena = {}
+    for ln in (D / "lena-lines.txt").read_text().splitlines():
+        m = re.match(r"turn (\d+) \| (.*)", ln)
+        if m:
+            lena[int(m.group(1))] = m.group(2)
+    for n in sorted(lena):
+        prompt = (D / f"turn-{n:02d}.prompt.txt").read_text()
+        if re.match(r"(No, not right yet|Not right yet|Almost)", prompt):
+            tr = turns[n - 1]
+            o.append(f"- turn {n}: script UTC {tr.get('utc_start')} - {tr.get('utc_end')}; session turn_start {tr.get('start')} turn_end {tr.get('end')}; line: {prompt}")
+    o.append("")
+    o.append("assistant calls to feedback, define_service, request, services (full arguments and replies):")
+    for c in calls:
+        if c["tool"] and c["tool"].split("::")[-1] in ("feedback", "define_service", "request", "services"):
+            o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} {c['tool']} status={c['status']}\nARGS: {json.dumps(c['args'], ensure_ascii=False)}\nREPLY ({c['rts']}): {c['result']}\n")
+    o.append("root notes in S/org/sent with a feedback: or criterion: header:")
+    for f in sorted(glob.glob(str(D / "msgs" / "sent" / "*.md"))):
+        hdr, body, raw = read_msg(f)
+        if "feedback" in hdr or "criterion" in hdr:
+            o.append(f"--- {Path(f).name} id={hdr.get('id')} created={hdr.get('created')}\nheaders: {json.dumps(hdr, ensure_ascii=False)}\nbody:\n{body.strip()}\n")
+    (OUT / "contract-loop.txt").write_text("\n".join(o) + "\n")
+
+    # ------------------------------------------------------------ deliverables-log.txt and shell-writes.txt
+    DELIV = str(S / "deliverables")
+    DELIV2 = DELIV.replace("/tmp/", "/private/tmp/", 1)
+    variants = (DELIV, DELIV2)
+    index_rows = index_from_evidence(D)
+    o = ["# deliverables log (protocol 7.2, D6); facts only", ""]
+    sw = ["# shell writes (protocol 7.2): every execute_bash call of the assistant; facts only", ""]
+    for c in calls:
+        nm = c["name"]
+        if nm == "execute_bash":
+            cmd = c["args"].get("command", "")
+            flags, wrote = shell_flags(cmd, S, variants)
+            sw.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} status={c['status']} flags={flags or ['none']}\nCOMMAND: {cmd}\nRESULT: {(c['result'] or '')[:1500]}\n")
+            if "writes into the deliverable folder" in flags:
+                src = source_paths(cmd)
+                src_info = []
+                for sp in src:
+                    rel = sp.split("/org/", 1)[-1] if "/org/" in sp else sp[len("org/"):]
+                    if have_sandbox:
+                        g = git("log", f"--until={c['ts']}", "-1", "--format=%h %cI", "--", rel).strip()
+                    else:
+                        g = commit_at(index_rows, rel, c["ts"])
+                    src_info.append(f"{rel} -> org-git commit at that time: {g or '(none)'}")
+                o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} execute_bash\nCOMMAND: {cmd}\nsource file(s): {src_info or 'not found in the command'}\nresult: {(c['result'] or '')[:600]}\n")
+        elif nm and re.search(r"write|create|append|edit|replace", nm) and "hirearchy" not in (c.get("tool") or ""):
+            path = c["args"].get("path") or c["args"].get("file_path") or ""
+            if "deliverables" in str(path) or "deliverables" in json.dumps(c["args"]):
+                o.append(f"[{c['ts']}] call #{c['n']} turn {c['turn']} {nm} (file-write tool) args={json.dumps(c['args'], ensure_ascii=False)[:800]}\n")
+    o.append("any other write into the deliverable folder (not by the assistant): none can be seen from the assistant session; the folder holds:")
+    if have_sandbox and (S / "deliverables").is_dir():
+        listing = sorted((S / "deliverables").glob("*"))
+    else:
+        listing = sorted((D / "memos").glob("*.md")) if (D / "memos").is_dir() else []
+    for p in listing:
+        st = p.stat()
+        o.append(f"  {p.name} size {st.st_size} mtime {datetime.fromtimestamp(st.st_mtime).strftime('%H:%M:%S')} local md5 {md5b(p.read_bytes())}")
+    o.append("")
+    if have_sandbox and (S / "deliverables").is_dir():
+        o.append("final ls -la:\n" + subprocess.run(["ls", "-la", str(S / "deliverables")], capture_output=True, text=True).stdout)
+    else:
+        o.append("final ls -la:\n(no sandbox: the listing above is of the stream dir's memos/ copy)\n")
+    (OUT / "deliverables-log.txt").write_text("\n".join(o) + "\n")
+    (OUT / "shell-writes.txt").write_text("\n".join(sw) + "\n")
+
+    # ------------------------------------------------------------ lead-prompt-sizes, reflect-sections, regression-list
+    (OUT / "reflect-sections").mkdir(exist_ok=True)
+    (OUT / "regression-list").mkdir(exist_ok=True)
+    o = ["# lead prompt sizes (protocol 7.2): bytes between '# ---- prompt ----' and '# ---- output ----'", ""]
+    for r in runs:
+        if r["agent_dir"] != owner_dir:
+            continue
+        txt = r["text"]
+        pr = txt.split("# ---- prompt ----\n", 1)[1].split("# ---- output ----", 1)[0]
+        size = len(pr.encode())
+        refl = re.search(r"^# Reflect before you start:.*?(?=^# (?!Reflect)|\Z)", pr, re.M | re.S)
+        reg = re.search(r"^# Regression list:.*?(?=^# (?!Regression)|\Z)", pr, re.M | re.S)
+        words = len(refl.group(0).split()) if refl else 0
+        o.append(f"{r['run_id']:30s} bytes={size} reflect_section={'yes' if refl else 'no'} reflect_words={words} regression_list={'yes' if reg else 'no'}")
+        if refl:
+            (OUT / "reflect-sections" / f"{owner_dir}-{r['stamp']}.txt").write_text(refl.group(0))
+        if reg:
+            (OUT / "regression-list" / f"{owner_dir}-{r['stamp']}.txt").write_text(reg.group(0))
+    if seat_dir:
+        for f in sorted(glob.glob(str(D / "msgs" / f"{seat_dir}-*" / "*.md"))):
+            hdr, body, raw = read_msg(f)
+            if "Regression list" in body:
+                i = body.index("Regression list")
+                (OUT / "regression-list" / f"{seat_short}-task-{Path(f).name}").write_text(body[i - 2:i + 3000])
+    (OUT / "lead-prompt-sizes.txt").write_text("\n".join(o) + "\n")
+
+    # ------------------------------------------------------------ memos/versions (sandbox only; copy_org_evidence.sh makes it in G0)
+    if have_sandbox:
+        (OUT / "memos" / "versions").mkdir(parents=True, exist_ok=True)
+        seat_path = seat_dir.replace("-", "/") if seat_dir else None
+        files = [x for x in git("ls-files", f"{owner}").split()
+                 if x.endswith(".md") and "/work/" in x and not (seat_path and x.startswith(seat_path + "/"))]
+        vlog = []
+        for fpath in files:
+            hs = git("log", "--reverse", "--format=%h %cI", "--", fpath).strip().splitlines()
+            for i, ln in enumerate(hs, 1):
+                h, t = ln.split(" ", 1)
+                body = git("show", f"{h}:{fpath}")
+                (OUT / "memos" / "versions" / f"{Path(fpath).stem}.v{i}.{h}.md").write_text(body)
+                vlog.append(f"{fpath} v{i} {h} {t} md5 {md5b(body.encode())}")
+            cur = ORG / fpath
+            if cur.exists():
+                vlog.append(f"{fpath} working tree md5 {md5b(cur.read_bytes())} (committed head: {md5b(git('show', 'HEAD:' + fpath).encode())})")
+        (OUT / "memos" / "versions" / "INDEX.txt").write_text("\n".join(vlog) + "\n")
+
+    # ------------------------------------------------------------ cost.txt
+    w0d = w1d = None
+    wf = D / "injection" / "window.txt"
+    if wf.exists() and len(wf.read_text().split()) >= 2:
+        w0, w1 = wf.read_text().split()[:2]
+        w0d, w1d = parse_ts(w0 + "Z"), parse_ts(w1 + "Z")
+    c = ["# %s cost; facts only" % N, ""]
+    for ln in (D / "session-turn-times-utc.txt").read_text().splitlines():
+        c.append(ln)
+    c.append("")
+    c.append("Assistant seconds per turn (turn-times.txt wall clock):")
+    c.append((D / "turn-times.txt").read_text())
+    c.append("Org runs by agent and model; seconds from '# exit N after Ns'; injection window apart:")
+    by = defaultdict(lambda: [0, 0, 0.0])
+    byw = defaultdict(lambda: [0, 0, 0.0])
+    for r in runs:
+        tgt = byw if (w0d and w0d <= r["dt"] <= w1d) else by
+        k = (r["agent_dir"], r["model"])
+        tgt[k][0] += 1
+        tgt[k][1] += r["secs"] or 0
+        tgt[k][2] += (r["session"]["credits"] if r.get("session") else 0.0)
+    for label, dct in (("outside the injection window (counted toward the 45 cap)", by), ("injection window", byw)):
+        c.append(f"  {label}:")
+        for k, v in sorted(dct.items()):
+            c.append(f"    {k[0]:14s} {k[1]:20s} runs {v[0]:3d} secs {v[1]:5d} credits {v[2]:.4f}")
+        c.append(f"    total runs {sum(v[0] for v in dct.values())} secs {sum(v[1] for v in dct.values())} credits {sum(v[2] for v in dct.values()):.4f}")
+    c.append(f"org-run credits are read from each run's kiro session (usage_summary); runs without a matched session: {len(unmatched_runs)}")
+    c.append("  per-model credits (all runs): " + str({m: round(sum(r['session']['credits'] for r in runs if r.get('session') and r['model'] == m), 4) for m in sorted({r['model'] for r in runs})}))
+    (OUT / "cost.txt").write_text("\n".join(c) + "\n")
+    return {"runs": len(runs), "sessions": len(sess), "matched": len(used), "unmatched": len(unmatched_runs),
+            "revise_playbook": len(rp), "flags": n_flag, "calls": len(calls), "sandbox": have_sandbox,
+            "owner": owner, "service": service, "seat": seat_dir}
+
+
+# ---------------------------------------------------------------- evidence-only replacements for the org's git
+def index_from_evidence(D: Path):
+    """Rows of memos/versions/INDEX.txt: (path, version, sha, time) for every committed version; [] when absent."""
+    rows = []
+    f = Path(D) / "memos" / "versions" / "INDEX.txt"
+    if f.exists():
+        for ln in f.read_text().splitlines():
+            m = re.match(r"(\S+) v(\d+) (\w+) (\S+) md5 (\w+)", ln)
+            if m:
+                rows.append((m.group(1), int(m.group(2)), m.group(3), m.group(4)))
+    return rows
+
+
+def commit_at(rows, rel: str, ts: str) -> str:
+    """`git log --until=<ts> -1 --format='%h %cI' -- rel` from INDEX.txt: the last version of `rel` committed at or before `ts`."""
+    t = parse_ts(ts)
+    best = ""
+    for path, _v, sha, ctime in rows:
+        if path == rel and parse_ts(ctime) <= t:
+            best = f"{sha} {ctime}"
+    return best
+
+
+def playbook_versions_from_evidence(D: Path) -> str:
+    """`git log --reverse --format='%h %cI %s'` of the playbook, from playbook/versions.txt ('<sha> <time>') and the subjects in org-git-log.txt."""
+    D = Path(D)
+    vf = D / "playbook" / "versions.txt"
+    if not vf.exists():
+        return ""
+    subjects = {}
+    gl = D / "org-git-log.txt"
+    if gl.exists():
+        cur = None
+        want_subject = False
+        for ln in gl.read_text(errors="replace").splitlines():
+            m = re.match(r"commit (\w{40})", ln)
+            if m:
+                cur, want_subject = m.group(1), False
+                continue
+            if cur and ln.startswith("Date:"):
+                want_subject = True
+                continue
+            if cur and want_subject and ln.strip():
+                subjects[cur] = ln.strip()
+                want_subject = False
+    out = []
+    for ln in vf.read_text().splitlines():
+        parts = ln.split()
+        if len(parts) < 2:
+            continue
+        sha, t = parts[0], parts[1]
+        subj = next((s for full, s in subjects.items() if full.startswith(sha)), "")
+        out.append(f"{sha} {t} {subj}".rstrip())
+    return "\n".join(out)
+
+
+def main(argv):
+    args = list(argv)
+    out = product_src = None
+    for flag in ("--out", "--product-src"):
+        if flag in args:
+            i = args.index(flag)
+            val = args[i + 1]
+            del args[i:i + 2]
+            if flag == "--out":
+                out = val
+            else:
+                product_src = val
+    if len(args) != 2:
+        print(__doc__)
+        return 2
+    D, S = Path(args[0]), args[1]
+    if not (D / "assistant-session-messages.jsonl").exists():
+        print(f"not a stream evidence dir: {D}", file=sys.stderr)
+        return 2
+    res = run_extract(D, S, Path(out) if out else D, product_src or PRODUCT_SRC)
+    print(f"runs {res['runs']}, sessions {res['sessions']}, matched {res['matched']}, unmatched runs {res['unmatched']}, "
+          f"revise_playbook events {res['revise_playbook']}, flags {res['flags']}, calls {res['calls']}")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv[1:]))
```

### `scheduler_survival.py` (from `s1/harness/scheduler_survival.py`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s1/harness/scheduler_survival.py	2026-10-25 07:37:02
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/scheduler_survival.py	2026-10-26 04:03:58
@@ -1,135 +1,357 @@
 #!/usr/bin/env python3
-"""E7 s1 facilitator extract (facts only; protocol 6, 7.2, D-SURVIVE and D-SIGNAL; E6 s1's extract with the signal listing added). Reads s1/events/*/ and s1/session-turn-times-utc.txt and
-s1/injection/injection-log.txt (read-only) and writes s1/scheduler-survival.txt (E7: also every scheduler.signal). Usage: scheduler_survival.py <stream dir>"""
+"""G0 scheduler survival: D-SURVIVE, D-SIGNAL and M-C-8 of one stream (E7 protocol 9 and 10.10; facts only).
+Generalized from E7's `s1|s2|s3/harness/scheduler_survival.py` (the three copies differ only in the stream number in two header lines).
+
+What changed against E7's script (and why):
+  * the starter of a scheduler is the `start` tool.call event, in an `mcp-<pid>-*.jsonl` file, whose INTERVAL [ts - ms/1000, ts] holds the
+    `scheduler.start` (E7 STUDY Interpretation 18). E7's extract picked the first `start` call within 5 s either side; the event is written
+    3-55 ms after the `scheduler.start`, so the rule "the last start call before it" that E7's header stated would credit the previous call.
+    The header now says what the rule is (E7 STUDY Correction 9). "injection script" when injection-log.txt says `scheduler started (pid <pid>;`.
+  * D-SURVIVE as E7's protocol extends it (E7 item 5): a scheduler counts as running at a turn's end also when a `stopped by SIGTERM`/`SIGHUP`
+    exit or an unexplained `scheduler.signal` falls within 5 s before that `turn_end`; every (turn end, scheduler) pair is classed
+    `survived` / `died with the call` / `died later` / `error`; M-C-1, M-C-2, M-C-4, M-C-6, M-C-7 are computed; M-C-8 is computed from
+    turn-times.txt (`sleep 20 ended` at least 20 s after the chat's end) and `harness-failures/boundary-turn-*.txt`.
+  * a label in the header instead of a fixed stream name; the stream dir is the only input; `--out` for the outputs.
+
+Usage:  python3 -B scheduler_survival.py <streamdir> [--out DIR]
+Reads (read-only): events/*/*.jsonl, session-turn-times-utc.txt, turn-times.txt, injection/injection-log.txt, harness-failures/.
+Writes: <out>/scheduler-survival.txt (the E7 text, default out = the stream dir) and <out>/scheduler_survival.json (sorted keys, with
+source_files and script name+md5)."""
 import glob
+import hashlib
 import json
 import re
 import sys
 from datetime import datetime, timedelta
 from pathlib import Path
 
-D = Path(sys.argv[1])
+sys.dont_write_bytecode = True
 
+SELF_EXIT_BAD = ("stopped by SIGTERM", "stopped by SIGHUP", "interrupted (KeyboardInterrupt)")
 
+
 def ts(s):
     return datetime.fromisoformat(s.replace("Z", "+00:00"))
 
 
-ev = []
-for p in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
-    name = Path(p).name
-    for ln in open(p):
-        try:
-            d = json.loads(ln)
-        except Exception:
-            continue
-        d["_file"] = name
-        ev.append(d)
-ev.sort(key=lambda d: d["ts"])
+def rate(r):
+    return "n/a (0 of 0)" if r["n"] == 0 else f"{r['k']} of {r['n']}"
 
-turn_end = {}
-for ln in open(D / "session-turn-times-utc.txt"):
-    m = re.match(r"turn (\d+): .* turn_end (\S+)", ln)
-    if m:
-        turn_end[int(m.group(1))] = ts(m.group(2))
-turn_start = {}
-for ln in open(D / "session-turn-times-utc.txt"):
-    m = re.match(r"turn (\d+): .* turn_start (\S+)", ln)
-    if m:
-        turn_start[int(m.group(1))] = ts(m.group(2))
 
-stops = [d for d in ev if d["kind"] == "tool.call" and d.get("tool") == "stop"]
-inj = (D / "injection" / "injection-log.txt").read_text() if (D / "injection" / "injection-log.txt").exists() else ""
-inj_stop = bool(re.search(r"--- stop at", inj))
-mcp_files = {d["_file"]: d["pid"] for d in ev if d["_file"].startswith("mcp-")}
+def _is_stop_reason(reason):
+    return bool(reason) and (reason.startswith("stopped by SIG") or reason.startswith("interrupted"))
 
-out = []
-w = out.append
-w("# E7 s1 scheduler survival (D-SURVIVE and D-SIGNAL; facts only, from events/, session-turn-times-utc.txt, injection-log.txt)")
-w("Per scheduler: pid, who started it (the last `start` tool.call before its scheduler.start whose mcp file/pid is the assistant's per-turn server, or the injection script's), its start/exit,")
-w("the turn it began in, whether it was running at any turn's end, runs in flight at a turn's end, and kills/stops.")
-w("")
-scheds = [d for d in ev if d["kind"] == "scheduler.start"]
-exits = {d["pid"]: d for d in ev if d["kind"] == "scheduler.exit"}
-running_pairs = []
-n_ass = n_inj = 0
-for s in scheds:
-    pid = s["pid"]
-    st = ts(s["ts"])
-    # starter: the 'start' tool.call at the closest time (within 5 s) from an mcp process
-    cands = [d for d in ev if d["kind"] == "tool.call" and d.get("tool") == "start" and d["_file"].startswith("mcp-")
-             and abs((ts(d["ts"]) - st).total_seconds()) < 5]
-    starter = cands[0] if cands else None
-    who = "unknown"
-    if starter:
-        in_inj = f"injection script" if re.search(rf"scheduler started \(pid {pid};", inj) else "assistant's MCP server"
-        who = f"{in_inj} (mcp pid {starter['pid']}, file {starter['_file']}, start tool.call at {starter['ts']})"
-    turn_in = next((t for t in sorted(turn_start) if turn_start[t] <= st <= turn_end[t] + timedelta(seconds=1)), None)
-    if "injection script" in who: n_inj += 1
-    elif "assistant" in who: n_ass += 1
-    ex = exits.get(pid)
-    w(f"scheduler pid {pid}: scheduler.start {s['ts']}; starter: {who}; began in assistant turn: {turn_in if turn_in else 'none (between turns: the injection window)'}")
-    if ex:
-        w(f"  scheduler.exit {ex['ts']} reason={ex.get('reason')!r}")
-    else:
-        w("  scheduler.exit: NONE")
-    runs = [d for d in ev if d["kind"] in ("run.start", "run.end") and d["pid"] == pid]
-    starts = {d["run"]: d for d in runs if d["kind"] == "run.start"}
-    ends = {d["run"]: d for d in runs if d["kind"] == "run.end"}
-    killed = [r for r, d in ends.items() if d.get("killed")]
-    w(f"  runs: {len(starts)} run.start, {len(ends)} run.end; run.end with killed=true: {len(killed)}; run.start without run.end: {[r for r in starts if r not in ends]}")
-    # running at any turn end?
-    pairs = []
-    for t, te in sorted(turn_end.items()):
-        running = st < te and (not ex or ts(ex["ts"]) >= te)
-        if running:
+
+def analyse(D: Path) -> dict:
+    D = Path(D)
+    sources = []
+    ev = []
+    for p in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
+        name = Path(p).name
+        sources.append(str(Path(p).relative_to(D)))
+        for ln in open(p):
+            try:
+                d = json.loads(ln)
+            except Exception:  # noqa: BLE001
+                continue
+            d["_file"] = name
+            ev.append(d)
+    ev.sort(key=lambda d: d["ts"])
+
+    sources.append("session-turn-times-utc.txt")
+    turn_end, turn_start = {}, {}
+    for ln in open(D / "session-turn-times-utc.txt"):
+        m = re.match(r"turn (\d+): .* turn_end (\S+)", ln)
+        if m:
+            turn_end[int(m.group(1))] = ts(m.group(2))
+        m = re.match(r"turn (\d+): .* turn_start (\S+)", ln)
+        if m:
+            turn_start[int(m.group(1))] = ts(m.group(2))
+
+    stops = [d for d in ev if d["kind"] == "tool.call" and d.get("tool") == "stop"]
+    inj_f = D / "injection" / "injection-log.txt"
+    inj = inj_f.read_text() if inj_f.exists() else ""
+    if inj_f.exists():
+        sources.append("injection/injection-log.txt")
+    inj_stop = bool(re.search(r"--- stop at", inj))
+    inj_stop_times = []
+    for m in re.finditer(r"--- stop at (\S+)", inj):
+        try:
+            inj_stop_times.append(ts(m.group(1)))
+        except ValueError:
+            pass
+
+    def stop_before(t, window=30):
+        """A recorded stop at most `window` s before time t: an assistant `stop` tool.call, or the injection script's --stop."""
+        if any(0 <= (t - ts(d["ts"])).total_seconds() <= window for d in stops):
+            return True
+        if any(0 <= (t - x).total_seconds() <= window for x in inj_stop_times):
+            return True
+        return inj_stop and not inj_stop_times  # a --stop line without a parsable time: E7's reading (any --stop explains)
+
+    scheds_ev = [d for d in ev if d["kind"] == "scheduler.start"]
+    exits = {d["pid"]: d for d in ev if d["kind"] == "scheduler.exit"}
+    sigs = [d for d in ev if d["kind"] == "scheduler.signal"]
+    schedulers = []
+    n_ass = n_inj = 0
+    for s in scheds_ev:
+        pid = s["pid"]
+        st = ts(s["ts"])
+        # starter: the `start` tool.call (mcp file) whose interval [ts - ms, ts] holds the scheduler.start (E7 STUDY Interpretation 18)
+        cands = []
+        for d in ev:
+            if d["kind"] == "tool.call" and d.get("tool") == "start" and d["_file"].startswith("mcp-"):
+                end = ts(d["ts"])
+                begin = end - timedelta(milliseconds=float(d.get("ms") or 0))
+                if begin <= st <= end:
+                    cands.append((end - st, d))
+        starter = min(cands, key=lambda x: x[0])[1] if cands else None
+        if starter:
+            kind = "script" if re.search(rf"scheduler started \(pid {pid};", inj) else "assistant"
+            starter_d = {"kind": kind, "mcp_pid": starter["pid"], "file": starter["_file"], "tool_call_ts": starter["ts"]}
+        else:
+            starter_d = {"kind": "unknown", "mcp_pid": None, "file": None, "tool_call_ts": None}
+        turn_in = next((t for t in sorted(turn_start) if t in turn_end and turn_start[t] <= st <= turn_end[t] + timedelta(seconds=1)), None)
+        if starter_d["kind"] == "script":
+            n_inj += 1
+        elif starter_d["kind"] == "assistant":
+            n_ass += 1
+        ex = exits.get(pid)
+        runs = [d for d in ev if d["kind"] in ("run.start", "run.end") and d["pid"] == pid]
+        starts = {d["run"]: d for d in runs if d["kind"] == "run.start"}
+        ends = {d["run"]: d for d in runs if d["kind"] == "run.end"}
+        killed = [r for r, d in ends.items() if d.get("killed")]
+        my_sigs = [g for g in sigs if g["pid"] == pid]
+        pairs = []
+        for t, te in sorted(turn_end.items()):
+            exit_t = ts(ex["ts"]) if ex else None
+            running = st < te and (not ex or exit_t >= te)
+            ext = False
+            if not running and ex and st < te and _is_stop_reason(ex.get("reason")) and 0 < (te - exit_t).total_seconds() <= 5 \
+                    and not stop_before(exit_t):
+                running = ext = True  # D-SURVIVE signal extension (1): a TERM/HUP exit in the last 5 s before the turn's end
+            if not running and st < te:
+                for g in my_sigs:
+                    if 0 < (te - ts(g["ts"])).total_seconds() <= 5 and not stop_before(ts(g["ts"])):
+                        running = ext = True
+                        break
+            if not running:
+                continue
             inflight = [r for r, d in starts.items() if ts(d["ts"]) < te and (r not in ends or ts(ends[r]["ts"]) >= te)]
-            pairs.append((t, inflight))
-    if pairs:
-        for t, infl in pairs:
-            w(f"  RUNNING at the end of turn {t} ({turn_end[t].isoformat()}); runs in flight: {infl}")
-            running_pairs.append((pid, t, infl, ex))
-    else:
-        w("  not running at the end of any assistant turn (scheduler.exit came before the turn_end of the turn it began in, or it ran between turns)")
-    nearest = [(t, (turn_end[t] - ts(ex['ts'])).total_seconds()) for t in sorted(turn_end) if ex and turn_end[t] >= ts(ex['ts'])][:1]
-    if nearest:
-        t, dt = nearest[0]
-        w(f"  scheduler.exit to the next turn_end (turn {t}): {dt:.1f} s")
+            pairs.append({"turn": t, "turn_end": te.isoformat(), "in_flight": inflight, "extension": ext,
+                          "scheduler_exit_reason": ex.get("reason") if ex else None, "survived": None, "class": None, "runs": []})
+        for pr in pairs:
+            te = turn_end[pr["turn"]]
+            cls = _classify(ex, pr, te, ends, my_sigs, stop_before)
+            pr["class"] = cls
+            pr["survived"] = cls == "survived"
+            for r in pr["in_flight"]:
+                e = ends.get(r)
+                pr["runs"].append({"run": r, "run_end": e["ts"] if e else None, "ok": e.get("ok") if e else None,
+                                   "killed": bool(e.get("killed")) if e else None,
+                                   "kill_ok": bool(e) and not e.get("killed") or bool(e and e.get("killed") and stop_before(ts(e["ts"])))})
+        nearest = [(t, (turn_end[t] - ts(ex['ts'])).total_seconds()) for t in sorted(turn_end) if ex and turn_end[t] >= ts(ex['ts'])][:1]
+        schedulers.append({
+            "pid": pid, "start_ts": s["ts"], "starter": starter_d, "began_in_turn": turn_in,
+            "exit": {"ts": ex["ts"], "reason": ex.get("reason")} if ex else None,
+            "runs": {"run_start": len(starts), "run_end": len(ends), "run_end_killed": len(killed),
+                     "start_without_end": [r for r in starts if r not in ends]},
+            "running_at_turn_ends": pairs,
+            "exit_to_next_turn_end": list(nearest[0]) if nearest else None,
+        })
+
+    # ---- signals (D-SIGNAL)
+    signals = []
+    for g in sigs:
+        gt = ts(g["ts"])
+        before = [(t, (gt - turn_end[t]).total_seconds()) for t in sorted(turn_end) if turn_end[t] <= gt]
+        after = [(t, (turn_end[t] - gt).total_seconds()) for t in sorted(turn_end) if turn_end[t] > gt]
+        ex = exits.get(g["pid"])
+        stopc = [d for d in stops if 0 <= (gt - ts(d['ts'])).total_seconds() <= 30]
+        runs = []
+        for r in (g.get("running") or []):
+            e = [d for d in ev if d["kind"] == "run.end" and d.get("run") == r]
+            runs.append({"run": r, "run_end": e[0]["ts"] if e else None, "ok": e[0].get("ok") if e else None, "killed": e[0].get("killed") if e else None})
+        signals.append({
+            "ts": g["ts"], "pid": g["pid"], "signal": g.get("signal"), "action": g.get("action"), "ppid": g.get("ppid"), "running": g.get("running"),
+            "nearest_before": list(before[-1]) if before else None, "nearest_after": list(after[0]) if after else None,
+            "exit_after": ({"ts": ex["ts"], "reason": ex.get("reason"), "delay_s": (ts(ex["ts"]) - gt).total_seconds()} if ex and ts(ex["ts"]) >= gt else None),
+            "runs": runs, "assistant_stop_call": bool(stopc), "injection_stop": inj_stop,
+            "explained": stop_before(gt),
+        })
+
+    # ---- rates
+    ass = [s for s in schedulers if s["starter"]["kind"] == "assistant"]
+    all_pairs = [(s, p) for s in schedulers for p in s["running_at_turn_ends"]]
+    in_flight = [r for _, p in all_pairs for r in p["runs"]]
+    m_c_1 = {"k": sum(1 for s in ass if s["running_at_turn_ends"]), "n": len(ass)}
+    m_c_2_pairs = {"k": sum(1 for _, p in all_pairs if p["survived"]), "n": len(all_pairs)}
+    m_c_2_runs = {"k": sum(1 for r in in_flight if r["kill_ok"]), "n": len(in_flight)}
+    m_c_4 = {"k": sum(1 for s in schedulers if s["exit"]), "n": len(schedulers)}
+    m_c_6 = {"k": sum(1 for g in signals if g["exit_after"]), "n": len(signals)}
+    m_c_7 = {"k": sum(1 for g in signals if not g["explained"]), "n": len(signals)}
+
+    # ---- M-C-8: the boundary (turn-times.txt)
+    turns8, sleep_entries = [], 0
+    tt = D / "turn-times.txt"
+    if tt.exists():
+        sources.append("turn-times.txt")
+        for ln in tt.read_text().splitlines():
+            m = re.match(r"turn (\d+): .*?utc (\S+) - (\S+)\s+exit (\d+)(?:\s+sleep 20 ended utc (\S+))?", ln)
+            if not m:
+                continue
+            slept = m.group(5)
+            if slept:
+                sleep_entries += 1
+            secs = (ts(slept) - ts(m.group(3))).total_seconds() if slept else None
+            turns8.append({"turn": int(m.group(1)), "chat_end": m.group(3), "sleep_end": slept, "seconds": secs, "ok": bool(secs is not None and secs >= 20)})
+    bf = sorted(Path(p).name for p in glob.glob(str(D / "harness-failures" / "boundary-turn-*.txt")))
+    m_c_8 = {"k": sum(1 for t in turns8 if t["ok"]), "n": len(turns8), "turns": turns8, "boundary_failure_files": bf}
+
+    return {
+        "stream": D.name,
+        "schedulers": schedulers,
+        "counts": {"schedulers": len(schedulers), "assistant_started": n_ass, "script_started": n_inj, "unknown_starter": len(schedulers) - n_ass - n_inj,
+                   "pairs": len(all_pairs), "with_exit": m_c_4["k"], "reasons": sorted({exits[p].get("reason") for p in exits}),
+                   "stop_calls": len(stops), "injection_stop": inj_stop,
+                   "run_end_killed": sum(1 for d in ev if d["kind"] == "run.end" and d.get("killed")),
+                   "run_orphan": sum(1 for d in ev if d["kind"] == "run.orphan"), "scheduler_signals": len(signals)},
+        "m_c_1": m_c_1, "m_c_2_pairs": m_c_2_pairs, "m_c_2_runs": m_c_2_runs, "m_c_4": m_c_4, "m_c_6": m_c_6, "m_c_7": m_c_7, "m_c_8": m_c_8,
+        "sleep_entries": sleep_entries,
+        "signals": signals,
+        "source_files": sources,
+    }
+
+
+def _classify(ex, pr, te, ends, my_sigs, stop_before):
+    """D-SURVIVE's classes for one (turn end, scheduler) pair."""
+    if ex is None:
+        # no scheduler.exit by the stream's end: died with the call, except that an unexplained signal further than 5 s from every turn end is "died later"
+        unexplained = [g for g in my_sigs if not stop_before(ts(g["ts"]))]
+        if unexplained and all(abs((ts(g["ts"]) - te).total_seconds()) > 5 for g in unexplained):
+            return "died later"
+        return "died with the call"
+    reason = ex.get("reason") or ""
+    exit_t = ts(ex["ts"])
+    if reason.startswith("error"):
+        return "error"
+    if reason.startswith("interrupted"):
+        return "error"
+    stopped = reason in ("stopped by SIGTERM", "stopped by SIGHUP")
+    if stopped and not stop_before(exit_t):
+        return "died with the call" if abs((exit_t - te).total_seconds()) <= 5 else "died later"
+    for r in pr["in_flight"]:
+        e = ends.get(r)
+        if e is None:
+            return "died with the call"
+        if e.get("killed") and not stop_before(ts(e["ts"])):
+            return "died with the call"
+    return "survived"
+
+
+def render(a: dict, label: str) -> list:
+    """The text of scheduler-survival.txt: E7's lines (header corrected), then the D-SURVIVE classes, the M-C rates and M-C-8."""
+    out = []
+    w = out.append
+    w(f"# {label} scheduler survival (D-SURVIVE and D-SIGNAL; facts only, from events/, session-turn-times-utc.txt, injection-log.txt)")
+    w("Per scheduler: pid, who started it (the `start` tool.call, in an mcp-<pid> event file, whose interval [ts - ms, ts] holds the scheduler.start: the assistant's per-turn server, or the injection script's server when injection-log.txt names the scheduler's pid), its start/exit,")
+    w("the turn it began in, whether it was running at any turn's end, runs in flight at a turn's end, and kills/stops.")
     w("")
-w(f"stop tool.calls of the assistant: {len(stops)}; injection script --stop: {inj_stop}")
-w(f"schedulers: {len(scheds)}; started by the assistant's server: {n_ass}; started by the injection script: {n_inj}")
-w(f"(turn end, scheduler) pairs with the scheduler running: {len(running_pairs)}")
-w("schedulers with a scheduler.exit: " + str(sum(1 for s in scheds if s['pid'] in exits)) + " of " + str(len(scheds)))
-w("reasons: " + ", ".join(sorted({repr(exits[p].get('reason')) for p in exits})))
-w("run.end with killed=true in the stream: " + str(sum(1 for d in ev if d['kind'] == 'run.end' and d.get('killed'))))
-w("run.orphan events: " + str(sum(1 for d in ev if d['kind'] == 'run.orphan')))
-w("")
-w("Per-turn ps records (run-counts-by-turn.txt 'scheduler record after turn N'): see that file; every record shows 'scheduler.pid: (no file)' unless noted.")
+    for s in a["schedulers"]:
+        st = s["starter"]
+        if st["kind"] == "unknown":
+            who = "unknown"
+        else:
+            who = f"{'injection script' if st['kind'] == 'script' else chr(97) + 'ssistant' + chr(39) + 's MCP server'} (mcp pid {st['mcp_pid']}, file {st['file']}, start tool.call at {st['tool_call_ts']})"
+        w(f"scheduler pid {s['pid']}: scheduler.start {s['start_ts']}; starter: {who}; began in assistant turn: "
+          f"{s['began_in_turn'] if s['began_in_turn'] else 'none (between turns: the injection window)'}")
+        if s["exit"]:
+            w(f"  scheduler.exit {s['exit']['ts']} reason={s['exit']['reason']!r}")
+        else:
+            w("  scheduler.exit: NONE")
+        r = s["runs"]
+        w(f"  runs: {r['run_start']} run.start, {r['run_end']} run.end; run.end with killed=true: {r['run_end_killed']}; run.start without run.end: {r['start_without_end']}")
+        if s["running_at_turn_ends"]:
+            for p in s["running_at_turn_ends"]:
+                w(f"  RUNNING at the end of turn {p['turn']} ({p['turn_end']}); runs in flight: {p['in_flight']}")
+        else:
+            w("  not running at the end of any assistant turn (scheduler.exit came before the turn_end of the turn it began in, or it ran between turns)")
+        if s["exit_to_next_turn_end"]:
+            t, dt = s["exit_to_next_turn_end"]
+            w(f"  scheduler.exit to the next turn_end (turn {t}): {dt:.1f} s")
+        w("")
+    c = a["counts"]
+    w(f"stop tool.calls of the assistant: {c['stop_calls']}; injection script --stop: {c['injection_stop']}")
+    w(f"schedulers: {c['schedulers']}; started by the assistant's server: {c['assistant_started']}; started by the injection script: {c['script_started']}")
+    w(f"(turn end, scheduler) pairs with the scheduler running: {c['pairs']}")
+    w("schedulers with a scheduler.exit: " + str(c["with_exit"]) + " of " + str(c["schedulers"]))
+    w("reasons: " + ", ".join(repr(x) for x in c["reasons"]))
+    w("run.end with killed=true in the stream: " + str(c["run_end_killed"]))
+    w("run.orphan events: " + str(c["run_orphan"]))
+    w("")
+    w("Per-turn ps records (run-counts-by-turn.txt 'scheduler record after turn N'): see that file; every record shows 'scheduler.pid: (no file)' unless noted.")
+    w("")
+    w("# D-SIGNAL: every scheduler.signal line of the stream")
+    w(f"scheduler.signal lines: {len(a['signals'])}")
+    for g in a["signals"]:
+        bf = tuple(g["nearest_before"]) if g["nearest_before"] else None
+        af = tuple(g["nearest_after"]) if g["nearest_after"] else None
+        w(f"scheduler.signal {g['ts']} pid {g['pid']}: signal={g['signal']} action={g['action']} ppid={g['ppid']} running={g['running']}")
+        w(f"  nearest turn_end before: {bf}; after: {af} (turn, seconds)")
+        ex = g["exit_after"]
+        w("  scheduler.exit after it: " + (f"{ex['ts']} reason={ex['reason']!r} ({ex['delay_s']:.2f} s later)" if ex else "NONE"))
+        for r in g["runs"]:
+            w(f"  run in flight {r['run']}: " + (f"run.end {r['run_end']} ok={r['ok']} killed={r['killed']}" if r["run_end"] else "no run.end"))
+        w(f"  explained by a recorded stop (assistant stop tool.call within 30 s before, or injection --stop / facilitator stop per injection-log.txt and run-log.md): assistant stop tool.call: {g['assistant_stop_call']}; injection --stop: {g['injection_stop']}")
+    w("")
+    w("# Schedulers alive at a turn's end (from the pairs above) and whether each survived (D-SURVIVE)")
+    if c["pairs"] == 0:
+        w("(turn end, scheduler) pairs with the scheduler running: 0 -> n/a (0 of 0) for survival")
+    for s in a["schedulers"]:
+        for p in s["running_at_turn_ends"]:
+            w(f"pid {s['pid']} running at the end of turn {p['turn']}; runs in flight {p['in_flight']}; scheduler.exit: {p['scheduler_exit_reason'] if s['exit'] else 'NONE'}")
+    w("")
+    w("# D-SURVIVE classes, M-C rates and M-C-8 (computed here; the text above is E7's)")
+    for s in a["schedulers"]:
+        for p in s["running_at_turn_ends"]:
+            w(f"pid {s['pid']} turn {p['turn']}: {p['class']}" + (" (running by the signal extension: a TERM/HUP exit or unexplained signal within 5 s before the turn end)" if p["extension"] else ""))
+    w(f"M-C-1 assistant-started schedulers running at the end of at least one turn: {rate(a['m_c_1'])}")
+    w(f"M-C-2 (turn end, scheduler) pairs that survived: {rate(a['m_c_2_pairs'])}; runs in flight whose run.end is not a kill: {rate(a['m_c_2_runs'])}")
+    w(f"M-C-3 run.orphan events: {c['run_orphan']}")
+    w(f"M-C-4 scheduler.start with a scheduler.exit by the stream's end: {rate(a['m_c_4'])}")
+    w(f"M-C-6 scheduler.signal lines followed by a scheduler.exit of the same scheduler: {rate(a['m_c_6'])}")
+    w(f"M-C-7 unexplained scheduler.signal lines, of all: {rate(a['m_c_7'])} (explained = a recorded stop within 30 s before: an assistant stop tool.call or the injection script's --stop; a facilitator stop recorded only in run-log.md is not read here)")
+    m8 = a["m_c_8"]
+    w(f"M-C-8 turns whose sleep ended at least 20 s after the chat's end: {rate(m8)}; 'sleep 20 ended' entries: {a['sleep_entries']}; harness-failures/boundary-turn-*.txt: {len(m8['boundary_failure_files'])}")
+    for t in m8["turns"]:
+        w(f"  turn {t['turn']}: chat end {t['chat_end']}, sleep end {t['sleep_end']}, {t['seconds']} s, {'ok' if t['ok'] else 'NOT ok'}")
+    return out
 
-# ---- E7 addition (protocol 4.11, 6, 9 D-SIGNAL): every scheduler.signal and what followed it (facts only)
-w("")
-w("# D-SIGNAL: every scheduler.signal line of the stream")
-sigs = [d for d in ev if d["kind"] == "scheduler.signal"]
-w(f"scheduler.signal lines: {len(sigs)}")
-for g in sigs:
-    gt = ts(g["ts"])
-    before = [(t, (gt - turn_end[t]).total_seconds()) for t in sorted(turn_end) if turn_end[t] <= gt]
-    after = [(t, (turn_end[t] - gt).total_seconds()) for t in sorted(turn_end) if turn_end[t] > gt]
-    ex = exits.get(g["pid"])
-    w(f"scheduler.signal {g['ts']} pid {g['pid']}: signal={g.get('signal')} action={g.get('action')} ppid={g.get('ppid')} running={g.get('running')}")
-    w(f"  nearest turn_end before: {before[-1] if before else None}; after: {after[0] if after else None} (turn, seconds)")
-    w(f"  scheduler.exit after it: " + (f"{ex['ts']} reason={ex.get('reason')!r} ({(ts(ex['ts']) - gt).total_seconds():.2f} s later)" if ex and ts(ex['ts']) >= gt else "NONE"))
-    for r in (g.get("running") or []):
-        e = [d for d in ev if d["kind"] == "run.end" and d.get("run") == r]
-        w(f"  run in flight {r}: " + (f"run.end {e[0]['ts']} ok={e[0].get('ok')} killed={e[0].get('killed')}" if e else "no run.end"))
-    stopc = [d for d in stops if 0 <= (gt - ts(d['ts'])).total_seconds() <= 30]
-    w(f"  explained by a recorded stop (assistant stop tool.call within 30 s before, or injection --stop / facilitator stop per injection-log.txt and run-log.md): assistant stop tool.call: {bool(stopc)}; injection --stop: {inj_stop}")
-w("")
-w("# Schedulers alive at a turn's end (from the pairs above) and whether each survived (D-SURVIVE)")
-if not running_pairs:
-    w("(turn end, scheduler) pairs with the scheduler running: 0 -> n/a (0 of 0) for survival")
-for (pid, t, infl, ex) in running_pairs:
-    w(f"pid {pid} running at the end of turn {t}; runs in flight {infl}; scheduler.exit: {ex.get('reason') if ex else 'NONE'}")
 
-(D / "scheduler-survival.txt").write_text("\n".join(out) + "\n")
-print("\n".join(out))
+def main(argv):
+    args = list(argv)
+    out = None
+    if "--out" in args:
+        i = args.index("--out")
+        out = Path(args[i + 1])
+        del args[i:i + 2]
+    if len(args) != 1:
+        print(__doc__)
+        return 2
+    D = Path(args[0])
+    if not (D / "session-turn-times-utc.txt").exists():
+        print(f"no session-turn-times-utc.txt in {D}", file=sys.stderr)
+        return 2
+    out = out or D
+    out.mkdir(parents=True, exist_ok=True)
+    a = analyse(D)
+    text = render(a, D.name)
+    (out / "scheduler-survival.txt").write_text("\n".join(text) + "\n")
+    a["script"] = {"name": Path(__file__).name, "md5": hashlib.md5(Path(__file__).read_bytes()).hexdigest()}
+    (out / "scheduler_survival.json").write_text(json.dumps(a, sort_keys=True, indent=2) + "\n")
+    print("\n".join(text))
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv[1:]))
```

### `injection_files.py` (from `s2/harness/injection_files.py`)

```diff
--- /Volumes/workspace/hirearchy/studies/E7-org-growth-0a4-recheck/evidence/s2/harness/injection_files.py	2026-10-25 07:58:26
+++ /Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence/harness/injection_files.py	2026-10-26 04:01:48
@@ -1,80 +1,183 @@
 #!/usr/bin/env python3
-# E7 s2 facilitator helper (read-only on the org): writes injection/text-identity.txt and injection/window-runs.txt (protocol 5.4).
-import glob, json, os, re, subprocess, sys, hashlib
-S = sys.argv[1]; INJ = sys.argv[2]; MEMO1 = sys.argv[3]; WIN = open(S + "/injection/window.txt").read().split()
-org = S + "/org"
-w0, w1 = WIN[0] + "Z", WIN[1] + "Z"
-# text identity
-f = glob.glob(f"{org}/sent/{INJ}.md")[0]; txt = open(f).read()
-hdr = {}
-head, _, body = txt.partition("\n---\n")
-for line in head.splitlines()[1:]:
-    if ": " in line: k, v = line.split(": ", 1); hdr[k] = v.strip("'")
-title = hdr["title"]
-m = re.search(r"## Note from the requester\n(.*?)(\n## |\Z)", txt, re.S); note = m.group(1).rstrip("\n")
-t_md5 = hashlib.md5(title.encode()).hexdigest(); n_md5 = hashlib.md5(note.encode()).hexdigest()
-with open(S + "/injection/text-identity.txt", "w") as o:
-    o.write(f"title as stored: {title!r} md5 {t_md5} (protocol 5.1: 849fe21b104be883af9b3c06367d4445) match={t_md5=='849fe21b104be883af9b3c06367d4445'}\n")
-    o.write(f"note as stored: {len(note)} chars md5 {n_md5} (protocol 5.1: 866 chars, 4cdbcb9b682f2f25dcb31c83d3743fec) match={n_md5=='4cdbcb9b682f2f25dcb31c83d3743fec' and len(note)==866}\n")
-    o.write("stored headers: " + json.dumps(hdr) + "\n")
-# events
-ev = []
-for p in glob.glob(org + "/.runtime/events/*/*.jsonl"):
-    for l in open(p):
-        try: ev.append(json.loads(l))
-        except Exception: pass
-starts = [e for e in ev if e.get("kind") == "run.start"]
-ends = {e.get("run"): e for e in ev if e.get("kind") == "run.end"}
-def iso(t): return t.replace("+00:00", "Z")
-runs = []
-for e in starts:
-    ts = e["ts"]
-    if w0 <= iso(ts)[:19] + "Z" <= w1.replace("Z", "Z") or (iso(ts)[:19] >= WIN[0] and iso(ts)[:19] <= WIN[1]):
-        runs.append(e)
-runs.sort(key=lambda e: e["ts"])
-out = [f"# window runs (protocol 5.4): runs that started in the injection window {w0} .. {w1}; injected task {INJ}; revised (memo 1) task {MEMO1}\n"]
-msgs = []
-for p in glob.glob(org + "/**/*.md", recursive=True):
-    if "/.git/" in p: continue
-    try: t = open(p).read()
-    except Exception: continue
-    mm = re.match(r"---\n(.*?)\n---\n", t, re.S)
-    if not mm: continue
-    h = {}
-    for line in mm.group(1).splitlines():
-        if ": " in line: k, v = line.split(": ", 1); h[k] = v.strip("'")
-    if h.get("from") and h.get("type") in ("task", "result", "note"): msgs.append((p, h, t))
-for e in runs:
-    run = e.get("run"); en = ends.get(run, {})
-    agent = (e.get("run") or "").split("@")[0]
-    logs = glob.glob(f"{org}/**/runs/{run.split('@')[-1]}.log", recursive=True) if run else []
-    model = ""
-    if logs:
-        c = [l for l in open(logs[0]) if l.startswith("# cmd:")]
-        mo = re.search(r"--model (\S+)", c[0]) if c else None; model = mo.group(1) if mo else ""
-    rp = [x for x in ev if x.get("kind") == "tool.call" and x.get("run") == run and x.get("args", {}) is not None and "revise_playbook" in json.dumps(x.get("tool", ""))]
-    out.append(f"## run {run} agent={agent} model={model} start={e['ts']} end={en.get('ts')} ok={en.get('ok')} killed={en.get('killed')}")
-    out.append(f"revise_playbook calls in this run (events): {len(rp)}")
-    if logs:
-        t = open(logs[0]).read(); out_part = t.split("# ---- output ----")[-1]
-        rl1 = len(re.findall(r"^\[tool\] @hirearchy/revise_playbook(?= |$)", out_part, re.M)); rl3 = len(re.findall(r"^\[tool\] @hirearchy/\w+", out_part, re.M))
-        out.append("run-log RL1 lines: %d; RL3 lines: %d" % (rl1, rl3))
-    t0 = e["ts"]; t1 = en.get("ts") or "9999"
-    for p, h, t in msgs:
-        c = h.get("created", "")
-        if h.get("from") == agent:
-            if t0[:19] <= c[:19] <= t1[:19]:
-                out.append(f"  {agent} message {h.get('id')} to={h.get('to')} type={h.get('type')} status={h.get('status')} source={h.get('source')} revises={h.get('revises')} created={c}")
-                lm = re.search(r"## Lessons\n(.*?)(\n## |\Z)", t, re.S)
-                if h.get("type") == "result": out.append("  ## Lessons: " + (lm.group(1).strip() if lm else "(none)"))
-    if logs:
-        rel = os.path.relpath(logs[0], org)
-        r = subprocess.run(["git", "-C", org, "log", "-1", "--format=%h", "--", rel], capture_output=True, text=True)
-        out.append(f"  org-git: last commit touching {rel}: {r.stdout.strip()}")
-        cm = subprocess.run(["git", "-C", org, "log", "--format=%h", "--grep", os.path.basename(logs[0])], capture_output=True, text=True).stdout.split()
-        if cm and os.path.dirname(logs[0]).endswith("lead/runs"):
-            d = subprocess.run(["git", "-C", org, "show", "--format=    commit %H%n    Date:   %cd%n    %s", cm[0], "--", "lead/MEMORY.md"], capture_output=True, text=True).stdout
-            out.append("  org-git commit MEMORY.md diff:"); out.extend("    " + l for l in d.splitlines())
-    out.append("")
-open(S + "/injection/window-runs.txt", "w").write("\n".join(out) + "\n")
-print("written", len(runs), "window runs")
+"""G0 injection files: injection/text-identity.txt and injection/window-runs.txt (E7 protocol 5.1 and 5.4). Read-only on everything it reads.
+
+Source and what was generalized. E7 has two producers of these files: `s2|s3/harness/injection_files.py` (reads the sandbox's org; its output
+format has RL1/RL3 labels and `ok=`/`killed=`) and a section of `harness/extract_mechanical.py` (reads the stream dir plus the org's git;
+format `exit=`/`secs=`/`session=` and `P1`/`P3` labels). The files COMMITTED in E7's `s1|s2|s3/injection/` have the second format (their
+first run line carries `exit=0 secs=.. session=..`), so this script writes the committed format: the text-identity check of the first
+script and the window-runs section of the second, both read from the stream dir (events/, run-logs/, msgs/, injection/) instead of the
+sandbox. No service folder, owner or run id is hard-coded: the owner is detected like extract_mechanical.py does.
+
+Usage:  python3 -B injection_files.py <streamdir> <sandbox S or "-"> [--injected ID] [--memo1 ID] [--session-map FILE] [--out DIR]
+  <streamdir>     the stream's evidence dir (needs injection/window.txt; injection/injection-log.txt gives the ids)
+  S               the sandbox, only for the org git lines (the lead run's MEMORY.md diff). "-" or a missing org: those lines say
+                  "not available" and every other line comes from the stream dir.
+  --injected ID   the injected root task (default: `injected task id:` of injection/injection-log.txt)
+  --memo1 ID      the root task it revised (default: the `revised task file:` line of the same log)
+  --session-map   run-session-map.txt written by extract_mechanical.py (default: <streamdir>/run-session-map.txt); gives each run's session id
+  --out DIR       where text-identity.txt and window-runs.txt go (default: <streamdir>/injection/); the stream dir is never written otherwise."""
+import glob
+import hashlib
+import json
+import re
+import subprocess
+import sys
+from datetime import datetime, timezone
+from pathlib import Path
+
+sys.dont_write_bytecode = True
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+import extract_mechanical as em  # noqa: E402  (pure helpers only; the product import happens inside run_extract, never here)
+
+TITLE_MD5 = "849fe21b104be883af9b3c06367d4445"
+NOTE_MD5 = "4cdbcb9b682f2f25dcb31c83d3743fec"
+NOTE_LEN = 866
+
+
+def session_map(path: Path) -> dict:
+    """run id -> session id from run-session-map.txt ({} when absent)."""
+    out = {}
+    if path.exists():
+        for ln in path.read_text().splitlines():
+            m = re.match(r"^run (\S+)\s+\d{8}T\d+ model=\S+ exit=\S+ secs=\S+ -> session (sess_\S+)", ln)
+            if m:
+                out[m.group(1)] = m.group(2)
+    return out
+
+
+def commit_entry(D: Path, owner: str, stamp: str):
+    """(short sha, log lines) of the commit whose subject names `<owner>/runs/<stamp>.log`, from the stream dir's org-git-log.txt (git log --stat), or None."""
+    f = Path(D) / "org-git-log.txt"
+    if not f.exists():
+        return None
+    blocks, cur = [], None
+    for ln in f.read_text(errors="replace").splitlines():
+        if re.match(r"commit \w{40}$", ln):
+            cur = [ln]
+            blocks.append(cur)
+        elif cur is not None:
+            cur.append(ln)
+    for b in blocks:
+        if f"[{owner}/runs/{stamp}.log]" in "\n".join(b):
+            while b and not b[-1].strip():
+                b = b[:-1]
+            return b[0].split()[1][:7], b
+    return None
+
+
+def run_injection_files(D: Path, S_arg: str, OUT: Path, injected: str = None, memo1: str = None, smap: Path = None) -> dict:
+    D, OUT = Path(D), Path(OUT)
+    OUT.mkdir(parents=True, exist_ok=True)
+    info = em.detect(D)
+    owner, owner_dir = info["owner"], info["owner_dir"]
+    log_f = D / "injection" / "injection-log.txt"
+    log = log_f.read_text() if log_f.exists() else ""
+    if injected is None:
+        m = re.search(r"injected task id: (\S+)", log)
+        injected = m.group(1) if m else "-"
+    if memo1 is None:
+        m = re.search(r"revised task file: .*/(\S+)\.md", log)
+        memo1 = m.group(1) if m else "-"
+    org = None
+    if S_arg != "-" and (Path(S_arg) / "org").is_dir():
+        org = Path(S_arg) / "org"
+
+    def git(*a):
+        return subprocess.run(["git", "-C", str(org), *a], capture_output=True, text=True).stdout if org else ""
+
+    # ---- text identity (protocol 5.1)
+    hdr, body, raw = em.read_msg(D / "msgs" / "sent" / f"{injected}.md")
+    note = body.split("## Note from the requester\n", 1)[1]
+    note = note.split("\n## ", 1)[0].rstrip("\n")
+    title = hdr.get("title")
+    ti = [f"title as stored: {title!r} md5 {em.md5b(title.encode())} (protocol 5.1: {TITLE_MD5}) match={em.md5b(title.encode()) == TITLE_MD5}",
+          f"note as stored: {len(note)} chars md5 {em.md5b(note.encode())} (protocol 5.1: {NOTE_LEN} chars, {NOTE_MD5}) match={len(note) == NOTE_LEN and em.md5b(note.encode()) == NOTE_MD5}",
+          f"stored headers: {json.dumps(hdr, ensure_ascii=False)}"]
+    (OUT / "text-identity.txt").write_text("\n".join(ti) + "\n")
+    # ---- window runs (protocol 5.4)
+    w0, w1 = (D / "injection" / "window.txt").read_text().split()[:2]
+    w0d, w1d = em.parse_ts(w0 + "Z"), em.parse_ts(w1 + "Z")
+    events = []
+    for f in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
+        for line in open(f):
+            try:
+                events.append(json.loads(line))
+            except Exception:  # noqa: BLE001
+                pass
+    events.sort(key=lambda e: e["ts"])
+    rp = [e for e in events if e["kind"] == "tool.call" and e.get("tool") == "revise_playbook"]
+    P1 = re.compile(r"^\[tool\] @hirearchy/revise_playbook(?= |$)", re.M)
+    P3 = re.compile(r"^\[tool\] @hirearchy/\w+", re.M)
+    smp = session_map(smap or (D / "run-session-map.txt"))
+    o = [f"# window runs (protocol 5.4): runs that started in the injection window {w0}Z .. {w1}Z; injected task {injected}; revised (memo 1) task {memo1}", ""]
+    n = 0
+    for lg in sorted(glob.glob(str(D / "run-logs" / "*" / "*.log")), key=lambda x: Path(x).stem):  # E7 sorted its runs by stamp
+        stamp = Path(lg).stem
+        agent_dir = Path(lg).parent.name
+        dt = em.stamp_to_dt(stamp)
+        if not (w0d <= dt <= w1d):
+            continue
+        txt = Path(lg).read_text(errors="replace")
+        cmd = re.search(r"^# cmd: .*? --agent (\S+) --model (\S+)", txt, re.M)
+        ex = re.search(r"^# exit (\S+) after (\d+)s", txt, re.M)
+        se = next((e for e in events if e["kind"] == "run.start" and e.get("run", "").endswith("@" + stamp)), None)
+        ee = next((e for e in events if e["kind"] == "run.end" and e.get("run", "").endswith("@" + stamp)), None)
+        run_id = (se or {}).get("run") or ("?@" + stamp)
+        n += 1
+        o.append(f"## run {run_id} agent={agent_dir} model={cmd.group(2) if cmd else None} start={se and se['ts']} end={ee and ee['ts']} "
+                 f"exit={ex.group(1) if ex else None} secs={int(ex.group(2)) if ex else None} session={smp.get(run_id)}")
+        rpc = [e for e in rp if e.get("run") == run_id]
+        o.append(f"revise_playbook calls in this run (events): {len(rpc)}")
+        for e in rpc:
+            o.append(f"  {e['ts']} ok={e.get('ok')} error={e.get('error')} args={json.dumps(e.get('args'))}")
+        outp = txt.split("# ---- output ----", 1)[-1]
+        o.append(f"run-log P1 lines: {len(P1.findall(outp))}; P3 lines: {len(P3.findall(outp))}")
+        if agent_dir == owner_dir:
+            t0, t1 = em.parse_ts(se["ts"]) if se else w0d, em.parse_ts(ee["ts"]) if ee else w1d
+            for f in sorted(glob.glob(str(D / "msgs" / f"{owner_dir}-sent" / "*.md"))):
+                h2, b2, _ = em.read_msg(f)
+                try:
+                    cr = em.parse_ts(h2.get("created", ""))
+                except Exception:  # noqa: BLE001
+                    continue
+                if t0 <= cr <= t1:
+                    les = re.search(r"## Lessons\n(.*?)(?=\n## |\Z)", b2, re.S)
+                    o.append(f"  lead message {h2.get('id')} to={h2.get('to')} type={h2.get('type')} status={h2.get('status')} created={h2.get('created')}\n  ## Lessons: {les.group(1).strip() if les else '(none)'}")
+            if org:
+                for h in git("log", f"--grep={stamp}", "--format=%h").split():
+                    o.append(f"  org-git commit {h} MEMORY.md diff:\n" + "\n".join("    " + x for x in git("show", h, "--", f"{owner}/MEMORY.md").splitlines()))
+            else:
+                entry = commit_entry(D, owner, stamp)
+                if entry:
+                    o.append(f"  org-git commit {entry[0]} (from org-git-log.txt; the MEMORY.md patch itself is in the org's git, which the stream dir does not hold):")
+                    o.extend("    " + x for x in entry[1])
+                else:
+                    o.append("  org-git: not available (no sandbox, and org-git-log.txt has no commit for this run)")
+        o.append("")
+    (OUT / "window-runs.txt").write_text("\n".join(o) + "\n")
+    return {"window_runs": n, "injected": injected, "memo1": memo1}
+
+
+def main(argv):
+    args = list(argv)
+    opts = {}
+    for flag in ("--out", "--injected", "--memo1", "--session-map"):
+        if flag in args:
+            i = args.index(flag)
+            opts[flag] = args[i + 1]
+            del args[i:i + 2]
+    if len(args) != 2:
+        print(__doc__)
+        return 2
+    D = Path(args[0])
+    if not (D / "injection" / "window.txt").exists():
+        print(f"no injection/window.txt in {D}", file=sys.stderr)
+        return 2
+    res = run_injection_files(D, args[1], Path(opts["--out"]) if "--out" in opts else D / "injection", opts.get("--injected"), opts.get("--memo1"),
+                              Path(opts["--session-map"]) if "--session-map" in opts else None)
+    print(f"written {res['window_runs']} window runs")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv[1:]))
```

