# Final Verification Report — competitors.md
Task: 20261017T201015412528-lead-1db6
Fact-checker: lead/factcheck
Date: 2026-10-17
Deliverable: lead/writer/work/competitors.md (1181 words, modified 20:07:58 UTC)
Previous check: 1172 words, modified 20:00:47 UTC

---

## Verdict: FAIL

Coverage: 91 claims examined (document has grown; 3 new claims from rework edits).
- **verified: 52**
- **wrong: 5**
- **unsupported: 13**
- **not-checkable: 21**
- **Total: 91** ✓

This re-check is FAIL: 5 wrong claims and 13 unsupported claims remain.

---

## What was fixed vs. the previous 9 required changes

| RC | Issue | Status after rework |
|----|-------|---------------------|
| RC-1 | AnyType €20 cited to wrong URL (3 locations) | **FIXED** — all 3 now cite business.anytype.io ✓ |
| RC-2 | "Obsidian defaults to cloud" | **FIXED** — now "stores notes locally by default; its Sync service is an optional paid add-on requiring intentional setup" ✓ |
| RC-3 | "Joplin and Trilium export via SQLite; cumbersome" | **FIXED** — now "Trilium supports Markdown import & export; Joplin exports to multiple formats" ✓ |
| RC-4 | "50% discount on personal plans" text | **FIXED** (text) — now says "on all membership plans" ✓; BUT **citation error introduced**: see NEW-1 below |
| RC-5 | Logseq Markdown file format cited to LICENSE.md | **PARTIALLY FIXED** — citation changed from LICENSE.md to blog post; but blog post still does not explicitly state "Logseq uses plaintext Markdown" → still unsupported |
| RC-6 | Joplin E2E sync cited to plans page | **FIXED** — now cites joplinapp.org/help/apps/joplin_server_business ✓ |
| RC-7 | "Joplin Server free personal non-commercial" | **FIXED** (text) — now "free to self-host under AGPL-3.0"; BUT **broken URL introduced**: see NEW-2 below |
| RC-8 | Same "personal non-commercial" in sync column | **FIXED** (text) — "Joplin Server AGPL-3.0 free" ✓ |
| RC-9 | "Plaintext sync with any file service" unsupported | **NOT FIXED** — still cites Logseq DB post which does not state plaintext file-service sync |

---

## REQUIRED CHANGES (5 remaining, ordered by severity)

---

### NEW-1 [HIGH] — Wrong citation for student/educator discount

**Location:** Table, AnyType Pricing: "50% student/educator discount on all membership plans (https://business.anytype.io/)"

**Problem:** The citation was changed from `https://doc.anytype.io/anytype-docs/memberships/monetization` to `https://business.anytype.io/`. However, business.anytype.io does NOT mention a student/educator discount anywhere. The page only discusses Anytype for Business pricing (€20/editor/mo) and the self-hosted option (€300/mo flat). The student/educator discount information is exclusively stated at `https://doc.anytype.io/anytype-docs/memberships/monetization`, which states: "Students or faculty members are eligible for a 50% discount on all of our membership plans."

The text of the claim has been correctly changed ("all membership plans" ✓) but the citation now points to a page that does not support it.

**Required fix:** Change the citation for the student/educator discount from `(https://business.anytype.io/)` back to `(https://doc.anytype.io/anytype-docs/memberships/monetization)`.

**Evidence:** doc.anytype.io/memberships states: "Is there a student / educational plan? Students or faculty members are eligible for a 50% discount on all of our membership plans." This text is absent from business.anytype.io.

---

### NEW-2 [HIGH] — Broken URL for Joplin Server AGPL-3.0

**Location:** Table, Joplin License: "Joplin Server: free to self-host under AGPL-3.0 (https://github.com/joplin/server)"

**Problem:** The URL `https://github.com/joplin/server` returns HTTP 404 Not Found. The Joplin server code is part of the main Joplin monorepo at `https://github.com/laurent22/joplin` (in the `packages/server` subdirectory). There is no separate `github.com/joplin/server` repository.

**Required fix:** Replace `(https://github.com/joplin/server)` with `(https://github.com/laurent22/joplin)`, which is the main Joplin repository under AGPL-3.0 that contains the server code.

