# Review: memo 2026-10-12

Files opened:
- lead/writer/work/memo-2026-10-12.md (memo, about 165 words by my count; header, separator and pipes excluded)
- /private/tmp/hirearchy-e7-s2-1792914064/notes/2026-10-12.md (source)
None I could not open.

## My own list from the notes (before comparing)
Decisions (3):
- D1: approve the rate limiter RFC with the token bucket (per API key) design, ship behind a feature flag first.
- D2: postmortem (Oct 8 outage) blameless, shared with the whole company, not just engineering.
- D3: deploy freeze on Oct 22 and Oct 23 (demo environment is the same cluster).

Commitments (5):
- A1: Dev writes the postmortem for the Oct 8 outage by Oct 14 -> 2026-10-14.
- A2: Marta sends the demo agenda to the customer by Oct 16 -> 2026-10-16.
- A3: Priya starts implementing the rate limiter behind a feature flag by Oct 20 -> 2026-10-20.
- A4 (informal): Sam "will probably sort it out himself" (out-of-date staging test data) "so that it's ready the day before the freeze starts" -> freeze starts Oct 22, so 2026-10-21.
- A5 (informal): Lee "he'll swap shifts with Dev" (pager, demo week, week of 19 Oct) -> no hard date, so none.

Not commitments / ambiguous:
- AMBIGUOUS-1: Sam's CI runner image fix ("needs more than a quick patch") is a status, nobody said they would do it. Memo has no row. I treat it as not a commitment but list it for the client.
- AMBIGUOUS-2: Sam's staging item is hedged ("will probably"). The memo includes it as a row; I consider it a commitment, but the hedge is the client's call.
- AMBIGUOUS-3: Lee's Due. "during the demo week" is a period, not a date. Under the ruling "'this week' with no hard date ... is 'none'" the memo's 'none' is right. A reader could instead take the event-date ruling (demo week = week of 19 Oct), but no single date can be resolved either way.
- Dev's side of the swap ("Dev, who would rather be free to present") is a preference, not a commitment. No row for Dev is correct.
- Priya "ready to start building" is covered by A3.

## Criteria
- C1 met. Only the Oct 12 meeting content: Oct 8 outage, demo week, freeze, all in the file. Nothing from other files.
- C2 met. Decisions section has exactly D1-D3: "Approve the rate limiter RFC with the token bucket design (per API key) and ship it behind a feature flag first."; "The postmortem for the Oct 8 outage will be blameless and shared with the whole company, not just engineering."; "Deploy freeze on Oct 22 and Oct 23, because the demo environment is the same cluster the team deploys to." No extra decision.
- C3 met. Rows for A1-A5, owners Dev, Marta, Priya, Sam, Lee, each the committing person. Nothing missing against my list (AMBIGUOUS-1 excluded as not a commitment).
- C4 met. Header "| Owner | Action | Due |", exactly three columns, markdown table.
- C5 met. Dev 2026-10-14, Marta 2026-10-16, Priya 2026-10-20 (notes' dates, ISO). Sam 2026-10-21 (day before Oct 22 freeze). Lee none. All verified against the notes and the client rulings.
- C6 met. About 165 words (summary 33, decisions about 62, table about 70), limit 400.
- C7 met. All other criteria are met and I require no changes, so no writer rework is outstanding.
- C8 met. First line is "Summary: Platform team weekly on 12 October 2026: ..." (one line), then "## Decisions", then "## Actions" with the table. No 'Open questions' section.
- R1 met. Same as C8: Summary line first, then decisions, then action items.

criteria met: 9 of 9 (C1-C8 plus R1)

## Factual claims checked (12)
Summary: meeting 12 October 2026 platform team weekly; RFC approved; Oct 8 postmortem blameless; freeze Oct 22 and 23. Decisions D1-D3 (one claim each). Rows A1-A5 (owner, action and due each, one claim per row). All 12 match the notes.
n of m factual claims verified: 12 of 12.

## REQUIRED CHANGES
None.

Note: a reviewer's pass is not a fact-check beyond comparison with the notes file; I did not check the notes against any outside source.
