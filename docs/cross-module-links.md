# Cross-module links

How an event in one module ripples into the others. **Read this whenever a feature or analysis
touches more than one module** so you don't miss a downstream effect.

Columns describe the impact of the **Trigger Event** on each module. "—" means no direct impact.

> Rows for **Inventory** and **Workflow & Documents** are grounded in the live schemas (item
> `*Ledger` mappings, `inventorytransactions.docType`/`type`, invoice status, conversion fields;
> verified 2026-08-06). **Accounting** and **CRM** cells are grounded in `saturn` migrations,
> `talos` schemas, `fence` enums and `serana/src/hooks/sync-document-with-voucher-entries.js`
> (verified 2026-08-15) — the *trigger and direction* are confirmed; the **exact ledger legs and
> amounts** are computed in `serana`'s sync-accounting service and `saturn` hooks, so **verify
> there** before depending on precise double-entry detail.

## ⚠️ Both Accounting and Inventory impacts are configuration-driven

**The Inventory and Accounting columns below describe the _default_ behaviour. Neither is fixed
per document type — both are business configuration.** Read this before relying on any cell.

### Inventory: the stock effect is configured per billType

A business chooses, **per document type**, whether that document `UPDATE`s stock, `BLOCK`s
(reserves) it, or `IGNORE`s it. The resolved value is written onto the document as
`advanceOptions.manageInventory` and is what `inventorytransactions.transactionType` is set from.

Resolution order (`birds/src/helpers/get-manage-inventory-flag.ts`, called by
`serana/src/hooks/manage-document-inventory-flag.js`):

1. **Explicit override** — if the incoming payload already carries
   `data.advanceOptions.manageInventory`, it wins and nothing else is consulted.
2. **Business master switch** — `businessConfigurations.manageInventory` (a **Boolean**, default
   `false`). If falsy, **everything resolves to `IGNORE`** — inventory is off entirely.
3. **Per-billType config** — `businessConfigurations.<docType>[0].manageInventory`
   (a **String** enum `IGNORE` · `BLOCK` · `UPDATE`, **no schema default**), for `invoice`,
   `proforma`, `quotation`, `deliveryChallan`, `purchaseOrder`, `expenditure`, `creditNote`,
   `debitNote`, `salesOrder`, `paymentReceipt`. Note the config is an **array** and only element
   `[0]` is read.
4. **Per-billType fallback** when that config is unset:

   | billType | Fallback |
   |---|---|
   | `INVOICE`, expenditure (`isExpenditure`) | `UPDATE` |
   | `PROFORMAINV` | `BLOCK` |
   | `QUOTATION`, `PURCHASEORDER`, `SALESORDER`, `DELIVERYCHALLAN` | `IGNORE` |
   | anything else (`CREDITNOTE`, `DEBITNOTE`, `PAYMENTRECEIPT`, …) | `IGNORE` |

5. **Item-level final gate** — per line item,
   `transactionType = inventory.isStockManaged ? inventoryFlag : 'IGNORE'`. A non-stock-managed
   item always yields `IGNORE`, whatever the document is configured to do.

> **Known doc discrepancy:** `serana/docs/inventory.md` states the `DELIVERYCHALLAN` fallback is
> `UPDATE`; the live resolver in `birds` returns `IGNORE`. **The code is authoritative** —
> `deliveryChallan.manageInventory || 'IGNORE'`. Re-verify if this matters to your work.

Consequences worth knowing:

- **A quotation, sales order or PO does _not_ reserve stock by default** — all three fall back to
  `IGNORE`. `BLOCK` is only the default for **proforma invoices**. A business must opt in to get
  reservation behaviour on the others.
- **The flag is snapshotted onto the document.** Changing the business config later does **not**
  retroactively change existing documents; `advanceOptions.manageInventory` on the saved document
  is what governs. A change to the flag on an existing document is itself a re-sync trigger.
- **`BLOCK_IGNORE` is never configurable.** It is derived at conversion time: when a `BLOCK`ed
  document converts into one resolving to `UPDATE`, the original transaction is patched to
  `BLOCK_IGNORE` so the reservation is cancelled without double-counting.

### Accounting: posting is opt-in per document type

**Every Accounting cell only happens if the business has opted in.** Three gates, all of which
must pass:

1. `businessConfigurations.syncAccounting.<docType>.status` is enabled for that document type.
2. The document is **not** `DRAFT` — drafts never post.
3. The document's `syncBreak.enabled` is false.

If any gate fails, the Accounting cell is a no-op even though the Inventory/CRM cells still fire.

