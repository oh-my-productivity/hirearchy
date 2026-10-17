# Self-Hosted Note-Taking / Knowledge-Base Apps: Competitor Analysis

**Date**: 2026-10-17  
**Audience**: Technical evaluators considering self-hosted note-taking or knowledge-base deployment  
**Scope**: 8 shortlisted apps as of October 2026

---

## Executive Summary

Eight self-hosted note-taking and knowledge-base apps were evaluated: **Joplin**, **TriliumNext (Trilium)**, **Memos**, **Outline**, **SiYuan**, **AFFiNE**, **AppFlowy**, and **Docmost**.

Key findings:

- **AppFlowy** (77.5k stars) and **AFFiNE** (73.6k stars) lead on community traction but both are venture-backed and still pre-1.0, with collaboration features that require paid or enterprise plans.
- **Joplin** has the best-documented client-side E2EE (all apps, AES-256-GCM) and is best suited to privacy-focused solo users. SiYuan's sync is also end-to-end encrypted [[23]](#sources-list).
- **Outline** is the strongest team wiki option but has no native email+password login (SSO/OIDC/SAML, or email magic-link sign-in once SMTP is configured) [[49]](#sources-list) and carries a Business Source License (BSL-1.1) that prohibits offering it as a service.
- **Docmost** is the most Confluence-like drop-in: real-time collaboration, simple Docker Compose deployment, no external SSO requirement, and a fully AGPL-3.0 core.
- **Memos** and **TriliumNext** are the lightest-footprint options. Memos is a microblog-style capture tool; TriliumNext is a powerful solo knowledge base with a hierarchical tree and scripting API.
- **SiYuan** offers the richest feature set for a solo power user (block editor, backlinks, databases, E2EE sync) but has a Chinese-origin governance and a subscription requirement to unlock cloud sync.
- No single app is best for all use cases. Selection depends on team size, privacy requirements, collaboration needs, and operational complexity tolerance.

Six apps were evaluated and dropped before shortlisting (HedgeDoc, SilverBullet, BookStack, Standard Notes, Notesnook, Logseq) due to maturity gaps, niche positioning, or experimental self-hosting status.

---

## Methodology and Limitations

**Sources**: GitHub repositories, official documentation, release notes, and third-party deployment guides (all URLs cited inline). Research conducted on 2026-10-17.

**Approach**: Each app was assessed on community health (stars, commit activity, release cadence, maintainer structure), feature coverage, self-hosting complexity, licensing, and risk profile. No hands-on testing was performed; all claims derive from published documentation and release notes.

**Limitations**:

- Resource requirements (RAM, CPU) are not confirmed for most apps; those claims are flagged UNVERIFIED.
- Some feature details (full import/export lists, SSO specifics, backlink implementations) could not be confirmed from primary sources and are flagged UNVERIFIED.
- Pre-release software (SiYuan alpha, AFFiNE canary) may change between this report and deployment.
- Star counts are snapshots as of the research date and shift over time.

---

## Landscape Table

All 8 shortlisted apps at a glance.

| App | Stars | Latest Release | License | E2EE | Real-Time Collab | Deployment |
|-----|-------|----------------|---------|------|------------------|------------|
| Joplin | 56.8k [[1]](#sources-list) | v3.7.21 (2026-09-25) [[2]](#sources-list) | AGPL-3.0-or-later (Joplin Server: Personal Use License) [[50]](#sources-list) | Yes (AES-256-GCM) [[4]](#sources-list) | No [[5]](#sources-list) | Docker [[6]](#sources-list) |
| TriliumNext | 38.4k [[7]](#sources-list) | v0.106.0 (Jul 2026) [[8]](#sources-list) | AGPL-3.0 [[7]](#sources-list) | No [[9]](#sources-list) | No [[10]](#sources-list) | Docker / binary [[11]](#sources-list) |
| Memos | 63.9k [[12]](#sources-list) | v0.31.0 / 26.10-rc.1 [[13]](#sources-list) | MIT [[12]](#sources-list) | No [[14]](#sources-list) | No [[15]](#sources-list) | Docker [[16]](#sources-list) |
| Outline | 40.9k [[17]](#sources-list) | v1.11.0 (2026-10-12) [[18]](#sources-list) | BSL-1.1 [[19]](#sources-list) | No [[17]](#sources-list) | Yes [[17]](#sources-list) | Docker Compose [[20]](#sources-list) |
| SiYuan | 46.8k [[21]](#sources-list) | v3.8.8-alpha.3 (2026-10-16) — latest stable UNVERIFIED [[22]](#sources-list) | AGPL-3.0 [[21]](#sources-list) | Yes (sync E2EE) [[23]](#sources-list) | No [[24]](#sources-list) | Docker / binary [[25]](#sources-list) |
| AFFiNE | 73.6k [[26]](#sources-list) | v0.27.x stable (Jul 2026) [[27]](#sources-list) | MIT [[26]](#sources-list) | UNVERIFIED [[28]](#sources-list) | Yes [[29]](#sources-list) | Docker Compose [[30]](#sources-list) |
| AppFlowy | 77.5k [[31]](#sources-list) | v0.14.8 (2026-10-08) [[32]](#sources-list) | AGPL-3.0 [[31]](#sources-list) | No [[31]](#sources-list) | Yes [[33]](#sources-list) | Docker Compose [[33]](#sources-list) |
| Docmost | 22.0k [[34]](#sources-list) | v0.96.0 (2026-09-08) [[35]](#sources-list) | AGPL-3.0 (core) [[34]](#sources-list) | No (server-side AES only) [[36]](#sources-list) | Yes [[36]](#sources-list) | Docker Compose [[34]](#sources-list) |

---

## Feature Matrix

One row per app across nine dimensions.

| App | Editor | Organization | Search | Backlinks | E2EE | Collaboration | Mobile | Plugins / API | Import / Export |
|-----|--------|-------------|--------|-----------|------|---------------|--------|---------------|-----------------| 
| **Joplin** | Markdown + optional WYSIWYG [[37]](#sources-list) | Notebooks (hierarchical), tags [[37]](#sources-list) | Full-text; AI-assisted in v3.7 [[2]](#sources-list) | No built-in (plugins exist — UNVERIFIED names) [[37]](#sources-list) | Yes — AES-256-GCM [[4]](#sources-list) | No [[5]](#sources-list) | iOS, Android [[37]](#sources-list) | Rich plugin ecosystem + REST API [[38]](#sources-list) | Import: ENEX, MD, HTML [[2]](#sources-list); Export: MD, HTML, PDF, JEX [[37]](#sources-list) |
| **TriliumNext** | WYSIWYG (CKEditor); code, canvas (Excalidraw), mind map [[11]](#sources-list) | Hierarchical note tree; labels/relations as tags [[9]](#sources-list) | Full-text [[9]](#sources-list) | Yes — bidirectional links, note map/graph [[9]](#sources-list) | No (transport TLS; individual note encryption UNVERIFIED) [[9]](#sources-list) | No [[10]](#sources-list) | None (web interface only) [[11]](#sources-list) | Extensive JS scripting API [[9]](#sources-list) | Import: MD, OPML, ENEX (UNVERIFIED full list) [[9]](#sources-list); Export: MD, HTML, PDF, OPML (UNVERIFIED full list) [[9]](#sources-list) |
| **Memos** | Markdown inline preview [[39]](#sources-list) | Tags, spaces, timeline/calendar views [[13]](#sources-list) | Full-text [[39]](#sources-list) | No (UNVERIFIED) [[13]](#sources-list) | No [[14]](#sources-list) | No (UNVERIFIED) [[15]](#sources-list) | Web only (responsive) [[14]](#sources-list) | REST API + gRPC API [[13]](#sources-list) | Import: UNVERIFIED; Export: UNVERIFIED |
| **Outline** | WYSIWYG rich text / Markdown shortcuts (ProseMirror) [[17]](#sources-list) | Collections, documents, sub-documents [[18]](#sources-list) | Fast full-text [[17]](#sources-list) | UNVERIFIED [[17]](#sources-list) | No [[17]](#sources-list) | Yes [[17]](#sources-list) | iOS, Android [[40]](#sources-list) | REST API; integrations (Slack, GitHub); MCP server (v1.11.0) [[18]](#sources-list) | Import: MD, Notion, Confluence, HTML, Word, OKF [[18]](#sources-list); Export: MD, HTML, PDF [[18]](#sources-list) |
| **SiYuan** | WYSIWYG block editor (20+ block types, Markdown-compatible) [[25]](#sources-list) | Hierarchical notebooks + blocks; tags; databases with relations/rollups [[25]](#sources-list) | SQL-based full-text (block level) [[25]](#sources-list) | Yes — block-level bidirectional links, backlinks panel, global graph [[25]](#sources-list) | Yes — incremental, E2EE sync [[23]](#sources-list) | No (UNVERIFIED team sync in server mode) [[24]](#sources-list) | iOS, Android, HarmonyOS [[23]](#sources-list) | Plugin marketplace (Bazaar) + REST API + MCP [[41]](#sources-list) | Import: MD, HTML, ENEX (UNVERIFIED full list) [[25]](#sources-list); Export: MD, HTML, PDF, Word (UNVERIFIED full list) [[25]](#sources-list) |
| **AFFiNE** | Block editor (WYSIWYG) + infinite canvas / whiteboard; CRDT-based [[26]](#sources-list) | Pages, collections, databases; multi-view [[26]](#sources-list) | Full-text [[42]](#sources-list) | Yes — linked pages, graph view [[26]](#sources-list) | UNVERIFIED (local-first mode local; server mode unconfirmed) [[28]](#sources-list) | Yes — CRDT real-time [[29]](#sources-list) | iOS, Android [[43]](#sources-list) | Plugin system + REST API [[42]](#sources-list) | Import: MD, Notion, Obsidian, Bear, OneNote [[44]](#sources-list); Export: MD, HTML, PDF (UNVERIFIED full list) [[44]](#sources-list) |
| **AppFlowy** | Block editor (WYSIWYG, Notion-like; Flutter + Rust) [[31]](#sources-list) | Spaces, docs, databases (Kanban, grid, calendar), wikis [[45]](#sources-list) | Full-text [[43]](#sources-list) | No built-in (UNVERIFIED) [[31]](#sources-list) | No [[31]](#sources-list) | Yes (with AppFlowy Cloud backend) [[33]](#sources-list) | iOS, Android [[43]](#sources-list) | REST API; plugin ecosystem depth UNVERIFIED [[31]](#sources-list) | Import: MD, Notion (UNVERIFIED full list) [[31]](#sources-list); Export: MD, CSV (UNVERIFIED full list) [[31]](#sources-list) |
| **Docmost** | WYSIWYG collaborative rich text (ProseMirror) [[34]](#sources-list) | Spaces, pages, sub-pages; permissions per space [[34]](#sources-list) | Full-text with enhanced filters (v0.96.0) [[36]](#sources-list) | UNVERIFIED [[34]](#sources-list) | No (server-side AES-256-GCM only, not client-side) [[36]](#sources-list) | Yes — real-time (Hocuspocus v4) [[36]](#sources-list) | No native apps (web only — UNVERIFIED) [[34]](#sources-list) | REST API; MCP OAuth (v0.96.0); diagrams (Draw.io, Excalidraw, Mermaid) [[36]](#sources-list) | Import: MD, Confluence, Notion (UNVERIFIED full list) [[34]](#sources-list); Export: MD, HTML, PDF (UNVERIFIED full list) [[34]](#sources-list) |

---

## Ops/Licensing Comparison

| App | Deployment Dependencies | Resource Requirements | Backup Method | Auth / SSO | License Implications | Paid-Tier Gating | Release Cadence |
|-----|------------------------|----------------------|---------------|------------|---------------------|-----------------|----------------|
| **Joplin** | Docker; PostgreSQL or SQLite; Node.js [[3]](#sources-list) [[6]](#sources-list) | UNVERIFIED (lightweight relative to Outline) [[6]](#sources-list) | pg_dump / JEX export [[6]](#sources-list) | Email/password; SSO UNVERIFIED for free tier [[6]](#sources-list) | Main repo AGPL-3.0-or-later; **Joplin Server is under a Personal Use License (non-commercial only; check before business use)** [[50]](#sources-list) | Personal self-hosted free; Joplin Server Business (paid) adds business features [[5]](#sources-list) | Multiple patches/month; major releases ~quarterly [[2]](#sources-list) |
| **TriliumNext** | Docker or binary; SQLite (bundled) [[9]](#sources-list) [[11]](#sources-list) | UNVERIFIED (lightweight; single binary) [[9]](#sources-list) | SQLite file backup; built-in DB export [[9]](#sources-list) | Username/password; OIDC SSO (v0.95.0) [[11]](#sources-list) | AGPL-3.0 — copyleft; source disclosure required if distributed [[7]](#sources-list) | None; fully open source [[10]](#sources-list) | Frequent; multiple per month [[46]](#sources-list) |
| **Memos** | Docker; Go binary; SQLite (default) or PostgreSQL [[16]](#sources-list) | Very lightweight (Go + SQLite) [[16]](#sources-list) | SQLite file copy or pg_dump [[16]](#sources-list) | Local auth; OAuth/SSO available [[13]](#sources-list) | MIT — no restrictions | None; fully open source [[14]](#sources-list) | ~Monthly; switching to calendar versioning [[13]](#sources-list) |
| **Outline** | Docker Compose; PostgreSQL; Redis; S3-compatible storage; an auth provider (OIDC/SSO) or SMTP for magic-link sign-in [[20]](#sources-list) | Moderate (4 services minimum — UNVERIFIED exact RAM) [[20]](#sources-list) | pg_dump + S3 backup [[20]](#sources-list) | No native email+password. Sign-in via OIDC/SSO (Google, Slack, Azure AD, or self-hosted) **or** email magic link (needs SMTP) [[49]](#sources-list) [[47]](#sources-list) | BSL-1.1 — **self-hosting for own org is permitted; offering as a service to others is NOT** [[19]](#sources-list) | Self-hosted free for own org; cloud SaaS is Outline's commercial product; some enterprise features UNVERIFIED [[40]](#sources-list) | Monthly major releases [[18]](#sources-list) |
| **SiYuan** | Docker or binary; no external database [[25]](#sources-list) | Lightweight (single Docker container) [[41]](#sources-list) | Built-in snapshot/backup; S3/WebDAV options [[23]](#sources-list) | Token-based (Docker); full SSO UNVERIFIED [[25]](#sources-list) | AGPL-3.0 — copyleft; source disclosure required if distributed [[21]](#sources-list) | All local features free; subscription (~$64 lifetime or monthly) unlocks cloud sync and S3/WebDAV backup [[23]](#sources-list) | Daily/weekly alpha; frequent stable releases [[22]](#sources-list) |
| **AFFiNE** | Docker Compose; PostgreSQL; Redis (4 containers) [[30]](#sources-list) | UNVERIFIED (moderate; 4 containers) [[30]](#sources-list) | pg_dump + volume backup (UNVERIFIED official strategy) [[30]](#sources-list) | Built-in auth; OIDC/SSO UNVERIFIED [[28]](#sources-list) | MIT (core) — permissive [[26]](#sources-list) | Self-hosted 10 seats free; paid plans unlock more seats and AI features [[29]](#sources-list) | Very frequent canary (daily); stable less often [[27]](#sources-list) |
| **AppFlowy** | Docker Compose; PostgreSQL; Redis; MinIO [[48]](#sources-list) | UNVERIFIED (moderate stack) [[48]](#sources-list) | pg_dump + MinIO/S3 backup (UNVERIFIED official strategy) [[48]](#sources-list) | Email/password; OIDC/SSO supported [[33]](#sources-list) | AGPL-3.0 — copyleft; commercial self-hosted features in separate commercial repo [[48]](#sources-list) | Free tier available; AI and some collaboration features require paid plans [[33]](#sources-list) | Multiple releases/month [[32]](#sources-list) |
| **Docmost** | Docker Compose; PostgreSQL; Redis [[34]](#sources-list) | UNVERIFIED (lightweight Node.js + PostgreSQL + Redis) [[34]](#sources-list) | pg_dump [[34]](#sources-list) | Built-in email/password (no external SSO required); LDAP/SSO UNVERIFIED [[47]](#sources-list) | AGPL-3.0 (core) + commercial license for enterprise features [[34]](#sources-list) | Core fully open source; enterprise features (SIEM, AI Chat controls, MCP OAuth, Turbopuffer AI search) require enterprise license [[36]](#sources-list) | ~Monthly [[35]](#sources-list) |

---

## Per-App Profiles

### Joplin

**Landscape health**: Mature, stable, large community (56.8k stars) [[1]](#sources-list). Solo primary maintainer (Laurent Cozic) is a key-person risk, though the project has 15,956 commits and multiple patch releases per month [[1]](#sources-list) [[2]](#sources-list).

**Key features**: Markdown-first editor with optional WYSIWYG toggle; hierarchical notebooks and tags; full-text search with AI-assisted search in v3.7 [[2]](#sources-list); E2EE (AES-256-GCM) [[4]](#sources-list); rich plugin ecosystem and REST API [[38]](#sources-list); iOS and Android apps [[37]](#sources-list).

**Self-hosting notes**: Official Docker image for Joplin Server; requires PostgreSQL (or SQLite) and Node.js [[6]](#sources-list). Backup via pg_dump or JEX export [[6]](#sources-list). SSO options for the free tier are UNVERIFIED.

**Standout strengths**: Best-documented client-side E2EE in the shortlist (opt-in per sync target; the password cannot be recovered). SiYuan's sync is also E2EE. Excellent Evernote migration path (ENEX import) [[2]](#sources-list). Most mature plugin ecosystem in this group.

**Notable limitations**: No real-time collaboration [[5]](#sources-list). No built-in backlinks or graph view (community plugins exist, UNVERIFIED exact names) [[37]](#sources-list). Business features (team sharing, per-user access controls) require the paid Joplin Server Business tier [[5]](#sources-list).

---

### TriliumNext (Trilium)

**Landscape health**: The original `zadam/trilium` was transferred to the community; `TriliumNext/Notes` was archived June 2025; active development now lives at `TriliumNext/Trilium` (v0.106.0, Jul 2026) [[8]](#sources-list). Active repo has 38.4k stars [[7]](#sources-list). Multi-contributor community org; lead developer @eliandoran [[10]](#sources-list).

**Key features**: WYSIWYG note editor (CKEditor); hierarchical note tree (notes as parent/child); multiple note types (text, code, canvas/Excalidraw, mind map) [[11]](#sources-list); bidirectional links, note relations, and note map/graph view [[9]](#sources-list); extensive JavaScript scripting API [[9]](#sources-list); OIDC SSO (added v0.95.0) [[11]](#sources-list).

**Self-hosting notes**: Lightweight — Docker or standalone binary; SQLite bundled, no external database required [[9]](#sources-list) [[11]](#sources-list). Backup via SQLite file copy or built-in export [[9]](#sources-list).

**Standout strengths**: Most flexible personal knowledge base in the group — hierarchical tree plus relations model is uniquely powerful for complex, interconnected notes. No external dependencies for basic deployment. Fully open source with no paid tier [[10]](#sources-list).

**Notable limitations**: Single-user design; no real-time collaboration [[10]](#sources-list). No native mobile apps (web interface only) [[11]](#sources-list). Repo transition (zadam → TriliumNext/Notes → TriliumNext/Trilium) may concern teams evaluating long-term governance.

---

### Memos

**Landscape health**: 63.9k stars [[12]](#sources-list); MIT license; 4,884 commits; very active [[12]](#sources-list). Transitioning to calendar versioning (26.10, 26.11...) [[13]](#sources-list). Single-lead maintainer with community contributors.

**Key features**: Microblog-style Markdown capture (rebuilt editor in v0.30) [[39]](#sources-list); tags, spaces, timeline and calendar views [[13]](#sources-list); full-text search [[39]](#sources-list); REST API and gRPC API [[13]](#sources-list).

**Self-hosting notes**: Simplest deployment of the group — single Docker container, Go binary, SQLite by default (PostgreSQL optional) [[16]](#sources-list). Very lightweight resource footprint [[16]](#sources-list). Backup via SQLite file copy [[16]](#sources-list). OAuth/SSO options available [[13]](#sources-list).

**Standout strengths**: Fastest to deploy. Extremely low operational overhead. MIT license. Strong API surface (REST + gRPC) for integration.

**Notable limitations**: Microblog-style tool — not a full-featured document or wiki editor. No E2EE [[14]](#sources-list). No real-time collaboration (UNVERIFIED) [[15]](#sources-list). No native mobile apps (web only) [[14]](#sources-list). Import/export formats are UNVERIFIED. Not suitable as a team knowledge base or document editor.

---

### Outline

**Landscape health**: 40.9k stars [[17]](#sources-list); commercially backed (Tom Moor / getoutline.com); 10,691 commits; monthly major releases [[17]](#sources-list) [[18]](#sources-list). Actively developed with a clear commercial incentive (cloud SaaS offering).

**Key features**: WYSIWYG ProseMirror editor with Markdown shortcuts [[17]](#sources-list); hierarchical collections and documents [[18]](#sources-list); fast full-text search [[17]](#sources-list); real-time collaborative editing [[17]](#sources-list); iOS and Android apps [[40]](#sources-list); REST API, Slack/GitHub integrations, MCP server (v1.11.0) [[18]](#sources-list); rich import (Notion, Confluence, Word, HTML, OKF) [[18]](#sources-list).

**Self-hosting notes**: Requires Docker Compose with PostgreSQL, Redis, S3-compatible storage, and either an OIDC/SSO provider or an SMTP server for email magic-link sign-in [[49]](#sources-list) [[47]](#sources-list). No native email+password auth, so plan the login method before deploying. Backup via pg_dump + S3 [[20]](#sources-list).

**Standout strengths**: Best-in-class team wiki experience. Real-time collaboration, native mobile apps, rich integrations, and strong import capabilities. Most "Confluence-like" UX in the group.

**Notable limitations**: BSL-1.1 license: **you may not offer Outline as a service to third parties** [[19]](#sources-list). No password login: you need an SSO provider or SMTP for magic links, which adds setup for small teams. No E2EE [[17]](#sources-list). Some enterprise feature details UNVERIFIED [[40]](#sources-list). Backlinks UNVERIFIED [[17]](#sources-list).

---

### SiYuan

**Landscape health**: 46.8k stars [[21]](#sources-list); AGPL-3.0; 28,933 commits — highest commit volume in the group [[21]](#sources-list). Daily/weekly releases (alpha and stable) [[22]](#sources-list). B3log open-source group (China); lead dev @88250. Latest stable version is UNVERIFIED exact number; v3.8.8-alpha.3 is current pre-release [[22]](#sources-list).

**Key features**: WYSIWYG block editor (20+ block types, Markdown-compatible) [[25]](#sources-list); hierarchical notebooks and block-level organization; databases with relations and rollups [[25]](#sources-list); block-level bidirectional links, backlinks panel, global graph view [[25]](#sources-list); E2EE incremental sync [[23]](#sources-list); iOS, Android, and HarmonyOS apps [[23]](#sources-list); plugin marketplace (Bazaar), REST API, MCP support [[41]](#sources-list).

**Self-hosting notes**: Lightweight — single Docker container or desktop binary; no external database [[25]](#sources-list) [[41]](#sources-list). Built-in snapshot/backup plus S3/WebDAV options [[23]](#sources-list). Auth is token-based for Docker; full SSO is UNVERIFIED [[25]](#sources-list).

**Standout strengths**: Richest solo-user feature set — block-level structure, relations, rollups, graph, E2EE, and MCP in one self-hostable package. Supports HarmonyOS (unique in this group). Lightest server footprint among feature-rich apps.

**Notable limitations**: No real-time collaboration (UNVERIFIED for server multi-user) [[24]](#sources-list). Cloud sync and S3/WebDAV backup require a paid subscription (~$64 lifetime) [[23]](#sources-list). Chinese-origin governance may concern organizations with data-sovereignty requirements. Extremely rapid release cadence (daily alphas) may introduce instability. Latest stable version unconfirmed.

---

### AFFiNE

**Landscape health**: 73.6k stars [[26]](#sources-list); MIT license (core); venture-backed (toeverything); 11,533 commits [[26]](#sources-list). Latest stable is v0.27.x (Jul 2026); active canary releases daily [[27]](#sources-list). Pre-1.0 product.

**Key features**: Block editor + **infinite canvas/whiteboard** (Excalidraw-style) in a unified interface; CRDT-based [[26]](#sources-list); linked pages and graph view [[26]](#sources-list); real-time collaboration [[29]](#sources-list); full-text search [[42]](#sources-list); rich importer (Notion, Obsidian, Bear, OneNote added in v0.27) [[44]](#sources-list); iOS and Android [[43]](#sources-list).

**Self-hosting notes**: Docker Compose with 4 containers (app, migration, PostgreSQL, Redis) [[30]](#sources-list). Backup via pg_dump and volume backup (official strategy UNVERIFIED) [[30]](#sources-list). OIDC/SSO UNVERIFIED [[28]](#sources-list). Self-hosted includes 10 free seats; more seats and AI features are paid [[29]](#sources-list).

**Standout strengths**: Unique canvas/whiteboard capability alongside document editing. Widest import coverage in the group. CRDT-based collaboration is architecturally robust.

**Notable limitations**: Still pre-1.0 and described as canary/pre-release for the latest builds [[27]](#sources-list). E2EE status UNVERIFIED [[28]](#sources-list). Seat-limited free tier may surprise teams that grow. Venture-backed with unclear long-term open-core model. Resource requirements UNVERIFIED.

---

### AppFlowy

**Landscape health**: Highest star count in the group (77.5k) [[31]](#sources-list); AGPL-3.0; venture-backed (AppFlowy-IO); 7,210 commits [[31]](#sources-list). Very active (multiple releases/month) [[32]](#sources-list). Pre-1.0. Commercial self-hosted features in a **separate** repo (AppFlowy-SelfHost-Commercial) [[48]](#sources-list).

**Key features**: Block editor (WYSIWYG, Notion-like; Flutter + Rust) [[31]](#sources-list); spaces, documents, databases (Kanban, grid, calendar), wikis [[45]](#sources-list); full-text search [[43]](#sources-list); real-time collaboration with AppFlowy Cloud backend [[33]](#sources-list); iOS and Android [[43]](#sources-list); OIDC/SSO supported [[33]](#sources-list).

**Self-hosting notes**: Docker Compose; requires PostgreSQL, Redis, and MinIO (S3-compatible object storage) [[48]](#sources-list). Auth with email/password and OIDC/SSO [[33]](#sources-list). Backup strategy (pg_dump + MinIO) UNVERIFIED officially [[48]](#sources-list).

**Standout strengths**: Most familiar Notion-like UX. Highest community traction. Strong database views (Kanban, grid, calendar). Native SSO support without requiring an external OIDC gateway.

**Notable limitations**: AGPL-3.0 — source disclosure required if distributed as a service [[31]](#sources-list). Commercial self-hosted features split into a separate proprietary repo [[48]](#sources-list). AI and some collaboration features require paid plans [[33]](#sources-list). No built-in backlinks or graph (UNVERIFIED) [[31]](#sources-list). Plugin depth UNVERIFIED [[31]](#sources-list). Still pre-1.0.

---

### Docmost

**Landscape health**: 22.0k stars [[34]](#sources-list) — smallest community in the group. AGPL-3.0 (core); solo primary maintainer (@Philipinho) [[35]](#sources-list); 1,172 commits [[34]](#sources-list). Actively developed with roughly monthly releases [[35]](#sources-list).

**Key features**: WYSIWYG ProseMirror editor [[34]](#sources-list); spaces, pages, sub-pages with per-space permissions [[34]](#sources-list); real-time collaboration (Hocuspocus v4) [[36]](#sources-list); full-text search with enhanced filters (v0.96.0) [[36]](#sources-list); REST API; MCP OAuth (v0.96.0); diagrams (Draw.io, Excalidraw, Mermaid) [[36]](#sources-list); AES-256-GCM server-side encryption [[36]](#sources-list).

**Self-hosting notes**: Simple Docker Compose; PostgreSQL and Redis [[34]](#sources-list). Built-in email/password auth — **no external SSO provider required** [[47]](#sources-list). Backup via pg_dump [[34]](#sources-list). LDAP/SSO UNVERIFIED. Enterprise features (SIEM, AI Chat controls, MCP OAuth, Turbopuffer AI search) under a commercial license [[36]](#sources-list).

**Standout strengths**: Easiest team wiki to self-host with real-time collaboration — no SSO provider needed (built-in email/password). Simple operational model (2 backing services). Clean open-source core with predictable commercial extension line.

**Notable limitations**: Smallest community and least battle-tested. Solo maintainer is a key-person risk. No client-side E2EE [[36]](#sources-list). Backlinks UNVERIFIED [[34]](#sources-list). No native mobile apps (UNVERIFIED) [[34]](#sources-list).

---

## Persona Recommendations

### Solo Power User

**Recommended**: **SiYuan**  
Rationale: Richest feature set for a single user — block editor, databases, backlinks, graph view, E2EE sync, MCP support, and lightweight Docker deployment [[25]](#sources-list) [[23]](#sources-list). All local features are free; cloud sync requires a subscription (one-time ~$64) [[23]](#sources-list). No collaboration required.

**Runner-up**: **TriliumNext** — best if the user prefers a hierarchical note-tree model and deep scripting without any paid features [[9]](#sources-list).

---

### Privacy-Focused User

**Recommended**: **Joplin**  
Rationale: Best-documented client-side E2EE (AES-256-GCM) [[4]](#sources-list); data is encrypted before it leaves the device once E2EE is enabled. Main repo is AGPL-3.0-or-later; Joplin Server is Personal Use licensed, which fits personal self-hosting but not business use [[50]](#sources-list).

**Caveat**: No real-time collaboration and no backlinks by default [[5]](#sources-list) [[37]](#sources-list).

---

### Small Team (2–20 people)

**Recommended**: **Docmost**  
Rationale: Real-time collaboration, built-in email/password auth (no OIDC dependency), simple Docker Compose deployment with 2 backing services, fully open-source core [[34]](#sources-list) [[36]](#sources-list) [[47]](#sources-list). Lower operational complexity than Outline or AppFlowy for small teams without an existing identity provider.

**Runner-up**: **AppFlowy** — better Notion-like UX and native SSO, but heavier stack (adds MinIO) and more features gated behind paid plans [[33]](#sources-list) [[48]](#sources-list).

---

### Org Wiki / Knowledge Base

**Recommended**: **Outline**  
Rationale: Best-in-class team wiki UX with real-time collaboration, native mobile apps, rich integrations (Slack, GitHub, MCP), and the strongest import story (Notion, Confluence, Word) [[17]](#sources-list) [[18]](#sources-list). Monthly releases with commercial backing provide predictable maintenance [[18]](#sources-list).

**Caveat**: BSL-1.1 license prohibits offering as a service [[19]](#sources-list). No password login: use an OIDC provider (e.g., Authentik, Keycloak, or a cloud IdP) or configure SMTP for email magic-link sign-in [[49]](#sources-list) [[47]](#sources-list). Easiest for organizations that already have an identity provider.

---

### Minimal Footprint

**Recommended**: **Memos**  
Rationale: Single Docker container, Go binary, SQLite by default, near-zero configuration [[16]](#sources-list). MIT license, no paid tiers, REST + gRPC APIs [[12]](#sources-list) [[13]](#sources-list). Ideal for quick capture, personal logs, or lightweight shared note streams.

**Caveat**: Not a full document editor or team wiki. No E2EE, no mobile apps, no collaboration [[14]](#sources-list) [[15]](#sources-list). Import/export capabilities UNVERIFIED.

---

## Risks

### Per-App Risks

| App | Key Risks |
|-----|-----------|
| **Joplin** | Solo maintainer key-person risk. Business features behind paid tier. No collaboration. UNVERIFIED SSO for free tier. |
| **TriliumNext** | Three repo migrations (zadam → TriliumNext/Notes → TriliumNext/Trilium) — governance fragility. No mobile. |
| **Memos** | Microblog paradigm limits use cases. Import/export entirely UNVERIFIED. Collaboration UNVERIFIED. Not suitable for teams. |
| **Outline** | **BSL-1.1 license trap**: any offering-as-a-service use is prohibited [[19]](#sources-list). If you choose SSO, the identity provider becomes a dependency that increases blast radius on auth outages (magic-link login via SMTP is the alternative). Backlinks UNVERIFIED. |
| **SiYuan** | Chinese-origin governance (data-sovereignty concerns for some orgs). Paid subscription for cloud sync/backup. Latest stable version unconfirmed. Team collaboration UNVERIFIED in server mode. |
| **AFFiNE** | Pre-1.0 product. E2EE UNVERIFIED. Seat-limited free tier. Venture-backed open-core with uncertain long-term model. Official backup strategy UNVERIFIED. |
| **AppFlowy** | Commercial features split into a separate proprietary repo — dual licensing risk. AGPL-3.0 triggers source-disclosure if distributed. Paid gates on AI and collaboration. Plugin depth UNVERIFIED. Pre-1.0. |
| **Docmost** | Smallest community, least battle-tested. Solo maintainer key-person risk. No mobile apps (UNVERIFIED). Backlinks UNVERIFIED. Enterprise features require commercial license. |

### General Risks

**Governance / bus-factor**: Joplin and Docmost both depend on a single primary maintainer. Joplin's age and community mitigate this; Docmost's is more acute given its smaller contributor base [[1]](#sources-list) [[35]](#sources-list).

**License traps**: Outline's BSL-1.1 is the most significant license risk — operators who later want to resell or offer the service must re-evaluate. AppFlowy's AGPL-3.0 combined with a separate commercial repo creates a fragmented licensing story [[19]](#sources-list) [[48]](#sources-list). TriliumNext's license is confirmed AGPL-3.0 [[7]](#sources-list).

**Vendor lock-in**: AFFiNE and AppFlowy are both venture-backed; open-core models can shift. SiYuan's paid sync is a soft lock-in for users who depend on cloud backup. Outline's BSL converts to Apache 2.0 after 4 years — check the conversion date for your deployed version [[19]](#sources-list).

**Maturity**: AFFiNE and AppFlowy are pre-1.0 [[27]](#sources-list) [[32]](#sources-list). SiYuan's latest stable version is UNVERIFIED [[22]](#sources-list). TriliumNext's active repo is in active migration. Organizations that need production stability should prefer Joplin, Outline, Memos, or Docmost.

**Data sovereignty**: SiYuan's cloud sync routes through B3log servers (China) [[21]](#sources-list). For self-hosted use without cloud sync, this risk is contained; for users relying on SiYuan's paid cloud sync, it is material.

---

## Sources List

1. https://github.com/laurent22/joplin
2. https://github.com/laurent22/joplin/releases/tag/v3.7.21
3. https://github.com/laurent22/joplin/blob/dev/packages/server/README.md
4. https://joplinapp.org/help/dev/spec/e2ee/native_encryption/
5. https://www.joplinapp.org/help/apps/joplin_server_business
6. https://knightli.com/en/2026/06/05/joplin-server-docker-compose-setup/
7. https://github.com/TriliumNext/Trilium
8. https://github.com/orgs/TriliumNext/discussions/11670
9. https://triliumnext.github.io/Notes/Script%20API/
10. https://github.com/TriliumNext
11. https://github.com/TriliumNext/Notes/releases/tag/v0.95.0
12. https://github.com/usememos/memos
13. https://github.com/usememos/memos/releases
14. https://github.com/usememos/memos (MIT; no E2EE)
15. https://github.com/usememos/memos (no real-time collab — UNVERIFIED)
16. https://dev.co/devops/open-source/usememos-memos
17. https://github.com/outline/outline
18. https://github.com/outline/outline/releases/tag/v1.11.0
19. https://hatchbox.io/docs/articles/55-outline
20. https://www.101howto.com/self-host-outline-docker-compose/
21. https://github.com/siyuan-note/siyuan
22. https://github.com/siyuan-note/siyuan/releases
23. https://www.positioniseverything.net/tools/siyuan/
24. https://github.com/siyuan-note/siyuan (no collab — UNVERIFIED server mode)
25. https://computingforgeeks.com/install-siyuan-self-hosted-docker/
26. https://github.com/toeverything/AFFiNE
27. https://blog.elest.io/affine-0-27-new-importers-calendar-view-and-a-sync-warning/
28. https://github.com/toeverything/AFFiNE (E2EE UNVERIFIED)
29. https://www.ssdnodes.com/learn/self-host-affine-notion-alternative
30. https://www.ssdnodes.com/learn/self-host-affine-notion-alternative (Docker Compose 4 containers)
31. https://github.com/AppFlowy-IO/AppFlowy
32. https://github.com/AppFlowy-IO/AppFlowy/releases
33. https://appflowy.com/what-is-new
34. https://github.com/docmost/docmost
35. https://github.com/docmost/docmost/releases/tag/v0.96.0
36. https://github.com/docmost/docmost/releases/tag/v0.96.0 (v0.96.0 features)
37. https://joplinapp.org/
38. https://joplinapp.org/api/
39. https://usememos.com/changelog/0-30-0
40. https://www.getoutline.com/
41. https://xda-developers.com/ditched-notion-20-tier-for-single-docker-container-that-costs-zero/
42. https://docs.affine.pro/self-host-affine
43. https://affine.pro
44. https://blog.elest.io/affine-0-27-new-importers-calendar-view-and-a-sync-warning/ (v0.27 importers)
45. https://appflowy.com/what-is-new (spaces, databases)
46. https://github.com/TriliumNext/Trilium/releases
47. https://contabo.com/blog/docmost-vs-outline-vs-notion/
48. https://github.com/AppFlowy-IO/AppFlowy-selfhost-commercial
49. https://docs.getoutline.com/s/hosting/doc/smtp-cqCJyZGMIB (SMTP is also required for email magic-link sign-in; Outline has no native email+password: https://docs.getoutline.com/s/hosting/doc/authentication-7ViKRmRY5o)
50. https://github.com/laurent22/joplin (root LICENSE: AGPL-3.0-or-later unless a subdirectory has its own license; Joplin Server's LICENSE.md is the Personal Use License, see item 3)
