# Fact-Check Findings: Competitor Analysis Research
**Fact-Checker:** lead/factcheck  
**Date:** 2026-10-17  
**Deliverable checked:** lead/researcher/work/final_research_data.md (and research_findings.md)  
**Note:** lead/writer/work/competitors.md did not exist at time of check; the writer had not yet produced the final document. Claims checked are sourced from the research data that will feed the final deliverable.

---

## Summary
- **Confirmed:** 7 claims
- **Wrong / Misleading:** 2 claims (high-severity)
- **Unverifiable within budget:** 0

---

## Checked Claims

### Claim 1: Obsidian license — "Free for personal, commercial, and non-profit use. Optional paid licenses (Catalyst, Commercial) available."
- **Source checked:** https://obsidian.md/license
- **Verdict: CONFIRMED**
- The official license page states: "Obsidian is free for all purposes, including personal, commercial, and non-profit use." Optional Catalyst and Commercial licenses are described as optional support mechanisms only.

---

### Claim 2: Logseq license — "AGPL-3.0 open-source license (strong copyleft)"
- **Source checked:** https://github.com/logseq/logseq
- **Verdict: CONFIRMED**
- The GitHub repository sidebar explicitly shows "AGPL-3.0 license" and the repository footer navigation confirms "AGPL-3.0 license."

---

### Claim 3: Joplin license — "Open-source license (AGPL implied, based on GitHub repo structure)" / listed as "AGPL" in comparison table
- **Source checked:** https://github.com/laurent22/joplin/blob/dev/LICENSE
- **Verdict: CONFIRMED** (with clarification)
- The LICENSE file states: "All code in this repository is licensed under the AGPL-3.0-or-later License unless a directory contains a LICENSE or LICENSE.md file." The precise license is AGPL-3.0-or-later (the research says "AGPL implied" which undersells certainty — it is explicit).

---

### Claim 4: Joplin E2EE — "Implements End-To-End Encryption (E2EE). Joplin Cloud encrypts data so staff cannot access user notes."
- **Source checked:** https://joplinapp.org
- **Verdict: CONFIRMED**
- Homepage states: "Uses End-To-End Encryption (E2EE) to secure your notes and ensure no-one but yourself can access them." The French-hosted cloud section adds: "Joplin Cloud implements strong end-to-end encryption so that not even we can access your data."

---

### Claim 5: Obsidian Sync — "Obsidian Sync uses end-to-end encryption for sync service."
- **Source checked:** https://obsidian.md/license (confirmed indirectly); https://obsidian.md/sync (pricing/features page)
- **Verdict: CONFIRMED** (via license page)
- The license/privacy page states: "Sync data is encrypted and inaccessible to our staff." The sync product page confirms it is a paid service (Standard $4/month, Plus $8/month). The sync page does NOT repeat the E2EE claim prominently — the research's cited source (https://obsidian.md/sync) shows the E2EE language is not front-and-center on the current sync page; the claim draws on the license/privacy page. The claim is accurate in substance.

---

### Claim 6: Trilium Notes license — "AGPL-3.0 open-source license" (cited source: https://github.com/zadam/trilium)
- **Source checked:** https://github.com/TriliumNext/Trilium (current active repository)
- **Verdict: CONFIRMED for license type, but WRONG source URL — requires correction**
- The AGPL-3.0 license is confirmed at the current active repo. However, `zadam/trilium` entered maintenance mode in January 2024 and the project was transferred to `TriliumNext/Trilium`. According to GitHub (TriliumNext/Notes README, archived Jun 24, 2025): "TriliumNext started as a fork of the original Trilium repository (zadam/trilium). @zadam transferred the original repo to us so the work will continue in https://github.com/TriliumNext/Trilium." The research cites the legacy/inactive repository. **Correct source URL: https://github.com/TriliumNext/Trilium.**

---

### Claim 7: AnyType license — "Open-source (license details in repository)" / comparison table shows "Open-source"
- **Source checked:** https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md
- **Verdict: WRONG — this is a significant factual error**
- AnyType uses the **"Any Source Available License 1.0"**, which is NOT an OSI-approved open-source license. The license restricts commercial use: it grants rights only for "(a) Non-Commercial Use, or (b) Commercial Use in Allowed Networks" (where Allowed Networks are networks expressly authorized by Any Association). This is a proprietary source-available license with commercial restrictions. Describing AnyType as "open-source" in a competitor analysis for a team building a competing product is materially misleading — especially given the commercial restriction may affect any competing product built on or interoperating with AnyType's codebase.

---

### Claim 8: AnyType self-hosting — "Self-hosted via Docker/Docker Compose. P2P architecture. Local-first design with optional network sync."
- **Source checked:** https://github.com/anyproto/any-sync-dockercompose
- **Verdict: CONFIRMED**
- anyproto maintains an official `any-sync-dockercompose` repository described as "a Docker Compose setup for self-hosting the any-sync network — designed for personal use, review, and testing." Self-hosting is possible and officially supported via Docker Compose. Note: the license restriction (see Claim 7) still applies to the self-hosted software.

---

## REQUIRED CHANGES (ordered by severity)

### HIGH — AnyType License is Wrong
**Location:** All references to AnyType's license in the final analysis  
**Current text (research):** "Open-source (license details in repository)" / comparison table: "Open-source"  
**Correct replacement:** "Source-available (Any Source Available License 1.0) — NOT OSI open-source; restricts commercial use outside Any Association-authorized networks"  
**Why critical:** The target audience is a team building a *competing* product. AnyType's license explicitly restricts commercial use and may create legal exposure if a competitor incorrectly categorizes it as open-source.  
**Primary source:** https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md

### MEDIUM — Trilium Notes Source Repository is Outdated
**Location:** All source citations referencing `https://github.com/zadam/trilium`  
**Current text:** Sources cite `https://github.com/zadam/trilium`  
**Correct replacement:** Replace all `zadam/trilium` source URLs with `https://github.com/TriliumNext/Trilium` — the original author put the project into maintenance mode in January 2024; the active maintained fork (now the canonical project) is at TriliumNext/Trilium.  
**Why important:** The zadam/trilium repository is now read-only/archived. Readers who follow the source URL will find an unmaintained project, undermining credibility and potentially leading to incorrect conclusions about Trilium's activity level.  
**Primary source:** https://github.com/TriliumNext/Trilium; confirmed by https://github.com/TriliumNext/Notes/blob/develop/README.md

### LOW — Joplin License Stated as "Implied" When It Is Explicit
**Location:** research_findings.md Joplin license claim  
**Current text:** "Open-source license (AGPL implied, based on GitHub repo structure)"  
**Correct replacement:** "AGPL-3.0-or-later (explicitly stated in LICENSE file at root of repository)"  
**Why minor:** The final comparison table already correctly says "AGPL" but the supporting claim uses hedged language ("implied") when the license file is unambiguous.  
**Primary source:** https://github.com/laurent22/joplin/blob/dev/LICENSE