| Trigger Event | Accounting Impact | Inventory Impact | CRM Impact | Workflow/Documents Impact |
|---------------|-------------------|------------------|------------|---------------------------|
| Sales **invoice** finalised (DRAFT→UNPAID) | Voucher entry created in the Sales voucher book (`voucherType: sales`); Dr client party ledger, Cr sales + output tax ledgers (GST `Sales_IGST/CGST/SGST/UTGST` or VAT/SST/PPN/HST per country) | Movements per the configured flag — **default `UPDATE`**: stock-out (`type: SELL`) for stock-managed line items; batch/serial allocated | `clients.balance.invoice` cache updated; `lastCommunication` / `retentionMetrics.docActivity.lastInvoiceDate` refreshed | `invoices.status` → `UNPAID`; `docId` links movements back to the document |
| **Purchase / expenditure** recorded | Voucher entry in the Purchase book (`voucherType: purchase`); Dr expense/asset + input tax (ITC) ledgers, Cr vendor party ledger | Movements per the configured flag — **default `UPDATE`**: stock-in (`type: BUY`); avg cost updated | Vendor client record updated; `balance.expenditure` cache | Purchase document created (`EXPENDITURE`/`PURCHASEORDER`) |
| **Payment** recorded against an invoice | Receipt voucher entry; Dr the `paymentAccounts.ledgerId` account, Cr client party ledger. A `transactions` (wallet) row may also be written with `paymentLedgerId`/`paymentVoucherEntryRefrence` back-references | — | `clients.balance.invoicePayment` updated; `avgPayingDate` recomputed | `status` → `PARTIAL` or `PAID`; `paymentrecords.settledInvoices[]` links the settlement |
| **Quotation / sales order / purchase order** created | — (no posting; these document types are not in `syncAccounting`) | Per the configured flag — **default `IGNORE`** for all three, i.e. no stock effect at all. A business must explicitly configure `BLOCK` to get reservation behaviour | Client linked; if it came from a lead, the lead links to the document and moves stage | Document convertible to invoice (`convertedFrom`, `partialConvert`); may enter an **approval workflow** (`workflowitems`) |
| **Proforma invoice** created | — (not in `syncAccounting`) | Per the configured flag — **default `BLOCK`**: reserves stock (decrements `stock`, leaves `stockInHand` untouched). This is the only document type that reserves by default | Client linked | Convertible to an invoice — on full conversion the `BLOCK` transaction is patched to `BLOCK_IGNORE` so the reservation is released without double-counting the invoice's `UPDATE` |
| **Delivery challan** created | — (not in `syncAccounting`) | Per the configured flag — **default `IGNORE`** in the live resolver. ⚠️ `serana/docs/inventory.md` claims `UPDATE`; verify before relying on either | Client linked | Often converted from / linked to an invoice |
| **Credit note** issued against an invoice | Credit Note voucher entry reversing sale + tax; reduces the client receivable | Sales-return stock-in for returned items (serials → `AVAILABLE`) | `clients.balance.creditNote` adjusted | `CREDITNOTE` linked to the source invoice |
| **Document cancelled / deleted** | `syncBreak` is set (`DOCUMENT_CANCELED` / `DOCUMENT_SOFT_DELETED` / `DOCUMENT_HARD_DELETED`) and a **reversal** voucher entry is written — the original is never deleted | Reversing inventory movements (confirm in `serana`) | Client balance cache adjusted | `status` → `CANCELED` |
| **Document edited after posting** | Only resyncs if an **accounting-relevant** field changed (see [modules/accounting/overview.md](modules/accounting/overview.md) for the exact field list); then the last voucher entry is patched and `version` bumps | Reversal + fresh movement rows | Balance cache recomputed | New `invoiceaudits` version written |
| **Stock transfer** between warehouses | — | `TRANSFERSTOCK` movements moving quantity between `warehouse`s | — | — |
| **Manual stock adjustment** | — (unless it feeds valuation, which is **prototype-only**) | `MANUAL` / `BULKMANUAL` `UPDATE` movement with a `reason` | — | — |
| **Lead converted** to a quotation/invoice | — until the resulting document is finalised (then the invoice row above applies) | — | `leads.client` set (creating a `clients` record if none); lead stage → `CLOSED`/"Deal Done"; `leadPipelineHistory` stage entry closed; `salesActivities` row written | Quotation/proforma/invoice created and linked back on the lead |
| **Client created or its ledger mapping changes** | A party ledger is created in `saturn.ledgers` with `document_refers_to: client\|vendor\|clientVendor` and `document_reference_id` = the Mongo client id | — | `clients.ledgerId` set; any prior value pushed to `previousLedgers[]` | — |
| **Payment account created** | A corresponding Saturn ledger is created; `paymentAccounts.ledgerId` stores its uuid (gated by `syncAccounting.paymentAccounts`) | — | — | Becomes selectable as "paid into / paid from" on payment documents |
| **Bank statement uploaded & reconciled** | `bank_statements` → `bank_transactions` parsed, matched against `bank_books`; `reconciliations` rows resolve to `MATCHED`/`MISSING_IN_*`/`RECONCILED` | — | — | — |
| **Document enters an approval workflow** | — (posting still keyed off `status`, not workflow state) | — | `workflowitems` row created (`OPEN`), assignee set, reminders/escalations scheduled; `workflowitemactivites` logs each move | Stage `policies[]` can restrict edit/view/delete on the document while it sits in that stage |

## How to use

- Find the row for your trigger event (or add one if missing).
- For any non-"—" cell, open that module's `overview.md` / `schema.md` before changing behaviour.
- For any **Accounting** cell, check the three opt-in gates above first — the impact may simply not
  happen for a given business.
- Keep trigger events phrased as concrete, observable actions, and cite the enforcing repo
  (`serana` hook, `saturn` service) when you add accounting detail.
