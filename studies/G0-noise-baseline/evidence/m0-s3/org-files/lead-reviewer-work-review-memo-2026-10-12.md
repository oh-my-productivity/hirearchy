# Review: memo-2026-10-12

Opened: lead/writer/work/memo-2026-10-12.md (182 words per org_read, 21 lines); /private/tmp/hirearchy-g0-m0-s3-1793000481/notes/2026-10-12.md (read in full). Nothing could not be opened.

## My own list from the notes (before comparing)
Decisions (3):
- D1 Approve rate limiter RFC, token bucket per API key, ship behind a feature flag first.
- D2 Oct 8 outage postmortem blameless, shared with whole company, not only engineering.
- D3 Deploy freeze Oct 22 and Oct 23 (customer demo week of 19 Oct).
Commitments (5 clear/likely + 1 ambiguous):
- A1 Dev: write postmortem by Oct 14 (labelled ACTION).
- A2 Marta: send demo agenda to customer by Oct 16 (ACTION).
- A3 Priya: start implementing rate limiter behind flag by Oct 20 (ACTION).
- A4 Sam: staging test data out of date, "will probably sort it out himself so that it's ready the day before the freeze starts" (prose; hedged). Day before Oct 22 = Oct 21.
- A5 Lee: "he'll swap shifts with Dev" / carry pager during demo week (prose). No single day.
- Not commitments: Sam's CI update (cache theory held up, fix needs more than a quick patch: status only, no one commits); Dev "would rather be free to present" (preference); meeting closed 10:50.

## Criteria
- C1 met. Only the 12 Oct meeting; all content (RFC, Oct 8 outage, freeze, demo, staging, pager, next meeting 19 Oct) is in the 12 Oct notes.
- C2 met. 182 words per read (limit 400).
- C3 met. "## Decisions" has 3 bullets matching D1-D3; no decision outside the notes. D3 adds "for the customer demo in the week of 19 October", which is in the notes.
- C4 met. "## Action items" holds a table with header `| Owner | Action | Due |`, exactly those 3 columns.
- C5 met (with ambiguity A-1, A-2). 5 rows: Dev, Marta, Priya, Sam, Lee = A1-A5. No row for CI status or Dev's preference. No row for something nobody committed to, except as per A-1.
- C6 met. Dev 2026-10-14, Marta 2026-10-16, Priya 2026-10-20 (all match notes' Oct 14/16/20, year 2026 from the notes title). Sam 2026-10-21 (freeze starts Oct 22, day before = Oct 21: correct). Lee `none` ("demo week" is a week, not a single day). All values ISO or none.
- C7 met. Every statement traces to the notes; checked incl. "Oct 8 billing service outage" (notes: "last Thursday's outage", billing service, and Oct 8 in the ACTION), Attendees (Present line) and Next meeting (closing line). Nothing added from outside.
- C9 met. Line 1 is "Summary: The team approved ..." (one line), then "## Decisions", then "## Action items".
- Requester note met. Summary is the very first line, no title line. Decisions then Action items follow. Attendees and Next meeting appear only after the table.
- R1 (regression) met: "Always start the memo with a one-line 'Summary:' of the meeting, then the decisions, then the action items." Order is exactly that. Earlier failures (title line before Summary; Attendees between Summary and Decisions) are gone.

criteria met: 8 of 8

## Judgement calls asked
1. Sam staging row: a commitment on a reasonable reading (he said he will sort it out himself, with a target); hedged by "probably". Date 2026-10-21 is right. The row text carries the hedge "(said he will probably do it himself)". Listed as ambiguous A-1 for lead.
2. Lee: row with Due none is correct under C6 (demo week is not a single day). Commitment is plain ("he'll swap shifts with Dev"). Ambiguity A-2: the memo says "Carry the pager during demo week by swapping shifts with Dev"; the notes say Lee doesn't mind carrying the pager and will swap shifts. Faithful, no change required.
3. Sam CI update: status only, no row: agree.
4. Missing/extra: none found.

## Ambiguous items (left to lead)
- A-1: Sam's hedged staging commitment ("will probably"): row kept; a stricter reading of "no row for something nobody committed to" could drop it. I read it as a commitment because he states what he will do and by when.
- A-2: Lee's pager/swap: Due none; if lead reads "demo week" as pointing to a single day it would not; it does not.
- A-3: Sam's CI follow-up ("needs more than a quick patch"): implies future work but no one commits; not a row.
- A-4: Summary line is one line but long (about 40 words); no limit stated, so fine.
- A-5: Attendees and Next meeting lines: allowed by the requester note only after the table; they are, but are not required by any criterion.

## REQUIRED CHANGES
None.

Not asked / not fact-checked: the notes' own facts (e.g. that Oct 8 was a Thursday, the outage duration) were not checked against outside sources; the memo omits the forty-minute duration anyway.
