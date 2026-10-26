# Review: memo-2026-10-05 (task 20261026T065858934710-lead-89ad)

Files opened:
- lead/writer/work/memo-2026-10-05.md (145 words per read)
- /private/tmp/hirearchy-g0-m1-s2-1792997653/notes/2026-10-05.md (362 words per read)
Not opened: none.

## My own enumeration from the notes (before comparing)
Decisions:
- D1: "we decided to push the gateway migration to the week of 26 October" (from week of 12 Oct). No owner.
- D2: "we decided to adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable." No owner.
- No other decisions. ("Nobody objected" on Sam's CI item is not a decision; the room need and SSO expiry are context.)

Commitments:
- A1: Priya, draft RFC for per-key rate limiter, "by Oct 9" (ACTION).
- A2: Dev, enable Renovate on the three core repos, "by Oct 8" (ACTION).
- A3: Sam, "he'd look into the flaky CI before Friday" (prose).
- A4: Marta, book the on-call training room "for Oct 14" (ACTION).
- A5: Lee, "ping the vendor about it this week and report back, no hard date attached" (prose).
Total: 2 decisions, 5 commitments. Year is 2026 (heading "Monday 5 October 2026"); Oct 8 and Oct 9 2026 are Thu and Fri of the same week.

## Criteria
- C1 (only this meeting, only decisions and who does what): met. Source line names notes/2026-10-05.md; content is only D1, D2, A1-A5. Minor: the trailing "Notes on dates" paragraph is commentary, not a decision or an action (optional trim, see below).
- C2 (at most 400 words): met. read shows 145 words.
- C3 (section "Decisions" lists every decision): met. "## Decisions" has 2 bullets matching D1 and D2 ("Push the API gateway migration to the week of 26 October ...", "Adopt Renovate with a weekly Monday batch ..."). No decision missed.
- C4 (table with exactly Owner | Action | Due, one row per commitment, informal included): met. Header is "| Owner | Action | Due |". 5 rows = A1-A5 (Sam and Lee are the prose ones, both present). No duplicates, none missing.
- C5 (Due is ISO; vague only converted when clear; else none; none when no date): AMBIGUOUS, not counted as met.
  - Priya 2026-10-09 and Dev 2026-10-08: met ("by Oct 9", "by Oct 8").
  - Lee none: met ("no hard date attached"; "this week" is explicitly not a hard date).
  - Sam none: ambiguous. "before Friday" in a meeting held Monday 5 Oct 2026 points to Friday 2026-10-09, so the notes may "make it clear". Readings: none (vague), 2026-10-08 (strictly before Friday), or 2026-10-09. I will not decide.
  - Marta none: ambiguous. "book the room for Oct 14": Oct 14 is the date the room is needed, not clearly a deadline for booking (writer's reading), but it is the only date attached to the action and one could read it as Due 2026-10-14. I will not decide.
  - Writer's choice (none for both) is the conservative reading and disclosed in the memo.
- C6 (traceable, nothing invented): met. Every decision and row traces to the notes (quotes above). One inference to flag: the memo states "Marta's 14 Oct is the training date, not a booking deadline"; the notes say only "book the on-call training room for Oct 14" and do not state outright that the training happens on 14 Oct. Optional softening below.
- C7: decided by lead, not scored.

criteria met: 5 of 6 (C1, C2, C3, C4, C6 met; C5 ambiguous, not counted). Verdict: not a pass until lead rules on C5 (pass requires n = m).

Factual claims: 13 checked (2 decisions, the "week of 12 October" original date, 5 owner/action pairs, 5 Due values). 11 of 13 verified; the 2 not verified are Due = none for Sam and Marta (ambiguous, see C5). Not checked: nothing outside the notes (no external facts in the memo). A reviewer pass is not a fact-check beyond the notes.

## REQUIRED CHANGES (ordered by severity)
1. Only after lead rules on C5:
   - If lead rules Sam's "before Friday" is clear: change Sam's Due from `none` to `2026-10-08` (strictly before Fri 9 Oct) or `2026-10-09`, per lead's ruling on "before"; and drop "before Friday" ambiguity from the Notes line.
   - If lead rules Marta's "for Oct 14" is a due date: change Marta's Due from `none` to `2026-10-14`.
   - If lead rules both vague: no change needed for C5.
2. No mandatory change otherwise.

## OPTIONAL changes
- Row Sam, Action: replace "Look into the flaky CI, before Friday (said in prose, not marked ACTION)" with "Look into the flaky CI" (the parenthetical is process commentary, not an action; "before Friday" belongs in Due or the date note).
- Notes line: replace "Marta's 14 Oct is the training date, not a booking deadline." with "Marta's notes give 14 Oct without saying whether it is the training date or a booking deadline, so Due is none." (avoids an inference not in the notes).
