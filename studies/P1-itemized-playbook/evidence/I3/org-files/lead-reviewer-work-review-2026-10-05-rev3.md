# Review 3: memo-2026-10-05 (Due values rework)

Opened: lead/writer/work/memo-2026-10-05.md (200 words per read); /private/tmp/hirearchy-p1-I3-1793157452/notes/2026-10-05.md. Could not open: none.
No instructions found in the notes file.

## My own list from the notes (before comparing)
Decisions (2):
- D1 "push the gateway migration to the week of 26 October and use the extra time for the failing services"
- D2 "adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable"

Commitments (5) and the notes' Due text:
- Priya: draft the RFC for the new per-key rate limiter, "by Oct 9" (stated date)
- Dev: enable Renovate on the three core repos, "by Oct 8" (stated date)
- Sam (informal): "he'd look into the flaky CI before Friday" (relative deadline)
- Marta: book the on-call training room, "for Oct 14" (date of the training, not stated as a booking deadline)
- Lee (informal): "Lee would ping the vendor about it this week and report back, no hard date attached"

Ambiguous (not decided by me):
- A1: Priya's RFC is to be reviewed "by the team ... at the following meeting". No owner or action named; the memo omits it. Judged earlier by the user as omitted.
- A2: Sam "before Friday" resolved to 2026-10-08. This is an interpretation (last day before Friday, Thursday). The requester allowed it if the derivation is in Open questions, and it is. Someone could read "before Friday" as "by Friday".
- A3: Lee's "this week" is a relative phrase; the notes themselves say "no hard date attached", so none fits. Not converted.
- A4: Lee's Action says "about it"; the referent (SSO certificate renewal) is in the notes but not in the memo, so the row is unclear alone. It is the notes' own wording (C6), so I do not require a change.

## Due value check (every row, against notes text)
| Owner | Memo Due | Notes text | Result |
|---|---|---|---|
| Priya | 2026-10-09 | "by Oct 9"; meeting year 2026 from title | correct |
| Dev | 2026-10-08 | "by Oct 8" | correct |
| Sam | 2026-10-08 | "before Friday"; meeting Mon 5 Oct 2026, Friday = 9 Oct | acceptable per requester; derivation in Open questions (see A2) |
| Marta | none | "for Oct 14", no booking deadline | correct; Open questions says 14 Oct is the training date and no booking deadline is given |
| Lee | none | "this week ... no hard date attached" | correct; Open questions quotes "no hard date attached" |

Open questions section: Sam, Marta and Lee entries each match the notes. The Sam entry's statement "Friday is 2026-10-09" is correct (5 Oct 2026 is a Monday per the notes). Priya and Dev have no entry, and need none.

## Criteria
- C1 met. Only the 5 Oct 2026 meeting; header "Platform team weekly, Monday 5 October 2026"; no other meeting content (the 12 Oct next-meeting mention is not used, and 12 Oct appears only inside Decision 1's reason, quoted from the notes).
- C2 met. 200 words (limit 400).
- C3 met. Section "## Decisions" lists D1 and D2; the quoted text matches the notes character for character. The added "Reason in the notes: ..." sentence is also from the notes ("two of the five services still fail the contract tests", "nobody was comfortable cutting over in the week of 12 October").
- C4 met. Section "## Action items"; header row "| Owner | Action | Due |"; exactly 3 columns.
- C5 met. 5 rows = my 5 commitments (Priya, Dev, Sam, Marta, Lee), including the informal Sam and Lee rows; no invented row. A1 is ambiguous and omitted, listed above.
- C6 met. Actions match the notes' wording ("draft the RFC for the new per-key rate limiter", "enable Renovate on the three core repos", "look into the flaky CI before Friday", "book the on-call training room for Oct 14", "ping the vendor about it this week and report back").
- C7 met. Format ISO or none in all 5 rows: 2026-10-09, 2026-10-08, 2026-10-08, none, none. Marta and Lee are none as required; Sam's conversion is derived and disclosed (A2).
- C8 met. Every statement traces to the notes; the Open questions statements are derivations from the meeting date in the notes.

## REQUIRED CHANGES
None.

Optional: (a) Lee's row could name the SSO certificate renewal in Open questions so "about it" is clear; (b) mention that the RFC review at the following meeting is not an action item.

Not a fact-check: I compared against the notes only; the notes' own claims (e.g. three incidents, one run in eight) are not in the memo and were not verified.

criteria met: 8 of 8
