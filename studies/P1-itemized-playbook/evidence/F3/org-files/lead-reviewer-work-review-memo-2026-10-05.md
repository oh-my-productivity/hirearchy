# Review: memo-2026-10-05.md

Files opened:
- lead/writer/work/memo-2026-10-05.md (94 words per hirearchy read, 16 lines)
- /private/tmp/hirearchy-p1-F3-1793152805/notes/2026-10-05.md (opened in full; read-only)
Not opened: none.

## My own list from the notes (before comparing)
Decisions:
- D1 "we decided to push the gateway migration to the week of 26 October and use the extra time for the failing services"
- D2 "we decided to adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable"

Commitments (formal and informal):
- K1 ACTION Priya: draft RFC for per-key rate limiter by Oct 9
- K2 ACTION Dev: enable Renovate on the three core repos by Oct 8
- K3 informal, Sam: "said he'd look into the flaky CI before Friday"
- K4 ACTION Marta: "book the on-call training room for Oct 14"
- K5 informal, Lee: "We agreed Lee would ping the vendor about it [SSO cert] this week and report back, no hard date attached"

Not commitments (checked): Dev walking through staging results; "so the team can review it at the following meeting" (purpose of Priya's RFC, not a task); "Nobody objected" to Sam (not a decision); support tickets, flaky-CI rate, next meeting Mon 12 Oct (facts); no other prose commitments found.
Ambiguous: K3 due date; K4 due date (see below).

## Comparison
D1 -> memo line 1: present. D2 -> memo line 2: present (the clause "widening later if the noise is acceptable" is omitted; a qualifier, optional).
K1 -> row Priya, 2026-10-09: matches. K2 -> row Dev, 2026-10-08: matches. K3 -> row Sam: present. K4 -> row Marta: present. K5 -> row Lee, none: present, matches "no hard date attached".
Memo has 2 decisions and 5 rows; mine has 2 and 5. Nothing in the memo is missing from the notes, nothing extra.

## Criteria
- C1 met. Only content from 2026-10-05 notes (title "Platform team weekly memo, 2026-10-05"); no other meeting.
- C2 met. Markdown (headings, list, table); 94 words per read, limit 400.
- C3 met. "## Decisions" has 2 one-line items = D1, D2.
- C4 met. Header `| Owner | Action | Due |` exactly three columns, in that order; all 5 rows have 3 cells.
- C5 met. All 5 commitments K1-K5 are rows, including the unlabelled K3 (Sam) and K5 (Lee).
- C6 NOT MET (see (b)). All Due values are ISO dates or `none`, format OK. Priya 2026-10-09 and Dev 2026-10-08 match explicit dates. Lee `none` correct. Sam 2026-10-08 is ok (a). Marta 2026-10-14 is the problem (b).
- C7 met. Every decision and every action is in the notes. Caveat: Marta's Due 2026-10-14 presents the room date as a booking deadline, which the notes do not say (counted under C6).
- C8 NOT MET. Review does not show every criterion met, and no required change has been applied yet.

## Points you asked me to judge
(a) Sam: Monday 2026-10-05 -> Friday is 2026-10-09 (checked: 5 Oct 2026 is a Monday). "Before Friday" excludes Friday, so the last day is Thursday 2026-10-08. 2026-10-08 is a faithful reading and I accept it. AMBIGUOUS in that a reader could take "by Friday" = 2026-10-09; the notes say "before", so 2026-10-08 stands. Verdict: acceptable.
(b) Marta: the notes say "book the room for Oct 14". Oct 14 is the date of the training/room. No deadline for the booking is stated. C6 says that if no date is given, Due is none; C7 says nothing invented. Required: Due = none. AMBIGUOUS only in that the sentence could be read as a deadline; I judge the room-date reading the natural one, and a booking deadline of the training date itself is not stated. Because Oct 14 would then disappear from the memo, put it in the Action text.
(c) Lee: "this week" with "no hard date attached" -> `none`. Correct. (Turning "this week" into 2026-10-09 would contradict "no hard date attached".)
(d) Decision lines and Lee/Sam actions: contain nothing beyond the notes. Decision 1 "using the extra time for the failing services" and Decision 2 "weekly Monday batch ... three core repos" are in the notes. Lee row: "Ping the identity vendor about the SSO certificate renewal and report back" matches. Sam row: "Look into the flaky CI" matches (the build-cache suspicion is not added).

## REQUIRED CHANGES (by severity)
1. Marta row, Due: change `2026-10-14` to `none`.
2. Marta row, Action: change `Book the on-call training room` to `Book the on-call training room for Oct 14` so the date from the notes is kept (the row then reads: `| Marta | Book the on-call training room for Oct 14 | none |`). If the lead decides 2026-10-14 is a deadline, record that decision; I cannot verify it from the notes.

Optional: add "and widen later if the noise is acceptable" to the Renovate decision line (in the notes, a qualifier of the decision). Memo stays far under 400 words.

Not checked: the memo and notes contain factual claims (dates, counts) I did not verify beyond the notes; this review is not a fact-check.

criteria met: 6 of 8
