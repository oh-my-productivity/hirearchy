# Manager decision: m0-s2's validity (2026-10-25)

## Ruling: (b). m0-s2 is INVALID from turn 7 (H7), with no replacement now.

## Reasons
- **H7 is met.** E7 4.10 gives L-KEEP only for a preference question that the answer key does not settle. D17 settles this one: at most one title heading may come before "Summary:".
  - The facilitator's "Keep it as it is." in T7, followed by the reject on exactly that point in T9, made Lena contradict herself.
  - That chain then decided the stream's later course: R2, contract v3 and v4, the declined spend, and memo 3 without a verdict.
- **G0 measures noise.** A facilitator error adds variation that is not the product's and not the models'. Counting the stream would widen the bands with harness error. So (a) is rejected.
- **G0 needs no replacement now.** G0 has no pass rule, and Phase 0b's exit criterion ("noise baseline measured") is met on 5 valid streams if the report states it honestly. Design 20.1 also lets the harness add a stream to an arm afterwards (`run_arm.sh M0 1`), so (c) stays open.
- **Spend is already over the approval.** G0 used 241 org runs and about 405 credits, against the approved ~230 runs and ~355 credits. A replacement needs the owner's OK. The manager is putting that question to the owner and will not spend further without it.

## What the report does
- M0 has k = 2 valid streams. Every M0 cell, and every cell of arm × stratum that rests on M0, reads `n/a (2 of 3)` for its spread. Design 21's "k = 3 valid streams per arm" is reported as not met for M0, with this decision as the reason.
- m0-s2's turns 1-6, which end before the facilitator's T7 line, are reported as "before the failure" (protocol 11). They are not pooled into the bands.
- Pooled values across arms use the 5 valid streams. Each pooled table says so.
- **Findings to record:**
  - **The facilitator's L-KEEP check (harness).** Any next study pre-registers a decision table that says which questions the key settles and the fixed line for each, and the run step checks every L-KEEP against it before sending.
  - **P2 `words=` accepted "Keep it as it is."** for contract v3 (C10) in m0-s2 after the failure. This is an observation, not a counted value. It is input for Phase 1: P2-WORDS checks only that the words are not the rejection's own words. A generic phrase passed.
- **Spend:** report it per stream and in total against the approval (241 runs and about 405 credits, against ~230 and ~355), with the reason. Streams ran up to the 15-turn cap more often than E7's did.
- **If the owner approves a replacement later,** m0-s2r runs under the frozen protocol, and the report gets an addendum.

The report step then aggregates, writes STUDY.md and `phase-0b/g0-report.md`, and continues.
