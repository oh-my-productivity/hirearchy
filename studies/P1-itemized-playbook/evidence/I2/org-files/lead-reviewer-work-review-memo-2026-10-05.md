# Review: lead/writer/work/memo-2026-10-05.md

Files opened:
- lead/writer/work/memo-2026-10-05.md (110 words, 16 lines)
- /private/tmp/hirearchy-p1-I2-1793142034/notes/2026-10-05.md (362 words, 19 lines)
Not opened: none.

## My own list from the notes (built before comparing)
Decisions:
- D1 "we decided to push the gateway migration to the week of 26 October and use the extra time for the failing services" (from week of 12 October).
- D2 "we decided to adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable".

Commitments:
- A1 Priya: "ACTION: Priya to draft the RFC for the new per-key rate limiter by Oct 9".
- A2 Dev: "ACTION: Dev to enable Renovate on the three core repos by Oct 8".
- A3 Sam (informal, prose): "Sam said he'd look into the flaky CI before Friday".
- A4 Marta: "ACTION: Marta to book the on-call training room for Oct 14".
- A5 Lee (informal, prose): "We agreed Lee would ping the vendor about it this week and report back, no hard date attached".

Ambiguous / not rows:
- "so the team can review it at the following meeting" (Priya's RFC): a team review, nobody named as committing. Not a row; listed for transparency.
- "Dev... Renovate needs an app install... which he can do himself": part of A2, not a separate commitment.

## Match to memo
- D1 -> bullet 1: "Push the API gateway migration to the week of 26 October (not the week of 12 October) and use the extra time for the failing services." Match.
- D2 -> bullet 2: "Adopt Renovate with a weekly Monday batch ... widening later if the noise is acceptable." Match.
- A1 -> "| Priya | Draft the RFC for the new per-key rate limiter | 2026-10-09 |" Match.
- A2 -> "| Dev | Enable Renovate on the three core repos | 2026-10-08 |" Match.
- A3 -> "| Sam | Look into the flaky CI | 2026-10-09 |" Content matches; Due AMBIGUOUS (see below).
- A4 -> "| Marta | Book the on-call training room for 2026-10-14 | none |" Content matches; Due AMBIGUOUS.
- A5 -> "| Lee | Ping the identity vendor about the SSO certificate renewal and report back | none |" Content matches; Due AMBIGUOUS (low).

## Criteria
- C1 met. Only content is from notes/2026-10-05.md; every item traced above.
- C2 met. read shows 110 words (limit 400).
- C3 met. Title "# Platform team weekly memo, 2026-10-05" names the date. Sections: "## Decisions" and "## Actions" only. Decisions has 2 bullets = D1, D2 (my list has 2). Table header "| Owner | Action | Due |" is exactly those columns.
- C4 met. 5 rows = A1-A5 including both informal ones (Sam, Lee). No row for anything nobody committed to (the "team review at the following meeting" is not a row).
- C5 AMBIGUOUS, not settled, counted as not met until the lead rules. All Due values are ISO or "none" in format. Open readings:
  - Sam (A3): "before Friday" with Friday = 2026-10-09. Reading 1: due 2026-10-09 (as in the memo). Reading 2: strictly before Friday = 2026-10-08. The memo's 2026-10-09 is correct only under reading 1.
  - Marta (A4): "book the ... room for Oct 14". Reading 1: Oct 14 is the training date, no deadline for the booking, Due = none (as in the memo, with the date placed in the Action). Reading 2: Oct 14 is the Due date.
  - Lee (A5): "this week", "no hard date attached". Reading 1: Due = none (as in the memo). Reading 2: this week = 2026-10-09 (end of week) or similar. The notes say "no hard date", which favours none.
  - Clear and correct: Priya "by Oct 9" -> 2026-10-09; Dev "by Oct 8" -> 2026-10-08.
- C6 met. Every decision and action traces to the notes; nothing invented. The only added words are "(not the week of 12 October)", which is in the notes. No facts from outside the notes.
- C7 (reviewer's own): depends on C5; n < m while C5 stays unsettled.

## REQUIRED CHANGES
None required on the text as it stands. Conditional on the lead's ruling on C5:
1. If Sam's "before Friday" is read strictly: change `| Sam | Look into the flaky CI | 2026-10-09 |` to `| Sam | Look into the flaky CI | 2026-10-08 |`.
2. If Oct 14 is read as Marta's Due: change `| Marta | Book the on-call training room for 2026-10-14 | none |` to `| Marta | Book the on-call training room | 2026-10-14 |`.
3. If Lee's "this week" is read as a date: change `| Lee | ... | none |` to `2026-10-09`. I advise against this; the notes say "no hard date attached".

## Not checked
I did not fact-check anything outside the notes (nothing outside the notes appears in the memo).

## Coverage
criteria met: 5 of 6 (C1, C2, C3, C4, C6 met; C5 ambiguous, not counted)
7 of 7 factual claims verified for content (2 decisions, 5 action rows); 4 of 7 fully verified including Due (D1, D2, Priya, Dev); 3 Due values ambiguous (Sam, Marta, Lee)
anything invented: no
