# Workflow & Documents — Document Workflow

> Grounded in `talos/src/invoices.js` (conversion/linking fields), `invoiceaudits.js`,
> `documentSignatureRequests.ts`, and `fence` enums, verified 2026-08-06. Transition *triggers*
> (what flips each status) are enforced in `serana` hooks — confirm there before relying on exact
> conditions; the states themselves are exact.

## Document types

All types are stored in the single **`invoices`** collection. Types (from
`fence/invoices/documentTypes.json`): `QUOTATION`, `PROFORMAINV`, `SALESORDER`, `PURCHASEORDER`,
`EXPENDITURE` (purchase), `INVOICE`, `DELIVERYCHALLAN`, `CREDITNOTE`, `DEBITNOTE`, `PAYMENTRECEIPT`.

Typical sales flow (conversions are optional and can be partial):

```
Quotation ──► Sales Order ──► Invoice ──► (Payment Receipt)
                              │
Delivery Challan ◄────────────┘   Credit Note / Debit Note adjust an issued Invoice
```

## Conversion & linking model

- **`convertedFrom`** → the source `invoices` document this one was created from.
- **`partialConvert`** / **`isSourceConverted`** — a source can be *partially* converted; the source
  is flagged rather than consumed, so remaining lines can still convert later.
- **`linkedDocuments[]` / `linkedInvoices[]` / `linkedProformaInvoices[]`** — cross-links between
  related documents (references, not conversions).
- **`recurringInvoice`** — chains auto-generated invoices via `previousInvoice` / `nextInvoice` /
  `originInvoice` on a `frequency` / `periodInDays` schedule.

## Status state machine (invoice)

States (`invoices.status`, default `UNPAID`): `DRAFT` · `UNPAID` · `PARTIAL` · `PAID` · `OVERDUE` · `CANCELED`.

| From | Event / action | To | Side effects (other modules) |
|------|----------------|----|------------------------------|
| `DRAFT` | Finalise / issue document | `UNPAID` | Inventory movements generated for stock items; accounting entries posted |
| `UNPAID` | Partial payment recorded | `PARTIAL` | Payment recorded in Accounting |
| `PARTIAL` / `UNPAID` | Full payment recorded | `PAID` | Receivables settled in Accounting |
| `UNPAID` / `PARTIAL` | Due date passes with balance | `OVERDUE` | — |
| any | Cancel document | `CANCELED` | Reversing inventory / accounting effects (confirm in `serana`) |

> Exact transition guards (e.g. what recomputes `PARTIAL` vs `PAID`, how `OVERDUE` is set) live in
> `serana` hooks — treat the triggers above as the intended model and verify before depending on them.

## Versioning

Every create/edit/delete writes an **`invoiceaudits`** row (`versionNumber`, `action` =
`create`/`patch`/`delete`, `oldValues`). This gives a full change history and lets a signature
request pin the exact version that was signed (`invoiceAuditId`).

## E-signature flow (`documentSignatureRequests`, via Digio)

```
create request (status PENDING, pins invoiceAuditId)
  └─ signers[] each REQUESTED ──► SIGNED (signedAt)
       └─ all signed ─► request SIGNED, signedPDF (S3) stored
  └─ expiresAt reached ─► EXPIRED (expire cron sweeps stale PENDING)
  └─ cancelled ─► CANCELLED
```

- Signer `role`: `BUSINESS` · `CLIENT` · `INTERNAL`; `signatureType`: `dsc` · `eSign`.
- `vendorDocId` (unique+sparse) resolves Digio webhooks back to exactly one request.
- `lastSyncedAt` enforces a 5-minute refresh cooldown.

## Rendering

Issued documents are rendered by **`ceres`** (client-side Handlebars → PDF/HTML) from the document
JSON. Editing templates = `ceres`; changing document data/logic = `serana` + `talos`.

## Cross-module dependencies

See [../../cross-module-links.md](../../cross-module-links.md) — document finalisation drives
Inventory movements and Accounting postings; payments settle receivables/payables.