**Evidence:** HTTP 404 at https://github.com/joplin/server. The server package exists at https://github.com/laurent22/joplin/tree/dev/packages/server with its own LICENSE.md under AGPL-3.0.

---

### RC-5-RESIDUAL [MEDIUM] — "Logseq uses plaintext Markdown (most portable)" — still unsupported

**Location:** §4 (Portable Markdown-First Format): "Logseq uses plaintext Markdown (most portable) (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/)"

**Problem:** The Logseq Sync blog post describes how to set up and use Logseq Sync. It mentions that graph files should be moved out of iCloud/Dropbox/OneDrive folders before using Logseq Sync (implying they are files), but the post DOES NOT explicitly state "Logseq uses plaintext Markdown format." The claim requires a source that directly states Logseq's file format is plaintext Markdown.

**Required fix:** Find a source that explicitly states Logseq stores notes as plaintext Markdown files (e.g., logseq.com or docs.logseq.com documentation on file formats), or change the citation to a page that does say this.

**Evidence:** The blog post does not contain the phrase "plaintext Markdown" or describe Logseq's file format. It focuses on the sync setup process.

---

### RC-9-UNRESOLVED [MEDIUM] — "Plaintext sync with any file service" (Logseq) — still unsupported

**Location:** Table, Logseq Sync: "Plaintext sync with any file service; Logseq Sync cloud option in beta; custom sync server URLs supported for advanced users (https://blog.logseq.com/how-to-setup-and-use-logseq-sync/)"

**Problem:** The Logseq Sync blog post describes Logseq's proprietary cloud sync, not plaintext file-service sync. The blog explicitly says: "From now on, only Logseq Sync should be syncing your graph" and instructs users to MOVE graphs out of iCloud/Dropbox folders. The cited Logseq DB update (https://discuss.logseq.com/t/whats-new-with-logseq-db-april-26-2026/34977) mentions "custom sync server URLs" but says nothing about plaintext sync with arbitrary file services.

Note: The claim "Plaintext sync with any file service" may have been true of older Logseq file-based graphs, but neither cited source currently states this. Logseq's DB version appears to be moving away from plaintext files toward a database format.

**Required fix:** Either (a) find an official Logseq source that states the current version supports plaintext sync with any file service, or (b) revise the claim to reflect what the sources actually say. The blog post supports "Logseq Sync cloud option in beta" (✓) and the DB post supports "custom sync server URLs" (✓), but not "Plaintext sync with any file service."

---

### PREVIOUS-UNSUPPORTED [LOW] — Residual unsupported claims from first check (unchanged)

The following claims were unsupported in the first check and remain unchanged/uncited in the reworked document. They do not require fixes per the original RC list but are documented here for completeness and transparency:

- C47: "All competitors support offline access" — cited sources don't individually confirm this
- C52: "Obsidian uses Markdown in proprietary vaults; plugins create vendor lock-in" — cited to license page which says nothing about vault format
- C64: "AnyType: collaboration included but proprietary format restricts portability" — cited source says nothing about portability restrictions
- C65: "Obsidian: proprietary cloud creates trust concerns for regulated industries" — cited to license page; the license page actually states "Sync data is encrypted and inaccessible to our staff"
- C66: "Joplin: AGPL-3.0 but licensing clarity around server" — cited source (community forum) doesn't support "licensing confusion" characterization
- C70: "Obsidian: large plugin ecosystem but proprietary marketplace" — cited to license page which says nothing about plugins or marketplace

These 6 claims are editorial assessments whose cited sources don't directly state them. They were marked UNSUPPORTED in the first check and remain so. They are not new errors introduced in rework.

---

## Claims fully verified in reworked document

