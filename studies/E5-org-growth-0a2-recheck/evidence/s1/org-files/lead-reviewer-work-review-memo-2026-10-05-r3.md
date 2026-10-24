# Review r3: lead/writer/work/memo-2026-10-05.md (task ...20c3)

Opened: lead/writer/work/memo-2026-10-05.md (151 words per hirearchy org_read, modified 03:14:08 UTC); /private/tmp/hirearchy-e5-s1-1792811051/notes/2026-10-05.md. Both opened.

## My own list from the notes
Decisions (2):
D1. "we decided to push the gateway migration to the week of 26 October and use the extra time for the failing services" (from week of 12 Oct).
D2. "we decided to adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable".
Commitments (5):
A1. Priya: draft RFC for per-key rate limiter "by Oct 9" (labelled ACTION).
A2. Dev: enable Renovate on three core repos "by Oct 8" (labelled ACTION).
A3. Sam: "he'd look into the flaky CI before Friday" (unlabelled, prose).
A4. Marta: "book the on-call training room for Oct 14" (labelled ACTION).
A5. Lee: "would ping the vendor about it this week and report back, no hard date attached" (unlabelled, prose).
Ambiguous (not counted; reported only):
X1. "so the team can review it at the following meeting" (team reviews the RFC; Next meeting is Monday 12 October). Team-wide, no named owner; a plan, not a personal commitment. Not in memo.
X2. "use the extra time for the failing services" has no named owner; it is part of D1 and is in the memo only as part of the decision.
No other decisions or commitments found. Discussion about CI flakiness ("one run in eight") and the rate limiter background are not commitments.

## Due check against the notes (every row)
- Priya: notes "by Oct 9"; meeting dated Monday 5 October 2026, so the year is clear. Memo 2026-10-09. Correct.
- Dev: notes "by Oct 8". Memo 2026-10-08. Correct.
- Sam: notes "before Friday". Friday is 9 Oct, but "before Friday" could mean Thursday 8 Oct or end of Friday-eve; the exact day is not clear. Memo none. Correct, and explained in Open questions.
- Marta: notes "book ... room for Oct 14". Oct 14 is the training date, not stated as a booking deadline. Memo none, with explanation. Correct (defensible; the only alternative reading, due 2026-10-14, is not clear from the notes).
- Lee: notes "this week, no hard date attached". Memo none. Correct.

## Criteria
- C1 Built only from the named notes file: met. Every memo statement traces to the notes (D1, D2, A1-A5). The Open questions repeat the notes' wording ("before Friday", "Oct 14", "this week"). Nothing added from outside.
- C2 At most 400 words as counted by read: met. 151 words.
- C3 Markdown memo with Decisions section listing every decision, incl. unlabelled prose: met. "## Decisions" has 2 bullets matching D1 and D2, both stated in prose without a label. No decision from my list is missing.
- C4 Action items section as markdown table with exactly columns Owner | Action | Due: met. "## Action items" then header "| Owner | Action | Due |" with separator row; 5 rows, 3 cells each.
- C5 Table lists every commitment, informal and unlabelled, with the person as Owner: met. Rows Priya, Dev, Sam, Marta, Lee = A1-A5. Sam and Lee (unlabelled, prose) are present, each with the person who made it as Owner.
- C6 Every Due is ISO date or none; vague ones become dates only when clear: met. Values: 2026-10-09, 2026-10-08, none, none, none. All valid format; none of the "none" rows has a clear date in the notes (see check above).
- Plus: Sam none and Marta none, each explained in an Open questions section: met. "## Open questions" has "Sam's flaky-CI deadline is \"before Friday\"; the notes give no explicit date." and "Marta: 14 Oct is the training date, and no booking deadline is given." Lee is also explained.

criteria met: 7 of 7 (C1-C6 plus the Plus requirement). Verdict: pass.

## REQUIRED CHANGES
None.

## Optional / for lead to decide
- X1: the RFC review at the next meeting (12 Oct) is a team plan with no named owner; memo omits it. Left out, consistent with the Scope (no discussion). Reported as ambiguous, not decided.
- The Marta row's Action text says "Oct 14" (not ISO); it is in the Action column, not Due, so C6 is not affected.

## Not checked
Factual claims in the memo beyond matching the notes (for example whether 12 Oct is a Monday) were not independently fact-checked; this review is not a fact-check.
