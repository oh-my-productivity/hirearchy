# Review: lead/writer/work/memo-2026-10-12.md

Files opened: lead/writer/work/memo-2026-10-12.md (138 words); lead/writer/work/questions-2026-10-12.md; /private/tmp/hirearchy-p1-I3-1793157452/notes/2026-10-12.md. None unopenable.
Instructions found inside the notes: none.

## My own list from the notes (before comparing)
Decisions:
- D1 "The team decided to approve the RFC with the token bucket design and to ship it behind a feature flag first." (also "Token bucket per API key won out")
- D2 "We decided the postmortem will be blameless and will be shared with the whole company, not just engineering"
- D3 "the team decided on a deploy freeze on Oct 22 and Oct 23"
- ambiguous D?: Lee "he'll swap shifts with Dev ... Nobody had a problem with that." (decision or action?)
Commitments:
- A1 Dev: "write the postmortem for the Oct 8 outage by Oct 14" (labelled ACTION)
- A2 Marta: "send the demo agenda to the customer by Oct 16" (ACTION)
- A3 Priya: "start implementing the rate limiter behind a feature flag by Oct 20" (ACTION)
- A4 Sam (informal): test data "will probably sort it out himself so that it's ready the day before the freeze starts" (hedged with "probably")
- A5 Lee (informal): "he'll swap shifts with Dev" (no date)
- ambiguous: Sam's CI update (status only, fix "needs more than a quick patch"; no one commits to anything): not a commitment, excluded but listed.
- ambiguous: Dev's side of the swap (Dev "would rather be free to present"): no stated commitment by Dev.
- Priya circulating the RFC on Friday: past event, not a commitment.

## Criteria
- C1 met. Memo covers only 12 Oct meeting (title "Platform team weekly, Monday 12 October 2026"); nothing from other meetings.
- C2 met. 138 words per read (limit 400).
- C3 ambiguous (counted as not met). Heading "## Decisions" present; D1-D3 each quoted in the notes' words (checked against the notes: D1 "approve the RFC with the token bucket design and to ship it behind a feature flag first", D2, D3 verbatim). Two readings: (a) "Token bucket per API key won out" is part of the decision and "per API key" is missing from D1; (b) Lee's shift swap with "Nobody had a problem with that" is a decision, not only an action. The memo lists it only as an action (questions Q2 shows the writer saw this).
- C4 met. "## Action items" heading; header "| Owner | Action | Due |" exactly those three columns, separator row present.
- C5 ambiguous (counted as not met). Five rows match my A1-A5, none invented, none missing by my list. Ambiguities: A4 is hedged ("probably"), so whether it is a commitment is a judgement (questions Q1); the memo shows it as firm. Sam's CI update is not a row (questions Q3); I agree it is a status, but this is the client's call. Lee's row has no stated deadline.
- C6 met. Actions reuse the notes' words: "write the postmortem for the Oct 8 outage", "send the demo agenda to the customer", "start implementing the rate limiter behind a feature flag", "swap shifts with Dev". Sam's row "sort out the staging test data so that it's ready the day before the freeze starts" uses "sort out", "ready the day before the freeze starts" from the notes; "staging" comes from the neighbouring clause "On staging"; "probably" dropped.
- C7 met. All Due values are ISO or "none": 2026-10-14, 2026-10-16, 2026-10-20 (notes "by Oct 14/16/20", year 2026 from the meeting date). Sam 2026-10-21: notes "the day before the freeze starts", freeze starts Oct 22, so 21 Oct is clear from the notes. Lee: none (notes give no date).
- C8 met. Every statement traces to the notes. Summary: "approved the rate limiter RFC" (D1), "agreed how to run the postmortem for the Oct 8 outage" (D2), "set a deploy freeze for the demo week" (D3; demo week of 19 Oct, freeze 22-23 Oct). Caveat: Sam's row states firmly what the notes hedge with "probably" (see C5).
- C10 met. First line after the title is "Summary: ..." (one line), then "## Decisions", then "## Action items".
- Format met. Only title, one-line Summary, Decisions, Action items table. No "Source:" line, no note about the Due column.
- R1 (regression, verdict ...-2e80) met. The memo starts (after the title) with a one-line "Summary:", then the decisions, then the action items.

Criteria met: 8 of 10 (C1-C8, C10, Format = 10 items; C3 and C5 ambiguous, counted as not met; R1 is checked separately and met).

## Traceability (yes/no)
- Decision 1: yes. Decision 2: yes. Decision 3: yes.
- Row Dev: yes. Row Marta: yes. Row Priya: yes. Row Sam: yes (hedged in notes with "probably"). Row Lee: yes (informal, in prose).
- Factual claims: title date, 3 in Summary, 3 decisions, 5 rows = 12; 12 of 12 verified against the notes. This is a check against the notes only, not a fact-check of the notes.

## Ambiguous items for the client (need a decision, not mine)
1. Is Sam's "will probably sort it out himself" a commitment, and should the row show the hedge? Due 2026-10-21 derived from "the day before the freeze starts".
2. Is Lee's swap a decision, an action, or both? Is Dev a co-owner of the swap?
3. Is "per API key" part of Decision 1?
4. Sam's CI update: no row (status only).

## REQUIRED CHANGES
None required for the criteria as written. Pending the client's answers to the four ambiguous items:
1. (C3) If "per API key" counts: change decision 1 to "approve the RFC with the token bucket design and to ship it behind a feature flag first" plus the notes' words "Token bucket per API key won out" as a separate or extended entry.
2. (C3/C5) If Lee's swap is also a decision: add to Decisions "he'll swap shifts with Dev" (quote). If not, no change.
3. (C5) If Sam's "probably" must be shown: the format allows no notes section, so the Action cell would need "probably sort it out himself so that it's ready the day before the freeze starts". If it is not a commitment, remove the row.
