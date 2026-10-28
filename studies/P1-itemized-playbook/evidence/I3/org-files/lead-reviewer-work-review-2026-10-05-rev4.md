# Review rev4: memo-2026-10-05 (Summary line, C10)

Opened: lead/writer/work/memo-2026-10-05.md (199 words, 25 lines); /private/tmp/hirearchy-p1-I3-1793157452/notes/2026-10-05.md (source). Could not open: none.
No instruction found inside the notes file.

## My own list from the notes
Decisions ("we decided"):
- D1 push the gateway migration to the week of 26 October and use the extra time for the failing services
- D2 adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable
Commitments:
- A1 Priya: draft the RFC for the new per-key rate limiter by Oct 9 (ACTION)
- A2 Dev: enable Renovate on the three core repos by Oct 8 (ACTION)
- A3 Sam: "he'd look into the flaky CI before Friday" (informal; Friday = 2026-10-09)
- A4 Marta: book the on-call training room for Oct 14 (ACTION; Oct 14 is the training date, not stated as a deadline)
- A5 Lee: "We agreed Lee would ping the vendor about it this week and report back, no hard date attached" (informal)
Ambiguous:
- X1 Priya's RFC: "the team can review it at the following meeting" (team step, no owner or date; memo omits it, lead says deliberate)
- X2 Lee's agreement could count as a decision ("We agreed") as well as a commitment; memo lists it only as an action.
- X3 Lee "about it": referent is the SSO certificate renewal; memo keeps "about it" without naming it.

## Criteria
- C1 met. Only the 2026-10-05 meeting; header matches the notes title.
- C2 met. 199 words (read), limit 400.
- C3 met. Section "## Decisions"; D1 and D2 quoted verbatim from the notes; none missing (see X2).
- C4 met. "## Action items" with header `| Owner | Action | Due |`, exactly these three columns.
- C5 met. 5 rows = A1-A5; no invented row, none missing from my list. Initials-only owners: none in this file. X1 omitted (ambiguous, see above).
- C6 met. Actions match the notes' words: "draft the RFC for the new per-key rate limiter", "enable Renovate on the three core repos", "look into the flaky CI before Friday", "book the on-call training room for Oct 14", "ping the vendor about it this week and report back" (X3).
- C7 ambiguous. All values are ISO. Priya 2026-10-09, Dev 2026-10-08 and Lee "none" match the notes. Sam 2026-10-09: the notes say "before Friday" (Friday = 2026-10-09); read literally C7 gives 2026-10-08 or none, so 2026-10-09 comes from the user's answer, not from the notes. Marta 2026-10-14: the notes give a training date, not a deadline; read literally C7 gives none. Both are disclosed in the memo's Due notes. I cannot decide whether a user answer overrides C7; lead decides.
- C8 ambiguous. All statements trace to the notes (summary "five people took action items" = Priya, Dev, Sam, Marta, Lee; "Present" line; decision reasons) except the Due notes line "these dates were set by the user", which is not in the notes. Same open question as C7.
- C10 ambiguous. Summary is present, one line, starts with "Summary:": "Summary: The team decided to push the gateway migration to the week of 26 October and to adopt Renovate, and five people took action items." Order Summary, then "## Decisions", then "## Action items" is correct, and R1 order is respected. But the memo's first line is the title "# Memo: ...", and a "Source: ..." line sits between the Summary and Decisions. Read strictly ("starts with", "followed by"), neither is allowed; read as body structure, both are fine. Lead decides.

## R1 (client rejection of C10)
Summary line now exists and the order is Summary, Decisions, Action items: addressed in substance. The strict-reading question is the same as C10.

## REQUIRED CHANGES
None required under the reading that the title and Source line are allowed and the user's answers set the Sam and Marta dates.
If lead rules the strict readings apply (in severity order):
1. C7/C8: Sam Due -> `2026-10-08` or `none`; Marta Due -> `none`; delete the first bullet under "Notes on the Due column" (or lead confirms the user's dates override C7).
2. C10: make "Summary: ..." the first line of the file (title removed or moved below it) and move the "Source: ..." line after the Action items table or into the Summary.

## Not fact-checked
The memo's claims are checked against the notes only; the user's answers on the dates are not visible to me.

criteria met: 6 of 9 (C1-C6 met; C7, C8, C10 ambiguous, not counted)
