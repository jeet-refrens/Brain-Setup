# Workflow & Documents — Overview

> Grounded in the live `talos` schemas (`invoices.js`, `invoiceaudits.js`,
> `documentSignatureRequests.ts`) and `fence` enums, verified 2026-08-06. Business logic and the
> Documents Feathers services live in `serana`; PDF/HTML rendering in `ceres`.

## Purpose

Manage the business documents that flow through a sale or purchase — quotations, sales/purchase
orders, invoices, delivery challans, credit/debit notes, payment receipts — and the workflow that
connects them (draft → sent → paid, and conversions like quotation → invoice). One document model
backs all types; status, versioning, and e-signature ride on top.

## Core Entities

- **`invoices`** — the single collection for **all** document types (invoice, quotation, PO,
  delivery challan, etc.), distinguished per type. Holds parties, line items, totals, dates,
  status, and the conversion/linking graph.
- **`invoiceaudits`** — per-document version history (`versionNumber`, `action`, `oldValues`);
  every edit is captured for audit/rollback.
- **`documentSignatureRequests`** — e-signature requests (via Digio vendor) against a document,
  with per-signer state.
- **`documentConfigurations`** — business/document-level configuration for document behaviour.

## Key User Flows

1. **Create a document** — pick a type (quotation, invoice, …), add client/vendor and line items;
   it starts as a draft.
2. **Send & collect payment** — issue to the client; record payments; status moves toward Paid.
3. **Convert / link documents** — turn a quotation or order into an invoice (`convertedFrom`,
   `partialConvert`, `linkedDocuments`) — see [document-workflow.md](document-workflow.md).
4. **Recurring invoices** — auto-generate on a schedule (`recurringInvoice` sub-document).
5. **E-signature** — request signatures from business/client/internal signers; track to Signed.

## Status Lifecycles

- **Invoice status** (`invoices.status`, default `UNPAID`, enum `fence/invoices/invoiceStatus.json`):
  `DRAFT` · `UNPAID` · `PARTIAL` (part paid) · `PAID` · `OVERDUE` · `CANCELED`.
- **Signature request** (`documentSignatureRequests.status`, default `PENDING`):
  `NONE` · `PENDING` · `SIGNED` · `EXPIRED` · `CANCELLED`.
- **Per-signer** (`signers[].status`, default `REQUESTED`): `REQUESTED` · `SIGNED` · `EXPIRED` · `CANCELLED`.
- **Recurring** (`recurringInvoice.status`): see `fence/invoices/recurringInvoiceStatus.json`.

## Known Edge Cases

- **One collection, many document types.** Quotations, POs, invoices, etc. all live in `invoices`;
  don't assume a separate collection per type. (Exact type discriminator — confirm in `serana`;
  `documentSignatureRequests.documentType` uses `fence/invoices/documentTypes.json`.)
- **Partial conversion.** A source document can be partly converted (`partialConvert`,
  `isSourceConverted`) — it isn't a simple one-to-one hand-off.
- **Versioning + signatures.** A signature request pins `invoiceAuditId` — the document version
  that was active when signing started — so later edits don't silently change what was signed.
- **Expiry cron.** Pending Digio requests expire via `expiresAt` (a cron sweeps stale `PENDING`
  requests); a 5-min refresh cooldown is enforced via `lastSyncedAt`.
- **Documents drive Inventory & Accounting.** Confirming a document generates inventory movements
  and accounting entries — see [cross-module-links.md](../../cross-module-links.md).
