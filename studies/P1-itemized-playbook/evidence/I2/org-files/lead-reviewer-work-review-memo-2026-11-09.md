# Review: memo 2026-11-09

Opened: lead/writer/work/memo-2026-11-09.md (111 words per read); /private/tmp/hirearchy-p1-I2-1793142034/notes/2026-11-09.md (175 words). Nothing I could not open. I edited neither file.

## My own list from the notes (before comparing)
Meeting: Monday 2026-11-09 (header "Monday 9 November 2026"). Weekday check: Fri = 2026-11-13, Fri = 2026-11-20, Mon = 2026-11-16.

Decisions (3, each marked "we decided"):
- D1 "move the switch-off of the old gateway to Friday 20 November"
- D2 "we decided to approve it [Priya's rate limiter rollout plan] as written"
- D3 "We decided that Jo joins the on-call rotation from Monday 16 November"

Commitments (5):
- A1 "ACTION: Marta to circulate the quarterly review notes by Nov 11" -> 2026-11-11
- A2 "ACTION: Dev to switch off the old gateway on Nov 20" -> 2026-11-20
- A3 "ACTION: Priya to start the rate limiter rollout to all plans on Nov 16" -> 2026-11-16
- A4 (prose) "Sam said he would add Jo to the on-call rotation by Friday" -> Friday after Mon 2026-11-09 = 2026-11-13
- A5 (prose) "Lee said he'd go through the SSO audit log at some point to check for old service accounts. No date was given." -> none

Not commitments: customer confirmed review for Wednesday; deck went out; Dev's request for a week; Jo finished CI onboarding; meeting closed 14:40; next meeting Monday 16 November.

## Criteria
- C1 met. Every item in the memo traces to the 2026-11-09 notes; no other source content seen.
- C2 met. read: 111 words (limit 400).
- C3 met. Sections: title "# Platform team weekly memo, 2026-11-09" (names the date), "## Decisions", "## Actions". Decisions has 3 bullets = D1-D3. Table header "| Owner | Action | Due |" exactly. No other sections (Summary is a line, not a section; see C8).
- C4 met. 5 rows = A1-A5, incl. prose items Sam and Lee. No row for the Wednesday review, Jo's onboarding, or the next meeting.
- C5 met. Marta 2026-11-11 ("by Nov 11"); Dev 2026-11-20 ("on Nov 20"); Priya 2026-11-16 ("on Nov 16"); Sam 2026-11-13 ("by Friday", meeting Monday 2026-11-09); Lee none ("No date was given"). All ISO.
- C6 met. Each decision and row matches the notes (table below). Nothing invented. The Summary phrase "five actions were assigned" matches the 5 rows.
- C7 not counted (concerns this report).
- C8 met. Line 3 "Summary: The old gateway switch-off moves to 20 November, the rate limiter rollout plan is approved, Jo joins on-call from 16 November, and five actions were assigned." is one line, directly after the title, followed by Decisions then Actions; nothing else added.
- C10 met under lead's earlier ruling (owners as written in the notes; the notes have first names only: Priya, Sam, Lee, Marta, Dev). Owner cells: Marta, Dev, Priya, Sam, Lee. See ambiguity 1.
- C11 met (vacuously). No owner is given as initials only, so no cell needs "(full name not in the notes)". None added; correct.

Regression list:
- R1 met (Summary first, then decisions, then actions).
- R2 ("Owners as initials only, always") conflicts with R3/C10 and is a removed criterion (C9). Memo uses names, not initials. Not judged as a defect; see ambiguity 2.
- R3 met under the same reading as C10 (names as written in notes, never initials). See ambiguity 1.
- R4 not triggered: no initials-only owner in the notes.

## Factual claims verified (8 of 8)
| Item | Memo | Notes | OK |
|---|---|---|---|
| D1 | Move switch-off of old gateway to Friday 20 November | same | yes |
| D2 | Approve Priya's rate limiter rollout plan as written | same | yes |
| D3 | Jo joins on-call from Monday 16 November | same | yes |
| A1 | Marta / circulate quarterly review notes / 2026-11-11 | by Nov 11 | yes |
| A2 | Dev / switch off old gateway / 2026-11-20 | on Nov 20 | yes |
| A3 | Priya / start rate limiter rollout to all plans / 2026-11-16 | on Nov 16 | yes |
| A4 | Sam / add Jo to on-call rotation / 2026-11-13 | by Friday | yes (see ambiguity 3) |
| A5 | Lee / go through SSO audit log to check for old service accounts / none | no date given | yes |

## REQUIRED CHANGES
None.

## Ambiguous (not settled by me)
1. C10/R3 with first-name-only owners: "full name as written in the notes" can mean (a) the name exactly as written, i.e. first name, or (b) a full first+last name, which the notes never give. I read (a), following lead's earlier ruling for memos 2026-10-26 and 2026-11-02. Under (b) C10 could not be met by any text from the notes.
2. R2 ("initials only, always") contradicts R3/C10; C9 is removed. I did not apply it.
3. A4 "by Friday": the notes do not say which Friday. I read it as the Friday of the meeting week (2026-11-13), the nearest one after the Monday meeting. 2026-11-20 is a possible alternative reading, though less natural.
4. D3 and A4 overlap in subject (Jo on-call); I treated D3 as a decision and A4 as Sam's commitment, as the notes label them. Not a defect.

## Not checked
Real-world facts (e.g. whether 20 November 2026 is a Friday) beyond the calendar check above; this review is not a fact-check of the notes' own claims.

criteria met: 8 of 8 (C1-C6, C8, C10, C11; C7 excluded as it concerns this report). Verdict: pass, with ambiguities 1-3 above for lead.
8 of 8 factual claims verified.
