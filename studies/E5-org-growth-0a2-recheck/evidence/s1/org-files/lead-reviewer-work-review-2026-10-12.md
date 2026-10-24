# Review: memo 2026-10-12

Files opened: lead/writer/work/memo-2026-10-12.md (148 words, read); /private/tmp/hirearchy-e5-s1-1792811051/notes/2026-10-12.md (opened). None unopened.

## My own list from the notes
Decisions:
- D1 Approve rate limiter RFC, token bucket per API key, ship behind feature flag first ("The team decided...").
- D2 Postmortem blameless, shared with whole company ("We decided...").
- D3 Deploy freeze Oct 22 and Oct 23 ("the team decided on a deploy freeze").
- D4 (ambiguous) Lee swaps pager shifts with Dev for demo week: "Nobody had a problem with that". Informal agreement; memo records it as an action only, not under Decisions.
Commitments:
- A1 Dev: write Oct 8 postmortem by Oct 14 (ACTION).
- A2 Marta: send demo agenda to customer by Oct 16 (ACTION).
- A3 Priya: start implementing rate limiter behind flag by Oct 20 (ACTION).
- A4 Sam: sort out out-of-date staging test data himself ("will probably sort it out himself so that it's ready the day before the freeze starts"). Unlabelled, hedged. Freeze starts Oct 22, so day before = 2026-10-21.
- A5 Lee: carry pager during demo week, swap shifts with Dev ("he'll swap shifts with Dev"). Unlabelled. Demo week = week of 19 Oct, no single date.
Not commitments: Sam's CI update (no one commits to a fix; "needs more than a quick patch"), Dev "would rather be free to present", next meeting Monday 19 Oct.

## Criteria
- C1 met. Every memo statement traces to the notes (RFC, outage Oct 8 billing service, freeze rationale, all five items). No outside facts found.
- C2 met. 148 words from read, limit 400.
- C3 met. Markdown, "## Decisions" lists D1-D3, including the two not labelled (the notes have no labels on decisions). D4 ambiguous, see below.
- C4 met. Header is exactly `| Owner | Action | Due |`.
- C5 met. All five commitments A1-A5 present, owner is the person who made each. Sam and Lee (unlabelled, prose) included.
- C6 met. Due values: 2026-10-14, 2026-10-16, 2026-10-20, 2026-10-21, none. Dev/Marta/Priya dates match "Oct 14/16/20" (year 2026 from title). Sam 2026-10-21: notes say "the day before the freeze starts", freeze is Oct 22, so the date is clear. Lee none: "demo week" is a range, no single date, correct.
- C8 met. Line 1 is "Summary: Platform team weekly, ..." (one line), then "## Decisions", then "## Action items" table. Order correct.
- R1 (Summary first, then decisions, then actions): met, same as C8.

criteria met: 8 of 8 as listed (C1-C6, C8); C7 is the lead's.

## REQUIRED CHANGES
none

## Ambiguous (reported, not decided)
1. D4: whether the Lee/Dev pager swap ("Nobody had a problem with that") is also a decision to list under Decisions. Memo has it only as an action row. Optional.
2. The memo ends with an extra line "Open question: Sam's staging commitment was stated as \"probably\"." after the table. C8 fixes the order of Summary, Decisions, table but does not say whether anything may follow. The line is supported by the notes. Also the hedge is already in the Sam row.
3. Sam's Due 2026-10-21 relies on inferring the freeze start date from D3; I judge it clear, but a stricter reader could say "day before the freeze" is relative.
4. Summary says "deploy freeze set for demo week"; the freeze is Oct 22-23 within the week of 19 Oct, not the whole week. Minor wording, not a criterion failure.

No factual claims beyond the notes were checked; this is not a fact-check beyond comparison with the notes.
