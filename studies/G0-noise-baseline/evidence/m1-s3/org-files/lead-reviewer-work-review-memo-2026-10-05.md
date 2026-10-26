# Review: memo 2026-10-05

Files opened: lead/writer/work/memo-2026-10-05.md (249 words); /private/tmp/hirearchy-g0-m1-s3-1793003475/notes/2026-10-05.md. None unopened.

## My own list from the notes (before comparing)
Decisions (2):
- D1 push gateway migration from week of 12 Oct to week of 26 Oct ("we decided to push the gateway migration to the week of 26 October")
- D2 adopt Renovate, weekly Monday batch of PRs, start with three core repos ("we decided to adopt Renovate...")

Commitments (5):
- A1 Priya: draft RFC per-key rate limiter "by Oct 9" (ACTION)
- A2 Dev: enable Renovate on three core repos "by Oct 8" (ACTION)
- A3 Sam: "he'd look into the flaky CI before Friday" (prose, unlabelled)
- A4 Marta: book on-call training room "for Oct 14" (ACTION)
- A5 Lee: "Lee would ping the vendor about it this week and report back, no hard date attached" (prose)
Ambiguous: Dev "can do [the app install] himself" is part of A2, not separate. No other items found.

## Comparison
D1 present, D2 present. A1-A5 all present as rows, owners correct. Decisions found 2 / in memo 2; commitments found 5 / in memo 5.

## Criteria
- C1 met. Every statement traces to the notes (present list, 10:55 close, next meeting 12 Oct, test failures, reasons, room for eight with screen, SSO expiry). Nothing from other meetings. (Facts not independently fact-checked beyond comparison to the notes.)
- C2 met. read shows 249 words (<= 400).
- C3 met. "## Decisions" section lists D1 and D2.
- C4 met. Header is exactly "| Owner | Action | Due |" with separator row.
- C5 met. Five rows, including Sam and Lee (prose-only), owners right.
- C6 NOT MET (ambiguous on one row). All Due values are ISO or none. Check against Monday 2026-10-05:
  - Priya 2026-10-09: notes "by Oct 9" - correct.
  - Dev 2026-10-08: notes "by Oct 8" - correct.
  - Sam 2026-10-08: "before Friday"; Friday is 2026-10-09, so before Friday = 2026-10-08 - correct. (Ambiguous only if read as "by Friday" = 10-09; the criterion's own example "before Friday" supports 10-08.)
  - Lee none: notes say "no hard date attached" - correct. ("this week" could be read as 2026-10-09; the notes explicitly deny a hard date, so none is right.)
  - Marta 2026-10-14: AMBIGUOUS. Notes say "book the on-call training room for Oct 14": Oct 14 is the date of the training, not a deadline for booking. The notes do not state by when the booking must be made. The memo itself concedes it "reads" Oct 14 as due. Under C6 ("converted to a date ... when the notes make it clear; otherwise Due is none") the notes do not make a booking deadline clear, so Due should be none. I rate this not met, flagged ambiguous for the lead to overrule.

## REQUIRED CHANGES (by severity)
1. Marta row, Due: change "2026-10-14" to "none" (the notes give the training date, not a booking deadline), unless the lead decides the training date is the intended deadline. Optionally keep "Oct 14" in the Action text (it already is).
2. Assumptions line: change "\"for Oct 14\" is read as due by 2026-10-14, the date given in the notes" to say that the notes give no booking deadline, so Due is none (only if change 1 is applied).

Optional: none.

criteria met: 5 of 6
Decisions/commitments: 7 found in notes (2 decisions, 5 commitments); 7 present in memo.
