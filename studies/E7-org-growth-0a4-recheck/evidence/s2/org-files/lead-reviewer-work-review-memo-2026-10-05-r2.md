# Re-review: memo-2026-10-05 (task 20261025T074809756939-lead-d5ce, revises 20261025T074606589355-lead-12e5)

Files opened:
- lead/writer/work/memo-2026-10-05.md (137 words per hirearchy org_read, modified 07:47:42 UTC)
- /private/tmp/hirearchy-e7-s2-1792914064/notes/2026-10-05.md (read in full)
- lead/reviewer/work/review-memo-2026-10-05.md (my first review)
Not opened: none.

## My own list from the notes (unchanged, rebuilt from the source)
Meeting Monday 2026-10-05; Friday = 2026-10-09.
Decisions: D1 push gateway migration to week of 26 October (extra time for failing services); D2 adopt Renovate, weekly Monday batch, three core repos first, widen later if noise acceptable.
Commitments: A1 Priya RFC "by Oct 9"; A2 Dev enable Renovate "by Oct 8"; A3 Sam "said he'd look into the flaky CI before Friday" (informal); A4 Marta "book the on-call training room for Oct 14"; A5 Lee "agreed ... would ping the vendor about it this week and report back, no hard date attached" (informal).
Not commitments: Dev's remark that he can install the app himself (covered by A2); next meeting Monday 12 October.

## Changes since the first review
- Sam Due: 2026-10-09 -> 2026-10-08. Matches "before Friday" read strictly (Friday = 2026-10-09). Fixed.
- Sam Action: "(said in passing; ...)" removed. Now "Look into the flaky CI; he suspects the shared build cache", tied to "since he suspects the shared build cache". Fixed.
- Everything else unchanged and re-checked (Priya, Dev, Lee rows, both decisions, Next meeting line).

## Added-wording check (every statement vs notes)
- Decision 1: "from the week of 12 October" <- "cutting over in the week of 12 October"; "Two of the five services still fail the contract tests" <- same sentence; "extra time is for fixing them" <- "use the extra time for the failing services". OK.
- Decision 2: near verbatim. OK.
- Priya: "for the new per-key rate limiter, for review at the following meeting" <- "so the team can review it at the following meeting". OK.
- Dev: OK. Sam: OK. Marta: verbatim. Lee: "identity vendor", "expiring SSO certificate" (<- "expires at the end of the month"), "report back". OK.
- "Next meeting: Monday 2026-10-12." <- "Next meeting Monday 12 October." OK (extra line, supported).
No unsupported wording found.

## Criteria
- C1 met. All statements tie to 2026-10-05.md; nothing from other files.
- C2 met. Decisions section: exactly D1 and D2; no invented decision. (Lee's "We agreed" is an assignment, listed as action A5; see ambiguity 2.)
- C3 met. Five rows for A1-A5 incl. informal ones (Sam, Lee); Owner = the committing person in each row.
- C4 met. Header "| Owner | Action | Due |", separator row, three columns in every row.
- C5 AMBIGUOUS, pending the lead's ruling on Marta (see ambiguity 1). Priya 2026-10-09, Dev 2026-10-08, Sam 2026-10-08 ('before Friday' strict), Lee none ("no hard date attached") are correct. Marta: Due is "none" while the notes contain the date "Oct 14".
- C6 met. 137 words per org_read, limit 400.

Criteria met: 5 of 6 (C1, C2, C3, C4, C6 met; C5 depends on the Marta ruling).
If the lead rules that "for Oct 14" is the training date and not a due date: 6 of 6, pass. If the lead rules that it is a stated date under C5: C5 not met, and the required change is below.

## Ambiguities (for the lead to rule on)
1. C5, Marta. "book the on-call training room for Oct 14". C5 says Due is ISO "when the notes state a date or give a deadline". Oct 14 is a date in the notes, but it is the date the room is needed (training), not stated as the deadline for the booking. Reading A: Due = none (memo as is; no deadline is stated, and a date would add a deadline the notes do not say). Reading B: Due = 2026-10-14. I did not decide.
2. C2/C3, Lee. "We agreed Lee would ping the vendor" is an agreement and a commitment. Listed once, as an action.
3. C5, Sam. "before Friday": strict 2026-10-08 (memo), or inclusive 2026-10-09. Memo follows the strict reading, which I take.
4. C5, Lee. "this week" could resolve to 2026-10-09, but the notes say "no hard date attached"; "none" accepted.

## REQUIRED CHANGES
None, unless the lead picks Reading B for Marta. Then: Marta row Due `none` -> `2026-10-14`.

## Not checked
Not a fact-check: claims inside the notes (e.g. number of failing services) were not checked against any other source.
