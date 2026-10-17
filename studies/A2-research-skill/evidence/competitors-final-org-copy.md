# Competitor Analysis: Self-Hosted Note-Taking Apps

## Comparison Table

| App | License | Self-Hosting | Sync & Collaboration | Editor & Format | Mobile Apps | E2E Encryption |
|-----|---------|--------------|---------------------|-----------------|-------------|-----------------------|
| **Obsidian** | [Freemium (proprietary)](https://obsidian.md/license) | ❌ No | [Proprietary Sync (paid, E2E encrypted)](https://obsidian.md/sync). [Shared vaults via email invite](https://obsidian.md/license). | [WYSIWYG Markdown, plain text files, plugins](https://obsidian.md) | [iOS, Android](https://obsidian.md/mobile) | [Sync only (local files unencrypted)](https://obsidian.md/sync) |
| **Logseq** | [AGPL-3.0](https://github.com/logseq/logseq) | ✅ Yes | [RTC in DB version (alpha). Multi-device sync, Git-based option](https://github.com/logseq/logseq). | [Markdown/Org-mode, WYSIWYG, graph-based](https://github.com/logseq/logseq) | [iOS available; Android in development](https://github.com/logseq/logseq) | [Not implemented in stable; no E2E encryption in current releases](https://github.com/logseq/logseq) |
| **Joplin** | [AGPL-3.0-or-later](https://github.com/laurent22/joplin/blob/dev/LICENSE) | ✅ Yes ([Joplin Server self-hostable](https://github.com/laurent22/joplin); [WebDAV/Nextcloud support](https://joplinapp.org)) | [Joplin Server (E2E), Dropbox, OneDrive, WebDAV, Nextcloud](https://joplinapp.org). [Note sharing & collaboration](https://joplinapp.org). | [Markdown/Rich Text, multimedia support](https://joplinapp.org) | [iOS, Android](https://joplinapp.org) | ✅ [Yes (E2E on all sync methods)](https://joplinapp.org) |
| **Trilium Notes** | [AGPL-3.0](https://github.com/TriliumNext/Trilium) | ✅ Yes ([Self-hosted sync server, Docker](https://github.com/TriliumNext/Trilium)) | [Self-hosted sync server, public sharing, OpenID/TOTP](https://github.com/TriliumNext/Trilium) | [Rich WYSIWYG: tables, math, sketching, mind maps](https://github.com/TriliumNext/Trilium) | [Web-responsive (not native)](https://github.com/TriliumNext/Trilium) | ✅ [Yes (per-note, granular)](https://github.com/TriliumNext/Trilium) |
| **AnyType** | [Source-available (Any Source Available License 1.0)](https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md) | ✅ Yes ([P2P via Docker](https://github.com/anyproto/any-sync-dockercompose)). Local-first, optional sync. | [P2P (self-hosted Docker). Local-first, optional sync](https://github.com/anyproto/any-sync-dockercompose). [Real-time collaboration](https://blog.anytype.io) | [Block-based (Notion-like), Markdown, semantic objects](https://github.com/anyproto/anytype-ts) | [iOS, Android](https://github.com/anyproto/anytype-ts) | ✅ [Yes (core architecture)](https://github.com/anyproto/anytype-ts) |

---

## App Profiles

### Obsidian
**Strengths:** [Market-leading feature set](https://obsidian.md), beautiful UI, [native Markdown storage](https://obsidian.md), thriving plugin ecosystem, strong community.  
**Weaknesses:** [No self-hosting](https://obsidian.md/license); vendor lock-in; [E2E encryption limited to paid sync service](https://obsidian.md/sync); local files unencrypted; collaboration requires paid tier.  
**Best For:** Individual users seeking a feature-rich, offline-first desktop app; not suitable for self-hosted deployments.

### Logseq
**Strengths:** [Open-source AGPL](https://github.com/logseq/logseq); [graph-based knowledge organization](https://github.com/logseq/logseq); [self-hosting supported](https://github.com/logseq/logseq); [multi-format support (Markdown, Org-mode)](https://github.com/logseq/logseq); [emerging real-time collaboration (DB version)](https://github.com/logseq/logseq).  
**Weaknesses:** [Real-time collaboration in alpha stage](https://github.com/logseq/logseq); [no E2E encryption in stable releases](https://github.com/logseq/logseq); [iOS only, Android in development](https://github.com/logseq/logseq); smaller community than Obsidian.  
**Best For:** Teams wanting open-source infrastructure and graph-based note linking; suitable for self-hosted deployments with developer familiarity.

### Joplin
**Strengths:** [Mature E2EE across all sync methods](https://joplinapp.org); multi-platform support; [flexible sync (Joplin Cloud, Dropbox, OneDrive, WebDAV, Nextcloud)](https://joplinapp.org); [AGPL open-source](https://github.com/laurent22/joplin); [strong encryption prevents server access to data](https://joplinapp.org).  
**Weaknesses:** [Joplin Server is self-hosted but other sync methods use third-party cloud services](https://joplinapp.org); less polished UI than Obsidian; smaller plugin ecosystem.  
**Best For:** Users requiring strong encryption guarantees; mature deployments needing multi-platform support; teams valuing data privacy via E2EE.

### Trilium Notes
**Strengths:** [Enterprise-grade self-hosting with Docker](https://github.com/TriliumNext/Trilium); [per-note encryption with granular control](https://github.com/TriliumNext/Trilium); [advanced editor (WYSIWYG, tables, math, sketching, mind maps)](https://github.com/TriliumNext/Trilium); [full web-based frontend](https://github.com/TriliumNext/Trilium); [strong AGPL community](https://github.com/TriliumNext/Trilium).  
**Weaknesses:** [No native mobile apps (web-responsive only)](https://github.com/TriliumNext/Trilium); steeper deployment complexity; smaller user base; less market recognition.  
**Best For:** Organizations wanting on-premises deployment, advanced editing capabilities, and fine-grained encryption control; DevOps-friendly teams.  
**Note on repository:** [The original zadam/trilium repository entered maintenance mode in January 2024](https://github.com/TriliumNext/Trilium). [The active maintained project is at TriliumNext/Trilium](https://github.com/TriliumNext/Trilium).

### AnyType
**Strengths:** [P2P architecture emphasizes data ownership and local-first operation](https://github.com/anyproto/anytype-ts); [E2EE core to design](https://github.com/anyproto/anytype-ts); [full cross-platform support (macOS, Linux, Windows, iOS, Android)](https://github.com/anyproto/anytype-ts); [self-hosted Docker option](https://github.com/anyproto/any-sync-dockercompose); [modern block-based interface](https://github.com/anyproto/anytype-ts).  
**Weaknesses:** Newer entrant (less mature ecosystem); [P2P collaboration feature launched April 2024](https://blog.anytype.io); smaller community; less third-party integration; [source-available license (Any Source Available License 1.0) restricts commercial use outside Any Association-authorized networks](https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md).  
**Best For:** Privacy-conscious teams; organizations prioritizing data sovereignty and P2P sync; users comfortable with evolving feature set. Note: [the Any Source Available License 1.0 restricts commercial use](https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md) and may affect competitive product development.

---

## Where We Can Win

A self-hosted note app can differentiate by combining proven strengths from the competitive landscape while addressing critical gaps:

**1. Obsidian-Grade UX + Zero Vendor Lock-In**  
[Obsidian dominates because it's beautiful and frictionless](https://obsidian.md), but [forces users into a proprietary sync ecosystem](https://obsidian.md/sync). A self-hosted alternative with comparable design and feature depth—without mandatory cloud dependency—captures users frustrated by Obsidian's lack of self-hosting while retaining its appeal.

**2. Joplin's E2EE Guarantee + Better Collaboration UX**  
[Joplin's encryption is strong](https://joplinapp.org), but collaboration remains fragmented across cloud providers. A self-hosted system offering both server-side and client-side encryption with native real-time collaboration (not beta, not alpha) outperforms Joplin's current offering for teams balancing security and teamwork.

**3. Trilium's Power + Simpler Deployment**  
[Trilium's advanced editor (sketching, mind maps, per-note encryption)](https://github.com/TriliumNext/Trilium) appeals to power users, but [Docker deployment intimidates most organizations](https://github.com/TriliumNext/Trilium). A self-hosted app with similar capabilities but one-click installation (managed service or simplified deployment) opens Trilium's feature set to mainstream users.

**4. AnyType's Data Ownership Philosophy + Better Mobile + Legal Clarity**  
[AnyType's P2P and local-first architecture attracts privacy advocates](https://github.com/anyproto/anytype-ts), but [mobile support ramped up only recently](https://blog.anytype.io) and [its source-available license restricts commercial use](https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md). A self-hosted solution emphasizing local ownership with mature, native mobile apps (not web-responsive views) and a clearly permissive open-source license fills this gap for teams that won't compromise on privacy, usability, or commercial freedom.

**5. Market Timing**  
Four of five competitors are [open-source or source-available](https://github.com/logseq/logseq) but fragmented by approach ([AGPL](https://github.com/laurent22/joplin), [RTC alpha](https://github.com/logseq/logseq), [per-note encryption](https://github.com/TriliumNext/Trilium), [P2P](https://github.com/anyproto/anytype-ts), [licensing restrictions](https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md)). None cleanly combine ease of deployment, strong encryption, true collaboration, and native mobile apps. First-mover advantage exists for a cohesive, self-hosted product that unifies these strengths without the trade-offs each competitor currently requires.

**Opportunity:** Target early adopters from all five camps—Obsidian users tired of vendor lock-in, Trilium teams seeking simplicity, AnyType advocates wanting mature mobile and commercial freedom, and teams prioritizing E2EE collaboration over single-product ecosystems.
