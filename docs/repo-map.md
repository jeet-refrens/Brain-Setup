# Repo map

What each Refrens code repository is for — use this to find which repo owns a given piece of
behaviour before starting feature or analysis work.

> Consolidated from the former `andromeda-master/` reference notes (the andromeda meta-repo
> `CLAUDE.md` + `README.md` + per-repo `docs/<repo>.md`). Per-repo deep-dive notes are kept in
> `_archive/andromeda-master/docs/<repo>.md`. Fetch exact schema/field detail from the live
> repos via the `gh` CLI (reference `GITHUB_PAT` by name only).

## What andromeda is

`andromeda` is the **meta-repo** for the Refrens engineering setup — it tracks every Refrens
repository in one place and clones each in as an **independent git repo** (it is **not** a
monorepo). Repos are managed with [`mani`](https://manicli.com) and selected by tag; most tasks
span several repos. Feature work uses per-repo git **worktree workspaces** grouped under one
branch. (Setup/usage detail lives in the archived andromeda docs.)

## Backend services

| Repo | Purpose |
|------|---------|
| serana | Core backend API |
| astrid | Admin / back-office API |
| marika | Subscription management product (customer-facing) |
| saturn | Advanced accounting / bookkeeping (PostgreSQL) |
| courier | Email / messaging |
| riften | Real-time Forex rates API |
| stella | AI-powered service |
| dibella | Serverless image / PDF generation |
| shopifyApp | Shopify integration |

## Frontend apps

| Repo | Purpose |
|------|---------|
| lydia | Main web app |
| elisif | Public marketing / SEO pages |
| phobos | Public profile pages |
| sithis | Admin panel |
| aurora | Mobile app (React Native / Expo) |
| kherpa-welcome-space | Lovable-generated Vite/React starter |
| whiterun | CMS (Strapi 3) for elisif |
| ceres | Client-side Handlebars document renderer |

## UI / component libraries

| Repo | Purpose |
|------|---------|
| disco | Refrens component library |
| jupiter | Widget library (built on disco) |

## Shared packages / libraries

| Repo | Purpose |
|------|---------|
| birds | Shared helpers — Feathers hooks (backend) + utils (frontend) |
| fence | Config / constants library |
| mudra | Number / numeric utilities |
| talos | Central Mongoose schema repo (~100 collections) |
| venus | Embeddable contact-form widget (Preact) |
| gst-states | India GST state codes data |
| eslint-config | Shared ESLint config |

## Tools & infrastructure

| Repo | Purpose |
|------|---------|
| azure | Infrastructure as code |
| nebula | Ops / devops orchestration |
| kuiper | CLI repo bootstrapper |
| mercury | API docs (Retype) — legacy, see refrens-docs/api |
| github-deploy | GitHub deployment CLI |
| seeds | Data seeding, migrations & Elastic sync |

## Module → repos

Verified for Accounting and CRM on 2026-08-15; Inventory and Workflow & Documents on 2026-08-06.

- **Accounting** — **`saturn`** owns the books (PostgreSQL: `accountgroups`, `ledgers`, `vouchers`,
  `voucher_entries`, `lineitems`, `financial_years`, bank-reconciliation tables, and the `reports`
  service). **`serana`** owns the trigger (`src/hooks/sync-document-with-voucher-entries.js`, the
  `sync-accounting`/`sync-payments` services) and the Mongo-side feeders (`paymentrecords`,
  `transactions`/`wallets`, `paymentAccounts`, GST services). **`talos`** holds those Mongo schemas;
  **`fence/accounting/`** holds every enum and the default chart-of-accounts templates.
- **Inventory** — `serana` (business logic, hooks), `talos` (schemas), `fence/inventory/` (enums),
  `lydia` (item forms)
- **CRM** — `serana` (clients, contacts, leads, workflows, lead reports and integrations),
  `talos` (schemas; note pipelines live in `businessConfigurations.lms`), `fence/leads/`,
  `fence/contacts/`, `fence/workflows/`, `lydia` (pipeline UI), `venus` (embeddable contact form).
  **`shopifyApp` is a standalone app**, not an `integrations` row.
- **Workflow & Documents** — `serana` (document lifecycle), `ceres` (rendering), `talos` (schemas)

## Reading repo source from this environment

`gh` is **not installed** here. Read files via the GitHub REST API, referencing `GITHUB_PAT`
**by name only** (never print or paste its value):

```bash
curl -s -H "Authorization: Bearer $GITHUB_PAT" -H "Accept: application/vnd.github.raw" \
  "https://api.github.com/repos/refrens/talos/contents/src/clients.js"
```

Directory listing uses the same endpoint without the `raw` Accept header. Load the token into the
environment from `.env` without echoing it, e.g.
`export GITHUB_PAT="$(grep -E '^GITHUB_PAT' .env | sed -E 's/^[^=]*=[[:space:]]*//' | tr -d '\r\n')"`.
