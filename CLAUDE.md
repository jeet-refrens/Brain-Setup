# Refrens — product context root

## About Refrens

Refrens is a **one-stop ERP platform for SMBs** — a single place for small and medium businesses
to run their operations: invoicing, billing, accounting, inventory management, CRM, and the
documents/workflow that tie them together.

**User base:** ~60% India, ~40% international (notably Saudi Arabia, UAE, Malaysia, USA, UK, and
others). This mix matters for product and analysis work: India-specific tax/compliance (GST,
HSN/SAC, GST states, e-invoice, e-way bill) sits alongside international needs (VAT, multi-currency,
per-country address/tax formats). Don't assume India-only — check whether a flow, field, or report
must also hold for non-Indian businesses.

## This repo

This repo holds product documentation, feature work, data analysis, and experiments for
Refrens. Product knowledge is organised around **four modules**. Read the relevant module docs
before doing feature or analysis work — don't guess field names or flows from memory.

## The four modules

| Module | One-line summary | Docs |
|--------|------------------|------|
| **Accounting** | Double-entry books in a **separate PostgreSQL service** (`saturn`): chart of accounts, vouchers, ledger balances, bank reconciliation, financial + GST reports. Posting from documents is **opt-in per business per document type**. | [docs/modules/accounting/](docs/modules/accounting/) |
| **Inventory** | Stock items, warehouses, valuation, and stock movements. | [docs/modules/inventory/](docs/modules/inventory/) |
| **CRM** | Clients (organisations), contacts (people), leads + pipelines, approval workflows, and third-party lead integrations. | [docs/modules/crm/](docs/modules/crm/) |
| **Workflow & Documents** | Business documents (quotes, orders, invoices) and their conversion/status lifecycle. | [docs/modules/workflow-documents/](docs/modules/workflow-documents/) |

## Querying the data

Ask a data question in plain language — no database ids, collection names, field names, or
join paths needed. Use `/ask-data <question>` or just ask.

[docs/data/](docs/data/) holds the map of what lives where, the confirmed field lists, the
join map, and the safety rules. All Metabase access goes through `python scripts/mb.py`,
which enforces the guardrails and refuses queries that would scan a production collection.

**The two rules:** never guess a field, look it up or ask. Never read a whole collection.

## Working rules

- **Before feature or analysis work**, read the relevant module's `overview.md` **and**
  `schema.md`. Start from the curated Summary; only chase the "Source of truth" repo when you
  need exact field-level precision.
- **If your work touches more than one module**, read
  [docs/cross-module-links.md](docs/cross-module-links.md) — it maps how an event in one
  module ripples into the others.
- **Before introducing any new field name, status, or term**, check
  [docs/glossary.md](docs/glossary.md) and reuse the existing name if one fits. Add new terms
  there rather than inventing synonyms.
- [docs/repo-map.md](docs/repo-map.md) maps the underlying Refrens code repositories — use it
  to find which repo owns a given piece of behaviour.
- **Before showing or saving any doc, task, spec, or analysis write-up — new or edited — run
  the `plain-english` skill over it.** Small words, short sentences, short paragraphs, every
  big word explained on first use, nothing that doesn't change what the reader does. It keeps
  field names, enum values, thresholds, and requirement strength exact. This applies to
  hand-written edits too, not just skill-generated docs.

## Where work lives

- `features/` — feature specs and prototypes (see `/refrens-idea`, the entry point for any new
  feature/epic/enhancement/bug).
- `analysis/` — Metabase / data-analysis work (see `analysis/CLAUDE.md` and `/analysis-kickoff`).
- `experiments/` — throwaway spikes (see `experiments/CLAUDE.md` and `/experiment-kickoff`).
- `_archive/` — retired material kept for reference; do not build on it.

## Secrets — never print or paste

The live `.env` in this folder holds `GITHUB_PAT`, `ASANA_PAT`, `METABASE_API_KEY`,
`METABASE_URL`, and `RAILWAY_TOKEN`. **Never print, echo, paste, or embed their values** in
files, messages, commits, or logs. Reference them **by name only** when invoking the `gh` CLI
or any API call, and let the tool read the value from the environment.
