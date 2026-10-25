# Review: memo 2026-10-12

Opened: lead/writer/work/memo-2026-10-12.md (176 words, 19 lines, per hirearchy org_read); /private/tmp/hirearchy-e7-s1-1792911600/notes/2026-10-12.md (read in full). No other notes file opened. Nothing I could not open.

## My own list from the notes (before comparing)
Decisions (stated as decided):
- D1 "The team decided to approve the RFC with the token bucket design and to ship it behind a feature flag first."
- D2 "We decided the postmortem will be blameless and will be shared with the whole company, not just engineering"
- D3 "the team decided on a deploy freeze on Oct 22 and Oct 23 so nothing changes under the presenter"
- Ambiguous: "Nobody had a problem with that" (Lee swaps shifts with Dev): agreement, not labelled decided. Memo does not list it as a decision (fine under C3 if it is not a decision).
Commitments:
- A1 Dev: write postmortem for Oct 8 outage by Oct 14 (ACTION)
- A2 Marta: send demo agenda to customer by Oct 16 (ACTION)
- A3 Priya: start implementing rate limiter behind feature flag by Oct 20 (ACTION)
- A4 Sam (prose): "will probably sort it out himself so that it's ready the day before the freeze starts" (staging test data)
- A5 Lee (prose): "doesn't mind carrying the pager during the demo week, so he'll swap shifts with Dev"
- Not commitments: Sam's CI fix ("needs more than a quick patch", nobody commits); Dev "would rather be free to present" (preference, no action stated).

## Per criterion
- C1 met. Every memo fact appears in the 2026-10-12 notes (e.g. "Oct 8 outage", "Oct 22 and Oct 23", "token bucket per API key"); no content from another meeting.
- C3 met. Three bullets match D1-D3 one-to-one; no bullet the notes present as undecided. Quote: "Approve the rate limiter RFC with the token bucket per API key design, and ship it behind a feature flag first."
- C4 met. Header "| Owner | Action | Due |"; five rows for A1-A5, including prose rows Sam and Lee. Subject to ambiguity 1 and 2 below.
- C5 met. Owners Dev, Marta, Priya, Sam, Lee are all in the "Present:" line and the text.
- C6 met, with ambiguity 3. Dev 2026-10-14 (notes "by Oct 14"), Marta 2026-10-16 ("by Oct 16"), Priya 2026-10-20 ("by Oct 20"); year 2026 from the notes title. Sam 2026-10-21: "the day before the freeze starts", freeze starts Oct 22, so Oct 21. Lee none: "during the demo week" gives no single day.
- C7 met. 176 words per read, limit 400.
- C9 met. Title line "# Platform team weekly memo, 2026-10-12", then one-line "Summary: ..." (single line), then "## Decisions", then "## Actions", nothing else. R1 regression: passes (Summary line first, then decisions, then actions).

Criteria met: 7 of 7. Verdict: pass.

## Factual claims: 14 of 14 verified (judgement: yes)
Checked against the notes: token bucket per API key; feature flag first; RFC approved; postmortem blameless; shared with whole company not just engineering; Oct 8 outage ("last Thursday", Oct 12 is Monday, so Thursday is Oct 8; the notes' own action text says Oct 8); freeze Oct 22 and 23; reason nothing changes under the presenter; demo is a customer demo; Dev/Marta/Priya tasks and dates; Sam staging test data out of date; Lee swaps shifts with Dev for demo week. This is limited to what the memo states; I did not check the notes themselves against any outside source.

## Ambiguous (not decided by me)
1. Sam's commitment is hedged ("will probably sort it out himself"). Whether a hedged statement is a commitment: I list it as one; the memo includes it and flags the hedge in the Action cell.
2. Lee's row: stated as "doesn't mind" + "he'll swap shifts with Dev". Counted as a commitment. Dev's agreement is implicit ("would rather be free"); no row for Dev, which I judge correct but flag.
3. Due for Sam: "the day before the freeze starts" is a day relative to the freeze date (Oct 22), not counted from the meeting date as C6 words it. It gives one clear day (2026-10-21). Whether this fits C6's "counted from the meeting date" is open; the alternative is none.
4. Lee: "demo week" (the week of 19 October) gives no single day, so none. The alternative reading (a date range) would still not be one day.
5. Memo's Sam Action cell contains a parenthetical "(said he will probably do it himself)", which is attribution commentary inside the table cell, not a criterion violation.

## REQUIRED CHANGES
None. Optional: if the client reads C6 strictly (counted from the meeting date), change Sam's Due from 2026-10-21 to none; if hedged statements are not commitments, drop the Sam row.
