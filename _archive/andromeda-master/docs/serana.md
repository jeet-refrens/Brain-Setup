# serana

The core backend API and primary application server for the Refrens platform. Handles business logic for invoices, quotations, purchase orders, contacts, leads, and all core document workflows, serving both the web frontend (`lydia`) and mobile app (`aurora`).

**Tech:** Feathers v4 (Express), MongoDB (Mongoose), Elasticsearch, AWS S3, JavaScript/TS
**Tags:** backend, backend-core, backend-ai, full-stack

## What it contains

- A modular-monolith of 200+ Feathers services under `src/services/`, grouped into Documents (invoices, quotes, POs, delivery challans), CRM (leads, contacts, sales activities), Business (businesses, permissions, collaborators), and Accounting (expenditures, payments, ledgers).
- Hook-driven business logic in `src/hooks/` — validations, side-effects, and permission checks run as before/after hook chains around every service call.
- Mongoose schemas for all entities in `src/models/`, with Elasticsearch sync for high-performance search and filtering.
- Document PDF storage and file attachments via AWS S3; custom auth/OAuth hooks in `src/authentication/`.
- CLI tooling, crons, and data migrations under `src/commands/`.
- Acts as the orchestrator that calls out to `marika` (subscriptions), `saturn` (payments), and `riften` (auth/real-time), and consumes shared packages `birds`, `fence`, `talos`, `mudra`.

## When to reach for it

- Changing invoice, quotation, purchase-order, or delivery-challan business logic.
- Adding a new core API entity or Feathers service, model, or hook chain.
- Working on lead/contact (CRM), business-profile, permission, or accounting/ledger behavior.
- Touching Elasticsearch indexing/search, S3 document storage, or PDF generation flows.
