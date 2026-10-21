# Re-review: lead/writer/work/memo-2026-10-12.md (task ...a9fd, revises ...5319)

Files opened: lead/writer/work/memo-2026-10-12.md (129 words per read); /private/tmp/hirearchy-e3-1792595952/notes/2026-10-12.md (340 words); lead/reviewer/work/review-memo-2026-10-12.md (456 words). None unopenable.

## My own enumeration from the notes (re-done from the source)
Decisions (3): (1) approve RFC with token bucket (per API key) design, ship behind feature flag first; (2) postmortem blameless, shared with whole company; (3) deploy freeze Oct 22 and Oct 23.
Commitments (5): Dev "write the postmortem for the Oct 8 outage by Oct 14"; Marta "send the demo agenda to the customer by Oct 16"; Priya "start implementing the rate limiter behind a feature flag by Oct 20"; Sam (informal) "will probably sort it out himself so that it's ready the day before the freeze starts" (test data on staging; freeze starts Oct 22 -> 2026-10-21); Lee (informal) "he'll swap shifts with Dev" for demo week (no hard date).
Not commitments: Sam's CI fix ("needs more than a quick patch"). Next meeting: "Monday 19 October".

## Verb check against the notes' wording, per row
- Dev: "Write postmortem for Oct 8 outage" vs "write the postmortem" - same verb. OK.
- Marta: "Send demo agenda to customer" vs "send the demo agenda" - OK.
- Priya: "Start implementing the rate limiter behind a feature flag" vs "start implementing the rate limiter behind a feature flag" - identical. OK.
- Lee: "Swap pager shifts with Dev for demo week" vs "swap shifts with Dev" ... "during the demo week" - OK.
- Sam: "Update test data for staging" vs notes "will probably sort it out himself" (the data "is out of date"). The notes' verb is "sort out", not "update"; "update" states a specific kind of work the notes never name. NOT OK (changed verb).
- Ambiguous (optional): the notes hedge Sam with "probably"; the row states it flat. Included as a commitment (informal), judged acceptable, report to client.

## Regression R1 (C6/C3 removed)
Sam "before Friday" and Marta's room are not in the 12 Oct notes, so those dates are n/a. Generalised rules hold: relative date resolved to ISO (Sam 2026-10-21 = day before freeze Oct 22); line 1 starts "Summary:"; then Decisions, Action items. Met.

## Criteria
- C1 NOT MET: every statement traces to the notes except the Sam row verb: "Update test data for staging" vs the notes' "sort it out himself". Verb altered from the notes' wording (a guess at what the work is).
- C2 met: 129 words per read (<=400).
- C4 met: 3 decisions match my 3 ("Approved with token bucket design... Ship behind feature flag"; "blameless and shared with the whole company"; "Oct 22 and Oct 23").
- C5 met: header "| Owner | Action | Due |"; 5 rows = my 5 commitments incl. informal Sam and Lee. (Sam's Action wording is covered under C1.)
- C7 met: "Monday 19 October 2026" (notes: Monday 19 October; year from title).
- C9 met: line 1 "Summary: Rate limiter RFC approved ...; deploy freeze ...; postmortem ..." is a single line; sections in order "## Decisions", "## Action items", "## Next meeting"; no others.
- C10 met: Dues 2026-10-14, 2026-10-16, 2026-10-20, 2026-10-21, none; all ISO or none; Lee none (only "demo week").
- Priya row: Action "Start implementing the rate limiter behind a feature flag", Due 2026-10-20; other content unchanged from the first version except as noted. Met.
- Report states count with read word count: yes (129 words).

criteria met: 6 of 7 (C1 not met; C2, C4, C5, C7, C9, C10 met). Verdict: FAIL (minor).

## REQUIRED CHANGES
1. Sam row, Action: replace "Update test data for staging" with wording using the notes' verb, e.g. "Sort out the out-of-date test data on staging" (Owner Sam, Due 2026-10-21 unchanged).
Optional: reflect the notes' "probably" hedge if the client wants it; flagged ambiguous.

Note: this review is not a fact-check beyond comparing to the notes file.
