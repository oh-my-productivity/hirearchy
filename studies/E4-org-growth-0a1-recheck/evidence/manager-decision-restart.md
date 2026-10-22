# Manager decision: restart E4 after the kiro runtime fix

**Date:** 2026-10-22. **Author:** project manager. The owner delegated execution decisions to the manager ("you are the manager, decide the
best for the project"), and this decision is taken on that authority. It is recorded here before any new stream starts. `protocol.md` (md5 `584b6cc7…`) is NOT edited.

## What happened

- **s1 is INVALID (H8).** Under kiro-cli 2.33.0 / KAS, org agents got no hirearchy MCP tools (`s1/harness-failures/`,
  `docs/research/org-growth/phase-0a1/kiro-mcp-diag/FINDING.md`).
- **The cause was hirearchy's kiro runtime adapter, not 0a/0a.1 logic.** It was fixed and merged as `main` = `7d86c31` (13 commits on `d85cc13`).
- **Evidence for the fix.** An opus spike review, design review, code review and final validation. Live verification passed: a real two-agent org through
  the real scheduler, confinement negatives refused, an `env -i` run (`docs/research/org-growth/kiro-v3/`).

## Decisions

1. **Replacement stream approved (protocol section 11).** It is named `s1r`. s1 stays in the evidence and the report as INVALID. The study needs 3 valid streams:
   `s1r`, `s2`, `s3`.
2. **Protocol amendment 1, pre-registered before `s1r` turn 1.** It goes in `protocol-amendment-1.md` with its own md5 file. Allowed changes, and nothing else:
   - **Product under test** is `main` = `7d86c31`. The 4.1 diff check is against `7d86c31` instead of `d85cc13`. The skill md5 stays `573495bb…`: `SKILL.md` is
     unchanged between the two commits (verified by the manager).
   - **Measurement methods (section 10) are re-validated against the V3 run-log and event formats.** The kiro fix changed how org runs are
     logged (stream-json renderer, launcher markers, the per-org kiro home under the hirearchy state dir). Every method whose evidence source or grep
     pattern moved is restated so it measures the same thing. Use `docs/research/org-growth/kiro-v3/live-verification.md` and
     `/tmp/kirov3-live` as real examples. **No pass rule changes.**
   - **Agent-visible changes since `d85cc13` are listed as context, not as confounds to remove.** They are:
     - org agents run from an empty scratch cwd;
     - the V3 built-in tool names in the Files guide;
     - the stricter workspace protections.
   - **Readiness refusals.** A scheduler `start` that the readiness gate refuses (kiro-cli unreachable or auth) is an H8-type infrastructure
     failure. The assistant's own retry is product behaviour; record it.
3. **A harness preflight before `s1r`.** One throwaway scratch org, outside the study sandboxes, with a lead on the study's lead model. It must call
   a hirearchy tool through the real scheduler, which `obs events` or the org's tool.call events show. Then delete it. If it fails, no
   stream starts and the run pauses for the manager.
4. **Everything else is unchanged.** Pass rules, models, injection, caps, Lena's lines, ambient-context rules and safety rules are exactly as in `protocol.md`.
