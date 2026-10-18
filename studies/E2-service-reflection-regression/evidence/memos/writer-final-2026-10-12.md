# Platform team meeting memo — 12 October 2026

Summary: The team approved the rate limiter RFC with token bucket design, planned for a blameless postmortem on the Oct 8 outage, set a deploy freeze for the customer demo week, and lined up implementation work and logistics.

## Decisions

- Rate limiter RFC approved with token bucket design counting per API key (rather than per customer account)
- Rate limiter to ship behind a feature flag
- Postmortem for the Oct 8 outage will be blameless and shared company-wide
- Deploy freeze scheduled for 22 and 23 October during the customer demo week

## Action items

| Owner | Action | Due |
|-------|--------|-----|
| Dev | Write postmortem for the Oct 8 outage | 2026-10-14 |
| Marta | Send demo agenda to customer | 2026-10-16 |
| Priya | Start implementing rate limiter behind feature flag | 2026-10-20 |
| Sam | Update test data to be ready | 2026-10-21 |
| Lee | Swap shifts with Dev for demo week | none |

## Open questions

- Lee's shift swap with Dev: no specific date mentioned in notes; commitment understood to cover the demo week (19–23 October).
