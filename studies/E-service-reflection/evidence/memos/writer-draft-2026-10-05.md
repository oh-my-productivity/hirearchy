# Platform Team Meeting Memo — 5 October 2026

## Decisions

- **API gateway migration**: Postpone the migration from the week of 12 October to the week of 26 October. Two of five services still fail contract tests due to header casing issues; the team will use the extra time to resolve these failures before cutover.

- **Dependency hygiene process**: Adopt Renovate for automated dependency updates with a weekly Monday batch of PRs, starting with the three core repos. The team will assess noise and consider widening to other repos if acceptable.

- **CI flaky builds**: Sam will investigate failing builds on the main pipeline (approximately one in eight runs without code changes), with focus on the shared build cache as a suspected cause.

- **SSO certificate renewal**: Proceed with renewal of the SSO certificate expiring at the end of October; Lee will handle vendor communication.

## Action items

| Owner | Action | Due |
|-------|--------|-----|
| Priya | Draft RFC for per-key rate limiter to address large-plan customer issues with batch import rate limits | 2026-10-09 |
| Dev | Enable Renovate on the three core repos | 2026-10-08 |
| Sam | Investigate flaky CI builds (suspected shared build cache issue) | 2026-10-09 |
| Marta | Book on-call training room for eight people with screen for newest engineers | 2026-10-14 |
| Lee | Contact SSO certificate vendor regarding renewal paperwork | none |
