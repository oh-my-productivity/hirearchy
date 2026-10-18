# Answer key (private; never shown to the assistant)
Weekdays: 2026-10-05 is a Monday.

## 2026-10-05
Decisions
- D1 Push API gateway migration to the week of 26 Oct (2 of 5 services fail contract tests).
- D2 Adopt Renovate, weekly Monday dependency PR batch, start with the 3 core repos.
Actions
- A1 (explicit) Priya | draft RFC for per-key rate limiter | 2026-10-09
- A2 (explicit) Dev | enable Renovate on the three core repos | 2026-10-08
- A3 (explicit) Marta | book on-call training room | 2026-10-14
- A4 (IMPLICIT) Sam | look into the flaky CI (shared build cache) | before Friday = 2026-10-09
- A5 (IMPLICIT) Lee | ping the identity vendor about the SSO certificate renewal | none (this week, no hard date)

## 2026-10-12
Decisions
- D1 Approve rate limiter RFC: token bucket per API key, behind a feature flag first.
- D2 Postmortem of the Oct 8 outage is blameless, shared company-wide.
- D3 Deploy freeze on Oct 22 and Oct 23 (customer demo).
Actions
- A1 (explicit) Dev | write postmortem for Oct 8 outage | 2026-10-14
- A2 (explicit) Marta | send demo agenda to customer | 2026-10-16
- A3 (explicit) Priya | start implementing rate limiter behind feature flag | 2026-10-20
- A4 (IMPLICIT) Sam | refresh staging test data, ready the day before the freeze | 2026-10-21
- A5 (IMPLICIT) Lee | swap on-call shifts with Dev for demo week (Lee carries the pager) | none (demo week 19-23 Oct)
(CI cache fix needing more work is a status update, not a new action.)

## 2026-10-19
Decisions
- D1 Go ahead with the customer demo, rate limiter left out.
- D2 Renew SSO vendor for twelve months.
- D3 Move weekly meeting Mon 10:00 -> Mon 14:00 from 2026-10-26.
Actions
- A1 (explicit) Marta | collect demo feedback and circulate | 2026-10-23
- A2 (explicit) Dev | remove deploy freeze in pipeline config | 2026-10-24
- A3 (explicit) Priya | present rate limiter benchmark results at next meeting | 2026-10-26
- A4 (IMPLICIT) Lee | sign off the SSO renewal once legal replies | ~2026-10-30 (end of next week) 
- A5 (IMPLICIT) Sam | pair with Jo on the CI pipeline in Jo's first week | week of 2026-10-26 (none exact)
