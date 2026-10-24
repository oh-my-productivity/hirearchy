# Review r4: memo-2026-10-05 after Due rework (task 1792)

Opened: lead/writer/work/memo-2026-10-05.md (195 words, modified 03:46:51 UTC); /private/tmp/hirearchy-e5-s2-1792812864/notes/2026-10-05.md (opened in full). Nothing unopened.

## My own list from the notes (before comparing)
Decisions:
- D1 "we decided to push the gateway migration to the week of 26 October" (from week of 12 Oct; reason: 2 of 5 services fail contract tests, header casing).
- D2 "we decided to adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable".
Commitments:
- A1 Priya: draft RFC for per-key rate limiter "by Oct 9" (explicit ACTION).
- A2 Dev: enable Renovate on the three core repos "by Oct 8" (explicit ACTION).
- A3 Sam: "said he'd look into the flaky CI before Friday" (informal, prose; not hedged, so not tentative).
- A4 Marta: "book the on-call training room for Oct 14" (explicit ACTION).
- A5 Lee: "We agreed Lee would ping the vendor ... this week and report back, no hard date attached" (informal).
Ambiguous: (a) A5 is also phrased "we agreed", so it could count as a decision as well as a commitment; the memo lists it only as an action. (b) Meeting closing time and "Next meeting Monday 12 October" are facts, not items.

## Per-criterion verdict
- C1 met. Memo header "Platform team weekly, 2026-10-05"; all content traces to 2026-10-05.md (checked below). No other note file content.
- C2 met. read shows 195 words (limit 400).
- C3 met. Markdown; "## Decisions"; table header "| Owner | Action | Due |" exactly three columns.
- C4 met. D1 and D2 both present, with the same details ("week of 12 October to the week of 26 October", "Two of the five services still fail the contract tests, mostly because of header casing"; "weekly Monday batch", "three core repos", "widen later if the noise is acceptable"). No third decision added.
- C5 met. One row each: Priya, Dev, Sam, Marta, Lee = A1-A5, no extras. No commitment in the notes is stated as uncertain (Sam "said he'd look into", "suspects" refers to the cause, not the commitment), so no 'tentative' marking is required and none is present.
- C6 met. Every Due cell is ISO or 'none':
  - Priya 2026-10-09: notes "by Oct 9"; year 2026 from the meeting date. Correct.
  - Dev 2026-10-08: notes "by Oct 8". Correct.
  - Sam none: notes "before Friday". Meeting is Monday 5 Oct, so Friday is 9 Oct, but "before Friday" could mean Thursday 8 Oct or Friday 9 Oct; the date is not unambiguously clear, so 'none' follows the rule. Explained in Open questions ("the notes give the deadline only as 'before Friday', so no date is set"). Matches the quote.
  - Marta none: notes "book the on-call training room for Oct 14"; Oct 14 is the date of the room/training, not stated as a booking deadline. 'none' follows the rule; explained in Open questions.
  - Lee none: notes "no hard date attached" ("this week" is vague). Correct. The memo does not explain Lee in Open questions; the Action cell says "this week", which is sufficient. Not required.

Specific: Sam none + Marta none, each explained in Open questions: met. Priya 2026-10-09 and Dev 2026-10-08: met.

## Nothing-added check (quality bar)
All memo facts trace to the notes: rationale for D1; "for review at the following meeting"; "suspects the shared build cache"; "for the two newest engineers (fits eight people, with a screen)"; "Next meeting: Monday 12 October". One small inference: "14 October is the training date" (Open questions). The notes say only "the on-call training room for Oct 14"; reading it as the training date is natural but is the writer's wording. Optional, not required.

## Note on earlier review
My earlier review (r3) accepted Sam 2026-10-09 and Marta 2026-10-14 as user-settled values. This version has 'none' for both. Under C6 both versions can be defended (Friday/Oct 9 is derivable from the meeting date; 'before Friday' still leaves Thursday vs Friday open). I judge this version against the criteria as written in this task, where 'none' is required for both.

## REQUIRED CHANGES
None.

Optional: change "14 October is the training date" to "the notes give Oct 14 for the room and no booking deadline" to stay strictly inside the notes.

Not a fact-check: I compared the memo with the notes only; I did not check the notes' own claims (e.g. 1 in 8 CI failure rate, which the memo does not repeat).

criteria met: 6 of 6
factual claims verified: 14 of 14 (D1 date shift, D1 2-of-5 services, D1 header casing, D2 Renovate/weekly Monday, D2 three core repos, D2 widen later, Priya task and date, Dev task and date, Sam task and 'before Friday', Marta task, room spec, Lee task, next meeting date, meeting date in title)