| ID | Claim | Source | Verdict |
|----|-------|--------|---------|
| C01 | Obsidian Sync $4-5/mo per user | obsidian.md/pricing | verified |
| C02 | Obsidian Publish $8-10/mo per site | obsidian.md/pricing | verified |
| C03 | Obsidian Commercial license $50/user/year | obsidian.md/pricing | verified |
| C04 | Obsidian: proprietary; free for all purposes including commercial | obsidian.md/license | verified |
| C05 | Obsidian sync E2E encrypted AES-256 | obsidian.md/pricing | verified |
| C06 | Obsidian: no official self-hosted server | obsidian.md/sync | verified |
| C07 | Obsidian sync: Cloud-only via Obsidian Sync | obsidian.md/pricing | verified |
| C08 | Logseq core app free | blog.logseq.com/... | verified |
| C09 | Logseq Sync beta requires $5+/mo Open Collective | blog.logseq.com/... | verified |
| C10 | Logseq future subscription model TBD | blog.logseq.com/... | verified |
| C11 | Logseq license: AGPL-3.0 | github.com/logseq/.../LICENSE.md | verified |
| C13 | Logseq Sync cloud option in beta | discuss.logseq.com/...34977 | verified |
| C14 | Logseq custom sync server URLs supported | discuss.logseq.com/...34977 | verified — post states "you can now point Logseq at a custom sync server URL" |
| C15 | Joplin desktop/mobile free | joplinapp.org/plans | verified |
| C16 | Joplin Cloud sync €2.99-9.99/mo | joplinapp.org/plans | verified |
| C17 | Joplin Server Business €2.50/user/mo (51+ users) | joplinapp.org/plans | verified |
| C18 | Joplin license: AGPL-3.0 | joplinapp.org/news/20221221-agpl | verified |
| C18b | Joplin Server: free to self-host under AGPL-3.0 (TEXT) | — | verified (text; URL broken — see NEW-2) |
| C19 | Joplin sync: all sync E2E encrypted | joplinapp.org/help/apps/joplin_server_business | verified — "End-to-end encryption: Activate encryption to protect your data and secure communications across teams." |
| C22 | Trilium: 100% free, open-source, no paid tier | github.com/TriliumNext/Trilium/README.md | verified |
| C23 | Trilium license: AGPL-3.0 | github.com/TriliumNext/Trilium/LICENSE | verified |
| C24 | Trilium: Built-in self-hosted sync server | github.com/TriliumNext/Trilium/README.md | verified |
| C25 | Trilium: no cloud services required | github.com/TriliumNext/Trilium/README.md | verified |
| C26 | Trilium: optional third-party hosting available | github.com/TriliumNext/Trilium/README.md | verified |
| C27 | AnyType: free basic tier | doc.anytype.io/.../memberships | verified |
| C28 | AnyType: Paid plans €20/editor/mo for business workspaces | business.anytype.io | verified — "€20 per editor / month" |
| C29 | AnyType: 50% student/educator discount on all membership plans (TEXT) | — | verified (text correct; citation wrong — see NEW-1) |
| C30 | AnyType: self-hosted business €300/mo flat (coming soon) | business.anytype.io | verified |
| C31 | AnyType: non-commercial use free; commercial requires permission | community.anytype.io/...12322/2 | verified |
| C32 | AnyType: Local-first by default | doc.anytype.io/.../privacy-and-encryption | verified |
| C33 | AnyType: optional encrypted sync via Anytype backup nodes | doc.anytype.io/.../privacy-and-encryption | verified |
| C34 | AnyType: users can self-host sync infrastructure | doc.anytype.io/.../privacy-and-encryption | verified |
| C35 | AnyType: all data encrypted end-to-end | doc.anytype.io/.../privacy-and-encryption | verified |
| C36 | Obsidian is proprietary (though free) | obsidian.md/license | verified |
| C37 | AnyType requires explicit commercial licensing for profitable use | community.anytype.io/...12322/2 | verified |
| C38 | Joplin and Logseq use AGPL-3.0 | joplinapp.org/news/20221221-agpl + github.com/logseq/LICENSE.md | verified |
| C39 | AGPL-3.0 restricts derivative works | LICENSE text | verified |
| C41 | Obsidian: $4-5/user/month cloud-only (no self-hosted option) | obsidian.md/pricing | verified |
| C42 | Joplin Server Business: €2.50/user/mo; 100 users = €250/mo | joplinapp.org/plans | verified |
| C43 | AnyType: €20/editor/month for business (§2) | business.anytype.io | verified |
| C44 | AnyType: €300/month flat self-hosted (coming soon) | business.anytype.io | verified |
| C46 | 100-user costs: $0 vs Joplin €250/mo vs Obsidian $400-500/mo | joplinapp.org/plans + obsidian.md/pricing | verified |
| C48 | Obsidian stores notes locally by default; Sync optional add-on | obsidian.md/pricing + obsidian.md/sync | verified — "Free without limits. No sign-up required. Optional add-on services make it easy to sync." |
| C49 | Joplin and Logseq require server setup or third-party services | joplinapp.org/plans + blog.logseq.com/... | verified |
| C53 | Trilium supports Markdown import & export | github.com/TriliumNext/Trilium/README.md | verified — "Evernote and Markdown import & export" |
| C55 | AnyType uses encrypted storage | doc.anytype.io/.../privacy-and-encryption | verified |
| C56 | Obsidian: free core + optional $4-10/mo services + optional licensing | obsidian.md/pricing | verified |
| C57 | Joplin: free core + optional €2.99-9.99/mo | joplinapp.org/plans | verified |
| C58 | Logseq: free core + unclear sync pricing | blog.logseq.com/... | verified |
| C59 | AnyType: free core + €20/mo business tier (§5) | business.anytype.io | verified |
| C60 | Trilium: free (no freemium confusion) | github.com/TriliumNext/Trilium/README.md | verified |
| C61 | Obsidian: Sync required $4-5/user/mo; no CRDT/OT co-editing; Publish is distribution | obsidian.md/sync | verified |
| C63 | Logseq and Trilium: primarily single-user | blog.logseq.com (Logseq Sync NOT support collaboration) | verified |
| C69 | AnyType: proprietary license; commercial restrictions | community.anytype.io/...12322/2 | verified |
| C78 | Obsidian: closed-source sync; users cannot audit | obsidian.md/license | verified |
| C80 | Logseq: sync architecture still evolving | blog.logseq.com/... | verified |
| C85 | Joplin: €250/month for 100 users at €2.50/user | joplinapp.org/plans | verified |
| C86 | Obsidian: $400-500/month at $4-5/user | obsidian.md/pricing | verified |
| C87 | Word count ≤ 1500 | read tool: 1181 words | verified ✓ |
| C88 | Five apps all present | document structure | verified ✓ |

