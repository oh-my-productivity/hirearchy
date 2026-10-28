# Manager decision: the preflight probe's definition defect, amendment H-A1 (2026-10-27)

**What happened** (`preflight.md`). The frozen `harness/probe.sh` defines the probe service (lines 42-43) without `--deliverable`. The
product refused that first definition. No service existed in any of the four probe orgs, so:
- root's `services` read `No services yet.` in all four sessions;
- the arm-F lock command failed;
- the positive control (contract v2 against v1) and the lock-hook checks were never exercised.

What the probe did show:
- `session_start` (memories block included), the `tool_load` hashes and the non-`[tool]` stderr lines are equal in all four sessions;
- failed empty-argument calls are 0 in both arms;
- `memories.db` was unchanged (`f0aaf02a...` before and after).

The cost was about 5.71 credits and 2 org runs. **This is a harness defect, not an arm difference and not a product defect.** The product's
refusal is correct (`hirearchy define-service --help` lists `--deliverable` and `--path`).

The lock command itself (`probe.sh` line 48) has the same form as the stream hook (`after_turn.sh` line 140): `define-service <lead> <service>
--locked` on a service that exists. It was not reached.

**Decision: APPROVED, amendment H-A1 (harness). Section 0 allows it, because F1's first turn has not happened.** Do these in order:
1. **The fix.** Change only `probe.sh`'s first definition (lines 42-43). Add `--deliverable`, and `--path` if the product requires it, with
   values the product accepts. Take them from the refusal text kept in attempt 1 and from `define-service --help`. Any `--path` is an absolute
   folder inside that probe's own sandbox. The arm-F lock line stays byte for byte as it is, so the re-run exercises the stream hook's own form
   on an existing service.
2. **The whole-harness check, before the re-freeze.** List every product CLI call in the frozen harness (`grep -n 'hirearchy ' harness/*`).
   Check each one's subcommand and flags against `hirearchy <subcommand> --help`; this is read-only. Write the list with OK or MISMATCH for each
   into `harness/CHANGES.md`, "Amendment H-A1".
   - If any other call is a MISMATCH, **stop and send a warning** with the line. Do not fix it on your own.
3. **Attempt 1 is kept, not overwritten.**
   - Move `evidence/probe/` to `evidence/probe-attempt-1/` unchanged, and copy into it whatever of the four `/tmp/hirearchy-p1-probe-*`
     sandboxes the protocol keeps as probe evidence.
   - Then delete those four study-owned `/tmp` sandboxes, and any probe profile still in `~/.kiro/agents` (the study's own only).
   - Record each deletion in `preflight.md`.
4. **The re-freeze.**
   - Update `harness/MD5SUMS`, and `protocol.md5` only if `protocol.md` changes. Record H-A1 in the amendment list the protocol's section 0
     names.
   - Append to `freeze.txt` the old and new md5s and this file's name.
   - Re-run `selfcheck.sh` on the re-frozen files. It must still be 17 of 17 parts and 206 tests.
5. **Re-run the probe once,** with the frozen pass criteria unchanged:
   - root's `services` reads `contract v2` in arm F and `contract v1` in arm I, and nothing else differs;
   - the lock checks pass (the reply, `SERVICE.md` `locked: true`, and the owner's quiet note);
   - failed empty-argument calls are 0 in both arms;
   - there is no unexplained difference;
   - `memories.db` is unchanged.
   **If it fails on anything, stop and send a warning. There is no third attempt without me.**
6. **Cost.** Record attempt 1 and attempt 2 separately in `preflight.md`. Their sum counts against the probe's line in the approval (about 20
   credits).
7. Then finish the preflight record and signal success. Start no stream in this step.

**Lesson for the backlog (study harnesses).** `probe_check.py` tested the probe's comparison on constructed sessions, and never the probe's
own product calls. Future harness self-checks must dry-run every product CLI call the harness makes against a throwaway org before the
freeze.
