# Review: memo 2026-11-09

Files opened: lead/writer/work/2026-11-09-memo.md (126 words, 17 lines); /private/tmp/hirearchy-p1-F2-1793146944/notes/2026-11-09.md. None unopened.

## My own list from the notes (before comparing)
Decisions ("We decided"/"decided"):
- D1 Switch-off of old gateway moved to Friday 20 November.
- D2 Priya's rate limiter rollout plan approved as written.
- D3 Jo joins on-call rotation from Monday 16 November.
Not decisions: deck went out / customer confirmed review for Wednesday (status); Meeting closed 14:40; Next meeting (excluded by R2/C9).
Commitments:
- A1 Marta: circulate quarterly review notes by Nov 11 (ACTION) -> 2026-11-11.
- A2 Dev: switch off old gateway Nov 20 (ACTION) -> 2026-11-20.
- A3 Priya: start rate limiter rollout to all plans Nov 16 (ACTION) -> 2026-11-16.
- A4 Sam: "said he would add Jo to the on-call rotation by Friday" (informal). Notes are dated Monday 9 Nov, so Friday = 2026-11-13. Under the settled rule (Friday after a Monday-dated meeting = that Friday's date) the Due is 2026-11-13.
- A5 Lee: "said he'd go through the SSO audit log at some point ... No date was given." -> none.
Initials-only people: none.

## Criteria
- C1 met: 126 words per read (limit 400); markdown (heading, bullets, table).
- C2 met: only the 9 Nov 2026 meeting; title says 2026-11-09.
- C3 met: three bullets match D1-D3 exactly; no other statements. Summary repeats the same three.
- C4 met: header `| Owner | Action | Due |`, exactly three columns.
- C5 met: five rows = A1-A5 (Marta, Dev, Priya, Sam, Lee), including the informal Sam and Lee rows.
- C6 NOT MET: Sam row Due is `none`, but the notes say "by Friday" in a Monday 9 Nov meeting, so the date is clear: 2026-11-13. Other Dues correct: Marta 2026-11-11, Dev 2026-11-20, Priya 2026-11-16, Lee none ("No date was given").
- C9 met: order is title line, `Summary:` line, `## Decisions` section, table; no Present/Next/closing lines. (The blank lines and the `## Decisions` heading are part of the required Decisions section.)
- C11 met: Marta, Dev, Priya, Sam, Lee as written in the notes; no initials.
- C12 met (vacuous): no person appears only as initials in the notes, and none appears in the memo.

Criteria met: 8 of 9. Verdict: NOT pass.

## Regression lines
- R1 (Summary first, then decisions, then actions): no problem; order correct.
- R2: no Present/Next/closing lines. Ok.
- R4: full names as in the notes (first names only, as written). Ok.
- R5: no initials-only people; nothing to apply. Ok.

## REQUIRED CHANGES (by severity)
1. Sam row: change Due `none` to `2026-11-13` (C6). Optional: the Action cell may keep "by Friday" or be shortened to "Add Jo to the on-call rotation"; not required.

## Ambiguous
- Sam's "by Friday" is the only judgment call. I treat it as 2026-11-13 per the settled rule from earlier approved memos (Friday after a Monday-dated meeting is that Friday's date). If the client prefers `none` for a bare "by Friday", C6 would be met; the lead should decide, but I cannot count it met.
- Summary line states only the decisions; no action-item count is claimed. Fine.

## Not checked
Factual claims in the memo were compared with the notes only; this is not a wider fact-check.