---

## NOT-CHECKABLE claims (21) — editorial assessments, unchanged

These are subjective comparative assessments present throughout the "Where we can win" section (UX quality, ecosystem size, market maturity comparisons). They cannot be verified or refuted from any cited source. They were present in the first check and remain unchanged.

Examples: "Trilium limited enterprise adoption," "AnyType less mature than Obsidian," "Joplin functional-not-delightful UX," "Logseq small ecosystem," "Obsidian mobile feels secondary," "Trilium lacks collaboration UX."

These do not constitute factual errors per se — they are opinion/editorial statements — but the reader should treat them as such.

---

## Word Count Verification
`read` reports deliverable as 1181 words — within the 1500-word limit ✓ (was 1172 words before rework)

## Scope Verification
All five apps present in table and "Where we can win": Obsidian, Logseq, Joplin, Trilium Notes, AnyType ✓

---

## Summary for rework

3 issues introduced during rework (NEW-1, NEW-2, RC-9 still open), 2 residual from first check (RC-5 partially fixed, RC-9 unresolved):

1. **NEW-1** [HIGH]: Student/educator discount — text fixed, citation broken: change citation back to `https://doc.anytype.io/anytype-docs/memberships/monetization`
2. **NEW-2** [HIGH]: Joplin Server URL 404: replace `https://github.com/joplin/server` with `https://github.com/laurent22/joplin`
3. **RC-5** [MEDIUM]: Logseq Markdown format still unsupported by blog citation — need a source that explicitly states Logseq uses plaintext Markdown
4. **RC-9** [MEDIUM]: "Plaintext sync with any file service" still unsupported — blog post contradicts this (instructs removing graphs FROM file services) — needs revision or new source

The 6 residual unsupported claims from the first check (C47, C52, C64, C65, C66, C70) remain unsupported but were not in the original RC list; they are documented above for transparency.
