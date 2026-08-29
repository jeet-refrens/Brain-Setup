# Workflow & Documents — Schema

## Summary

> Curated from the live `talos` models, verified 2026-08-06; `advanceOptions` added 2026-08-15.
> `invoices.js` is large (~2150 lines);
> the table below is a curated slice. Use **Source of truth** for exact/complete fields.

### Entities & key fields

| Entity (model) | Key fields (curated) | Notes |
|----------------|----------------------|-------|
| **`invoices`** (all document types) | `invoiceTitle`, `invoiceSubTitle`, `number`, `date`/`dueDate`, `status`(default `UNPAID`), `billType`(default `INVOICE`), `client`/`business`, line items (via `invoiceItems` helper), totals/`discount`/`additionalCharges`/`extraTotalFields`, `payments` (via `getPayments`), `convertedFrom`, `partialConvert`, `isSourceConverted`, `linkedDocuments[]`, `linkedInvoices[]`, `linkedProformaInvoices[]`, `recurringInvoice{...}`, `customHeaders[]`, `customFields`, e-invoice / GST / e-way-bill fields | One collection for invoice, quotation, PO, delivery challan, credit/debit note, etc. Shared fields come from `helpers/documentCommonFields` (`getTitle`/`getNumber`/`getDate`/`getStatus`/`getPayments`). |
| ↳ **`advanceOptions`** (embedded in `invoices`) | `manageInventory` (**resolved** stock effect: `IGNORE`/`BLOCK`/`UPDATE`), `isBatchRequired` | Stamped at save by `serana/src/hooks/manage-document-inventory-flag.js` from business config. **This — not the document type — is what drives `inventorytransactions.transactionType`.** A change to it on an existing document re-runs the inventory effect. See [../inventory/transactions.md](../inventory/transactions.md#how-transactiontype-is-decided--its-business-configuration). |
| **`invoiceaudits`** | `document`→`invoices`, `business`, `user`, `versionNumber`(unique), `action`(`create`/`patch`/`delete`), `oldValues`(Mixed), `isRemoved` | Append-only version history per document. |
| **`documentSignatureRequests`** | `business`, `invoice`→`invoices`, `invoiceAuditId`→`invoiceaudits`, `documentType`(default `INVOICE`), `status`(default `PENDING`), `vendorDocId`(Digio, unique+sparse), `signers[]`, `signedPDF`(S3 key), `expiresAt`, `lastSyncedAt` | E-sign request; `invoiceAuditId` pins the signed version. |
| ↳ **`signers[]`** (embedded) | `signerEmail`, `signerName`, `role`(BUSINESS/CLIENT/INTERNAL), `signatureType`(dsc/eSign), `signURL`, `status`(default `REQUESTED`), `signedAt` | One entry per signer. |
| **`recurringInvoice`** (embedded in `invoices`) | `frequency`, `periodInDays`, `nextDate`, `endDate`, `previousInvoice`/`nextInvoice`/`originInvoice`→`invoices`, `status`(default `DRAFT`) | Recurring-generation chain. |

### Enums (exact, from `fence`)

- **`invoiceStatus`** (`fence/invoices/invoiceStatus.json`): `DRAFT` · `PAID` · `UNPAID` · `OVERDUE` · `PARTIAL` · `CANCELED`.
- **`documentTypes`** (`.../documentTypes.json`): `INVOICE`, `PROFORMAINV`, `QUOTATION`, `PURCHASEORDER`,
  `EXPENDITURE`, `DEBITNOTE`, `CREDITNOTE`, `PAYMENTRECEIPT`, `DELIVERYCHALLAN`, `SALESORDER`.
- **`types`** (`.../types.json`): `INVOICE` (Tax Invoice) · `BOS` (Bill of Supply).
- **`signatureRequestStatus`**: `NONE` · `PENDING` · `SIGNED` · `EXPIRED` · `CANCELLED`.
- **`signerStatus`**: `REQUESTED` · `SIGNED` · `EXPIRED` · `CANCELLED`.
- **`signerRole`**: `BUSINESS` · `CLIENT` · `INTERNAL`.  **`signatureType`**: `dsc` · `eSign`.

### Relationships

- `invoices` —N `invoiceaudits` (`document`); each edit adds a version.
- `invoices` —N `documentSignatureRequests` (`invoice`); each request pins one `invoiceAuditId`.
- Conversion graph: `invoices.convertedFrom` → source `invoices`; `linkedDocuments[]` /
  `linkedInvoices[]` / `linkedProformaInvoices[]` cross-link related documents.
- `recurringInvoice.{previousInvoice,nextInvoice,originInvoice}` chain recurring generations.
- A document's line items reference `inventories` items (drives Inventory movements); payments and
  posting feed Accounting.

## Source of truth

Fetch exact definitions via the GitHub REST API (reference `GITHUB_PAT` **by name only**; `gh` is
**not installed** in this environment) — or run `/sync-schema workflow-documents`.

- **`refrens/talos`** — `src/invoices.js`, `src/invoiceaudits.js`, `src/documentSignatureRequests.ts`,
  `src/documentConfigurations.js`, `src/helpers/documentCommonFields.js`, `src/helpers/document.js`,
  `src/helpers/invoiceItems.js`.
- **`refrens/fence`** — `invoices/invoiceStatus.json`, `documentTypes.json`, `types.json`,
  `signatureRequestStatus.json`, `signerStatus.json`, `signerRole.json`, `signatureType.json`.
- **`refrens/serana`** — Documents Feathers services + hook chains (create/convert/status logic).
  **`refrens/ceres`** — document rendering (Handlebars templates → PDF/HTML).
- **`refrens/birds`** — `src/helpers/get-manage-inventory-flag.ts` (resolves
  `advanceOptions.manageInventory` from business config).
- **Fetch pattern:**
  ```bash
  curl -s -H "Authorization: Bearer $GITHUB_PAT" -H "Accept: application/vnd.github.raw" \
    "https://api.github.com/repos/refrens/talos/contents/src/invoices.js"
  ```
