# Self-Hosted Note-Taking Apps: Competitor Analysis

## Comparison Table

| App | Pricing | License | Sync Model |
|-----|---------|---------|-----------|
| **Obsidian** | Free core app; optional Sync $4–5/month (annual/monthly); Publish $8–10/month; Catalyst $25 one-time; Commercial $50/year | Proprietary; free for personal, commercial, non-profit, educational, and government use | Proprietary Obsidian Sync (end-to-end encrypted) or self-managed via third-party services (Dropbox, iCloud, OneDrive, WebDAV) |
| **Joplin** | Free core app; Joplin Cloud €2.40–7.99/month (annual pricing); Joplin Server Business (self-hosted) €30–40/year per user depending on team size | AGPL-3.0 | Joplin Cloud (managed), Joplin Server Business (self-hosted), or third-party services (Nextcloud, WebDAV, OneDrive, Google Drive) |
| **Logseq** | Free and open-source forever | AGPL-3.0 | Plaintext mode with third-party sync (Dropbox, OneDrive, Git, WebDAV) or optional beta Logseq Sync via sponsorship (currently $5–15/month recurring donation) |
| **Trilium Notes** | Free open-source; optional hosted instance $3.50/month | AGPL-3.0 | Self-hosted server (Linux/Windows) with desktop, web, and mobile clients syncing locally |
| **AnyType** | Free for personal use; €20/editor/month for Business; self-hosted Business (coming soon) €300/month | Custom license (personal use unrestricted; commercial use requires consent from Any Association); MIT for sync protocol | Personal: local-first, end-to-end encrypted peer-to-peer sync across devices; Business: cloud-hosted or self-hosted (coming soon), GDPR compliant |

### Sources
- **Obsidian**: https://obsidian.md/pricing (retrieved 2026-10-17); https://obsidian.md/license (retrieved 2026-10-17)
- **Joplin**: https://joplinapp.org/plans (retrieved 2026-10-17); https://discourse.joplinapp.org/t/joplin-is-switching-to-the-gnu-affero-general-public-license-v3-agpl-3-0/28747 (retrieved 2026-10-17)
- **Logseq**: https://blog.logseq.com/how-to-setup-and-use-logseq-sync/ (retrieved 2026-10-17); https://github.com/logseq/logseq (retrieved 2026-10-17)
- **Trilium Notes**: https://trilium.cc (retrieved 2026-10-17); https://github.com/TriliumNext/Trilium (retrieved 2026-10-17)
- **AnyType**: https://blog.anytype.io/our-open-philosophy/ (retrieved 2026-10-17); https://business.anytype.io (retrieved 2026-10-17)

---

## Where we can win (our assessment)

This competitive landscape reveals distinct positioning opportunities. Obsidian dominates the proprietary paid-sync market with strong pricing discipline (Sync starting at $4/month) and broad third-party integration, but its proprietary license, while permissive in use, may limit appeal to open-source-first users. Joplin and Trilium compete on openness (both AGPL-3.0) with strong self-hosting models, but Joplin's pricing complexity (multiple tiers, per-user scaling) and Trilium's sparse documentation of self-hosting may create friction. Logseq offers radical simplicity (free forever, plaintext-compatible) but with an underdeveloped paid sync story (currently beta-only for sponsors). AnyType differentiates on local-first architecture and team collaboration features at the high end (€20/editor/month), but the custom license and sparse documentation of personal-use sync leave gaps.

Winners here will compete on clarity of sync positioning (proprietary cloud vs. open self-hosted vs. plaintext-agnostic), transparent pricing at scale, and the developer experience of self-hosting. A contender with AGPL-3.0 licensing, straightforward self-hosted server setup, team-friendly pricing that doesn't scale linearly with users, and a clear, documented sync story could undercut Joplin's complexity and steal users seeking Trilium's openness without Trilium's documentation burden.

