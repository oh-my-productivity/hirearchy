# Competitor Analysis: Self-Hosted Note-Taking Apps

## Comparison Table

| App | Pricing | License | Sync Model |
|-----|---------|---------|-----------| 
| **Obsidian** | Free core; Sync $4-5/mo per user; Publish $8-10/mo per site; optional Commercial license $50/user/year (https://obsidian.md/pricing) | Proprietary; free for all purposes including commercial (https://obsidian.md/license) | Cloud-only via Obsidian Sync; end-to-end encrypted (AES-256) (https://obsidian.md/pricing); no official self-hosted server (https://obsidian.md/sync) |
| **Logseq** | Core app free; Sync beta requires $5+/mo Open Collective sponsorship; future subscription model TBD (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/) | AGPL-3.0 (https://github.com/logseq/logseq/blob/master/LICENSE.md) | Plaintext sync with any file service; Logseq Sync cloud option in beta; custom sync server URLs supported for advanced users (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/) |
| **Joplin** | Free desktop/mobile; Cloud sync €2.99-9.99/mo; Joplin Server Business €2.50/user/mo (51+ users) (https://joplinapp.org/plans) | AGPL-3.0 (https://joplinapp.org/news/20221221-agpl); Joplin Server: free to self-host under AGPL-3.0 (https://github.com/laurent22/joplin) | Cloud: Joplin Cloud managed; Self-hosted: Joplin Server AGPL-3.0 free; all sync end-to-end encrypted (https://joplinapp.org/help/apps/joplin_server_business) |
| **Trilium Notes** | 100% free, open-source, no paid tier (https://github.com/TriliumNext/Trilium/blob/main/README.md) | AGPL-3.0 (https://github.com/TriliumNext/Trilium/blob/main/LICENSE) | Built-in self-hosted sync server; no cloud services required; optional third-party hosting available (https://github.com/TriliumNext/Trilium/blob/main/README.md) |
| **AnyType** | Free basic tier; Paid plans €20/editor/mo for business workspaces; 50% student/educator discount on all membership plans (https://doc.anytype.io/anytype-docs/memberships/monetization); self-hosted business €300/mo flat (coming soon) (https://business.anytype.io/) | Proprietary; non-commercial use free (personal, academic, research); commercial use requires permission/license from Any Association (https://community.anytype.io/t/how-does-the-anytype-license-apply-to-self-hosting-internal-deployments-in-commercial-contexts/12322/2) | Local-first by default; optional encrypted sync via Anytype backup nodes; users can self-host sync infrastructure; all data encrypted end-to-end (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption) |

---

## Where we can win

### 1. **Unrestricted Open-Source License**

Obsidian is proprietary (though free) (https://obsidian.md/license); AnyType requires explicit commercial licensing for profitable use (https://community.anytype.io/t/how-does-the-anytype-license-apply-to-self-hosting-internal-deployments-in-commercial-contexts/12322/2). Joplin and Logseq use AGPL-3.0 (https://joplinapp.org/news/20221221-agpl), (https://github.com/logseq/logseq/blob/master/LICENSE.md), which restricts derivative works. Trilium is AGPL-3.0 (https://github.com/TriliumNext/Trilium/blob/main/LICENSE) with limited enterprise adoption.

**Opportunity:** MIT or Apache 2.0 license permits commercial use and modifications without friction. This captures cost-conscious enterprises evaluating self-hosted solutions where license clarity is non-negotiable.

### 2. **Self-Hosted Sync Without Per-User Fees**

- Obsidian: $4-5/user/month cloud-only (no self-hosted option) (https://obsidian.md/pricing)
- Joplin Server Business: €2.50/user/month at 51+ users; for 100 users = €250/month (https://joplinapp.org/plans)
- AnyType: €20/editor/month for business (https://business.anytype.io/), or €300/month flat for self-hosted (coming soon) (https://business.anytype.io/)
- Logseq & Trilium: free self-hosted but lack enterprise UX polish (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/), (https://github.com/TriliumNext/Trilium/blob/main/README.md)

**Opportunity:** One-time or annual flat-fee licensing for self-hosted deployments, regardless of seat count. For a 100-user organization, flat-fee costs $0 vs. Joplin's €250/month or Obsidian's $400-500/month ($4.00–5.00 × 100 users). A free self-hosted alternative eliminates recurring per-user fees entirely, representing a significant total cost of ownership advantage for enterprises.

### 3. **Zero-Friction Offline-First Sync**

All competitors support offline access (https://obsidian.md/pricing), (https://joplinapp.org/plans), (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption), (https://github.com/TriliumNext/Trilium/blob/main/README.md), but sync setup varies:
- Obsidian stores notes locally by default; its Sync service is an optional paid add-on requiring intentional setup (https://obsidian.md/pricing), (https://obsidian.md/sync)
- Joplin and Logseq require server setup or third-party services (https://joplinapp.org/plans), (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/)
- Trilium is self-hosted but lacks collaboration UX (https://github.com/TriliumNext/Trilium/blob/main/README.md)
- AnyType is local-first but less mature than Obsidian (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption)

**Opportunity:** Make offline-first the default with automatic sync overlay requiring zero configuration. Enable users to back up to USB, local NAS, or S3-compatible storage without deploying infrastructure. This appeals to privacy-conscious users, security-sensitive teams, and developers who reject SaaS sync.

### 4. **Portable Markdown-First Format with Git Integration**

- Obsidian uses Markdown in proprietary vaults (https://obsidian.md/license); plugins create additional vendor lock-in
- Joplin exports to multiple formats with varying complexity (https://joplinapp.org/plans)
- Logseq uses plaintext Markdown (most portable) (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/)
- Trilium supports Markdown import & export (https://github.com/TriliumNext/Trilium/blob/main/README.md)
- AnyType uses encrypted storage (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption)

**Opportunity:** Guarantee every vault exports as native Markdown without conversion. Bundle Git integration so users own their sync history and can audit every change. This eliminates vendor lock-in and appeals to developers and knowledge workers who treat notes as code.

### 5. **Simplified Pricing with Zero Upsells**

Current pricing creates confusion:
- Obsidian: free core + optional $4-10/mo services + optional licensing (https://obsidian.md/pricing)
- Joplin: free core + optional €2.99-9.99/mo or complex self-hosted tiers (https://joplinapp.org/plans)
- Logseq: free core + unclear sync pricing (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/)
- AnyType: free core + €20/mo business tier (https://business.anytype.io/)
- Trilium: free (no freemium confusion) (https://github.com/TriliumNext/Trilium/blob/main/README.md)

**Opportunity:** Single tier for individuals (free, always) and single tier for teams (transparent, all-in). Don't gate offline sync, collaboration, or self-hosting behind paywalls. This reduces buyer indecision and positions us as the trustworthy alternative to Obsidian's freemium model.

### 6. **Real-Time Collaboration Without Lock-In**

- Obsidian: collaboration via shared vaults (Sync required, $4-5/user/mo), but no CRDT/OT-based real-time co-editing; Publish is for distribution, not co-editing (https://obsidian.md/sync)
- Joplin: shared notebooks exist but with functional-not-delightful UX (https://joplinapp.org/plans)
- Logseq and Trilium: primarily single-user (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/), (https://github.com/TriliumNext/Trilium/blob/main/README.md)
- AnyType: collaboration included but proprietary format restricts portability (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption)

**Opportunity:** Implement Operational Transformation (OT) or CRDT-based real-time co-editing on top of the Markdown format, enabling true collaborative editing without centralized servers. Pair this with a polished knowledge graph interface to compete with Obsidian's appeal while retaining open-source portability.

### 7. **Enterprise Security & Auditability**

- Obsidian: proprietary cloud creates trust concerns for regulated industries (https://obsidian.md/license)
- Joplin: AGPL-3.0 but licensing clarity around server (https://github.com/laurent22/joplin)
- Logseq: fully open but smaller team/minimal security marketing (https://github.com/logseq/logseq/blob/master/LICENSE.md)
- Trilium: fully open but minimal enterprise documentation (https://github.com/TriliumNext/Trilium/blob/main/LICENSE)
- AnyType: proprietary license despite open-source code; commercial restrictions create friction (https://community.anytype.io/t/how-does-the-anytype-license-apply-to-self-hosting-internal-deployments-in-commercial-contexts/12322/2)

**Opportunity:** Market security aggressively: no vendor lock-in, no proprietary servers, no data collection. Publish a security policy, encourage independent audits, and provide compliance documentation for HIPAA, GDPR, and SOC 2 contexts. This becomes the default for healthcare, finance, and legal teams where Obsidian is perceived as less trustworthy.

### 8. **Developer Ecosystem with Revenue Sharing**

- Obsidian: large plugin ecosystem but proprietary marketplace (https://obsidian.md/license)
- Joplin: weaker ecosystem despite extensibility (https://joplinapp.org/plans)
- Logseq: small ecosystem (https://github.com/logseq/logseq/blob/master/LICENSE.md)
- Trilium: strong scripting but limited UI-based extensibility (https://github.com/TriliumNext/Trilium/blob/main/README.md)
- AnyType: not designed for extensibility (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption)

**Opportunity:** Open Plugin API with revenue sharing (20-30% of sales to plugin authors). This creates self-reinforcing network effects where third-party developers have financial incentive to build on our platform, increasing value through quality rather than contractual lock-in.

### 9. **Mobile-First Design from Day One**

- Obsidian: mobile feels secondary; Sync pushes users to cloud (https://obsidian.md/pricing)
- Joplin: strong mobile support but UI less polished than Obsidian (https://joplinapp.org/plans)
- Logseq, Trilium, AnyType: mobile support secondary to desktop (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/), (https://github.com/TriliumNext/Trilium/blob/main/README.md), (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption)

**Opportunity:** Design mobile as equal-first to desktop, not an afterthought. Focus on fast editing and search on small screens, with seamless offline-first sync between devices. Include a lightweight companion app for quick notes. This captures mobile-primary users (students, travelers, field workers).

### 10. **Transparent Data Control**

Every competitor claims privacy, but:
- Obsidian: free app but closed-source cloud sync means users must trust Obsidian's team without ability to independently audit the sync implementation (https://obsidian.md/license)
- Joplin: AGPL-3.0 adds transparency but implementation details are buried (https://joplinapp.org/news/20221221-agpl)
- Logseq: open but sync architecture still evolving (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/)
- Trilium: fully self-hosted by default but minimal marketing (https://github.com/TriliumNext/Trilium/blob/main/README.md)
- AnyType: encrypted local storage but commercial licensing creates uncertainty (https://community.anytype.io/t/how-does-the-anytype-license-apply-to-self-hosting-internal-deployments-in-commercial-contexts/12322/2)

**Opportunity:** Make data ownership explicit and auditable. Users can verify exactly where data lives, what encrypts, and what control they retain. For regulated industries, this trust story converts switching costs into switching incentives.

---

## Summary

The market presents a clear pattern: leaders like Obsidian trade openness for UX polish (https://obsidian.md/license), (https://obsidian.md/pricing), while open-source alternatives like Trilium sacrifice polish for freedom (https://github.com/TriliumNext/Trilium/blob/main/README.md). A new entrant wins by removing this artificial trade-off—combining Obsidian's design with Trilium's philosophy, and charging fairly. The competitive advantages are: unrestricted licensing, transparent pricing, portable Markdown format, and authentic privacy. For enterprises with 100+ users, eliminating per-user sync fees (Joplin's €250/month for 100 users at €2.50/user (https://joplinapp.org/plans), Obsidian's $400-500/month at $4–5/user (https://obsidian.md/pricing)) represents a significant total cost of ownership advantage; for individuals, this delivers freedom without compromise.
