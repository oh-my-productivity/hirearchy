# Re-review: memo 2026-10-12 (task ...-4099, revises ...-5116)

Files opened:
- lead/writer/work/memo-2026-10-12.md (147 words per hirearchy org_read, modified 23:39:33 UTC)
- /private/tmp/hirearchy-p1-I2-1793142034/notes/2026-10-12.md (read in full)
- lead/reviewer/work/review-memo-2026-10-12.md (my earlier review; its source list re-verified against the notes, not just reused)
Not opened: none.

## My list from the notes (re-built)
Decisions: D1 approve RFC, token bucket per API key, ship behind feature flag first ("The team decided to approve the RFC with the token bucket design and to ship it behind a feature flag first"). D2 blameless postmortem shared company-wide ("We decided the postmortem will be blameless and will be shared with the whole company"). D3 deploy freeze Oct 22 and Oct 23 ("the team decided on a deploy freeze on Oct 22 and Oct 23").
Commitments: A1 Dev, postmortem, by Oct 14. A2 Marta, demo agenda, by Oct 16. A3 Priya, start implementing, by Oct 20. A4 Sam (prose), sort out staging test data "ready the day before the freeze starts" = 2026-10-21 (hedged "will probably"; client ruled 2026-10-21). A5 Lee (prose), "he'll swap shifts with Dev", no date -> none (client ruled).
Not commitments: Sam's CI update; Dev's preference to present; Priya "ready to start building" (covered by A3); "Nobody had a problem with that"; next meeting 19 October.

## Ledger (memo vs my list)
| Item | Memo text | Result |
|---|---|---|
| D1 | "Approve the rate limiter RFC with the token bucket per API key design, and ship it behind a feature flag first." | present |
| D2 | "Make the postmortem for the 8 October billing outage blameless and share it with the whole company, not just engineering." | present |
| D3 | "Hold a deploy freeze on 22 and 23 October for the customer demo." | present |
| A1 | "\| D \| Write the postmortem for the 8 October outage \| 2026-10-14 \|" | present, Due matches "by Oct 14" |
| A2 | "\| M \| Send the demo agenda to the customer \| 2026-10-16 \|" | present, matches "by Oct 16" |
| A3 | "\| P \| Start implementing the rate limiter behind a feature flag \| 2026-10-20 \|" | present, matches "by Oct 20" |
| A4 | "\| S \| Update the out-of-date staging test data \| 2026-10-21 \|" | present; Oct 22 freeze, day before = Oct 21 |
| A5 | "\| L \| Swap pager shifts with Dev for the demo week \| none \|" | present; no date in notes |

## Criteria
- C1 met. Every name, date and detail in the memo appears in 2026-10-12.md; no other source used.
- C2 met. 147 words by read (limit 400).
- C3 met. Title "# Platform team weekly memo, 2026-10-12" names the date. Sections "## Decisions" (3 bullets = D1-D3) and "## Actions" with header "| Owner | Action | Due |". No other sections; the only extra element is the Summary line (allowed by C8).
- C4 met. 5 rows = A1-A5; no row for any item in my not-commitments list.
- C5 met. All Due values are YYYY-MM-DD or "none": 2026-10-14, 2026-10-16, 2026-10-20, 2026-10-21, none. Derivations checked in the ledger.
- C6 met. Each decision and row traces to the notes (quotes above); nothing invented. Summary claims (RFC approved, per-API-key token bucket, blameless company-wide postmortem, freeze 22 and 23 October, five actions) each trace to D1-D3 and the five rows.
- C8 met. Order is title, "Summary: The rate limiter RFC is approved ..." on one line directly after the title, "## Decisions", "## Actions". Summary is the only addition.
- C9 met. Owner column values are exactly D, M, P, S, L: one capital letter each, no full name in the column. Initials match the notes' names (Dev, Marta, Priya, Sam, Lee) and are unique among the five attendees, so each is unambiguous.

Regression list:
- R1 (C8, Summary first, then decisions, then actions): met, order confirmed above.
- R2 (C9, "Owners as initials only, always"): met in the Owner column. See ambiguous (1) for other places names appear.

criteria met: 8 of 8 (C1-C6, C8, C9; C7 is not in this task's list).

## Factual claims verified: 13 of 13 factual claims verified
3 decisions, 5 rows (owner, action, Due each), 5 Summary claims (RFC approved; per-API-key token bucket; blameless company-wide postmortem; freeze 22 and 23 October; five actions = five rows). The facts "billing outage" and "8 October" are both in the notes ("billing service was unavailable", "Oct 8"). This is a check against the notes only, not an external fact-check.

## Ambiguous
1. R2 "Owners as initials only, always" vs C9 wording: C9 limits itself to the Owner column. The memo still names "Dev" in the Action cell of the Lee row ("Swap pager shifts with Dev for the demo week"). "Always" in R2 could be read as covering the whole memo. The notes name Dev as the swap partner, so replacing it would lose information; under C9 as written it is allowed. I do not require a change; the lead decides. If the lead reads R2 as memo-wide, the fix would be to change that cell to "Swap pager shifts with D for the demo week" (writer to apply).
2. Sam row: "will probably sort it out himself" is hedged; counted as a commitment per client ruling. The memo shows 2026-10-21 as firm.
3. Lee "Nobody had a problem with that": not treated as a decision; criteria do not define agreement by silence.
4. D1 holds two decisions (approve with token bucket; ship behind flag first) in one bullet; client ruled one bullet.
5. Lee Due none: "demo week" is a period, not a date; none follows C5.
6. Summary says "five actions were assigned" while only three are labelled ACTION in the notes; two are prose commitments. Consistent with C4 and the five rows.

## REQUIRED CHANGES
None.
