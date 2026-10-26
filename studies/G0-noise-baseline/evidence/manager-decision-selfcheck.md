# Manager decision on G0's harness self-check (2026-10-25)

## Ruling principle
The harness's re-derivation implements the **design's rules** (0b design sections 3-9, as amended), independently of the product. That way the section 21 check "the view is right on live files" can catch product deviations.
- **"Published" values that describe the replay kit** have no org git history, which is the declared kit limit of the 0b build overrides, section 9. They are not the reference for the history path. For that path the reference is the design's rule applied to the full evidence.
- **Where the harness and the product agree but the design says otherwise,** the harness follows the design and the product's value is reported as a defect.

## The four mismatches
1. **`history.known`: amend.**
   - With E7's evidence the value is `true` in s1-s3. The 19.3 value `false` is the kit's.
   - The self-check expects `true`. The replay tests keep `false`, under their kit-limit label.
2. **s2 `unjudged_cases`: a product defect. Pre-register it as F-G0-1. G0 is not delayed.**
   - **The rule.** OQ-2's given delivery is the delivery whose checked artifact equals the file. **When several deliveries qualify, the one that carries a human-tier verdict is chosen. If none carries one, the latest is chosen.**
   - **Why.** That is OQ-2's stated intent ("read her verdicts"), and the design's history-path claim names c671.
   - **What the harness does.** It implements this rule. So s2's expected `unjudged_cases` is `[]`, with the given delivery c671.
   - **What the product does.** It takes the newest result first and names 3ca4. That is a deviation, so the self-check records it as **F-G0-1** (the product view, s2 of E7), not as a harness mismatch. The pattern (a head task's late `done` result seconds after its human rework's, with the same file) occurred in E7 s1 and s2. It will most likely recur in G0. Every occurrence is reported per stream as a view mismatch with its files.
   - **Why G0 still runs.** The harness's values are the correct ones, so G0's product-layer baseline stays usable. The fix comes after G0, in a small batch, and is verified deterministically on G0's and E7's kept evidence. No new live run is needed. G0 is not delayed.
3. **s3 `not_as_delivered`: amend. This is correct by definition.**
   - The file is v4, the artifact of d9bc, whose result da3c is `blocked`. A blocked result is no delivery (D4).
   - P3 compares against the team's last checked artifact, the relayed 5834's v3, so `[09df/5834]` follows from the definitions. The label is neutral ("not as delivered", OQ-3); it does not say hand-edited.
   - The design's claim in E7S3-6, "replay and history agree", is wrong. Record that as a design correction for the post-G0 batch, and record a finding: a file copied from a blocked result reads "not as delivered". A later label could say "from a blocked result" (backlog).
4. **score_memos, the s2 memo-3 v1 review: state D21's reading and match E7 if a stated rule can.**
   - The org commits after each run, so a review task can be sent a few seconds before the author's version is committed.
   - Find the mapping E7's scorer used (E7 STUDY and its interpretations). If a stated rule reproduces it, pre-register that reading of D21 in G0's protocol and implement it, so that the self-check gives E7's 8 of 8. A candidate rule: the version reviewed is the one committed by the author run whose result the review task follows.
   - If no stated rule reproduces E7's mapping, keep D21 literal, expect "no version", and record E7 STUDY's value as a correction.
   - Either way, the protocol states the reading, because reviewer ambiguity recall depends on it.

## Then
1. Re-run `selfcheck.sh`. It passes when every remaining mismatch is a declared product deviation (F-G0-1) or an amended expectation, each listed in `SELFCHECK.md`.
2. Freeze the protocol and harness.
3. Continue with the preflight.
