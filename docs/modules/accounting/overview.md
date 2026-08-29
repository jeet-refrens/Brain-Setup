# Accounting — Overview

> Grounded in the live `saturn` (PostgreSQL bookkeeping service), `talos` (Mongo schemas) and
> `fence` enums, read via the GitHub API, verified **2026-08-15**. See [schema.md](schema.md) for
> field-level detail and Source-of-truth pointers, and [reports.md](reports.md) for the report
> surface.

## Purpose

Turn the business documents and money movements a business already records into a real,
double-entry set of books — a chart of accounts, vouchers, ledger balances, and the statutory
reports (Trial Balance, Balance Sheet, P&L, Cash Flow, GST returns) built on top of them.

The defining architectural fact: **accounting is a separate service on a separate database.**
Documents, clients and payments live in MongoDB (`serana`/`talos`); the double-entry books live in
PostgreSQL (`saturn`). Nothing is posted automatically by being written to Mongo — a **sync layer**
pushes documents across, and it is **opt-in per document type per business**.

## The two ledgers — don't confuse them

Refrens has two things that both look like "a ledger". They are unrelated:

| | **Saturn books** | **Wallet transactions** |
|---|---|---|
| Where | PostgreSQL (`saturn`) | MongoDB (`transactions`, `wallets`) |
| What | Real double-entry bookkeeping: account groups → ledgers → voucher entries → line items | Money movement between wallets (`debit` wallet → `credit` wallet), settlement and payout tracking |
| Purpose | The business's books, statutory reports | Refrens-platform money flow (payments collected, fees, settlements, payouts) |
| Statuses | voucher entry `version`, `reversed` | `PENDING` → settled (`settledAt`, `bookedAt`) |

A `transactions` row links **into** the books via `paymentLedgerId` / `paymentVoucherEntryRefrence`
and carries its own `bookKeepingSyncStatus`. When someone says "ledger" in a product conversation,
check which one they mean.

## Core entities

**In `saturn` (PostgreSQL) — the books:**

- **`accountgroups`** — the chart-of-accounts groups (Sundry Debtors, Bank Accounts, Duties and
  Taxes, Sales Accounts, …). Each carries an `account_type` (asset/liability/income/expense/capital).
- **`ledgers`** — individual accounts inside a group. A ledger can point back at a Mongo entity via
  `document_refers_to` + `document_reference_id` (client, vendor, employee, SKU, bank account).
- **`vouchers`** — voucher *books* (Sales, Purchase, Payment, Receipt, Journal, Contra, …), not
  individual entries.
- **`voucher_entries`** — the actual posted entries. Holds `debits`/`credits` JSON, totals, currency,
  `voucher_date`, `narration`, and a `version` counter.
- **`lineitems`** — one row per Dr/Cr leg of a voucher entry, against one `ledger`, with `amount`
  (transaction currency) and `book_amount` (business currency, via `forex_rate`).
- **`financial_years`** — per-business FY windows; every entry and line item is stamped with one.
- **`fy_wise_ledgers_data`** / **`fy_wise_vouchers_data`** — per-FY rollups (opening balances,
  voucher numbering) that make balance reads cheap.
- **Bank reconciliation set** — `bank_statements`, `bank_transactions` (what the bank says),
  `bank_books` (what the books say), `reconciliations`, `reconciliation_bank_books`,
  `reconciliation_lineitems`.

**In `talos`/MongoDB — the feeders:**

- **`paymentrecords`** — payment receipts / payouts, settling one or many invoices.
- **`paymentAccounts`** — the "paid into / paid from" account a user picks; carries `ledgerId`
  (the Saturn ledger it maps to), optionally linked to a `bankaccounts` or `employeeaccounts` row.
- **`bankAccounts`** — bank account master (account no, IFSC/IBAN/SWIFT, verification state).
- **`transactions`** + **`wallets`** — the wallet money-movement layer described above.
- **`clients`** — also carries `ledgerId` and `previousLedgers[]`, linking a client/vendor to its
  Saturn party ledger (see [../crm/overview.md](../crm/overview.md)).
- **GST/compliance:** `gstReturns`, `gstFilings`, `gstr2bEntries`, `gstrVendors`, `hsnCodes`.

## Key user flows

1. **Enable accounting sync.** `businessConfigurations.syncAccounting` is switched on per document
   type (`invoice`, `creditNote`, `debitNote`, `expenditure`, `invoicePayment`,
   `expenditurePayment`, `debitNotePayment`, `paymentReceipt`), plus `client` and `paymentAccounts`
   for ledger backfill. Each is a `SyncDocument` block with its own
   `status` (`NONE` → `REQUESTED` → `SCHEDULED` → `DONE` / `FAILED`) and progress counters.
2. **Bootstrap the chart of accounts.** The `accounting-setup` service plus
   `ensure-system-accounts` create default account groups and ~75 default ledgers from the `fence`
   templates, keyed by stable `default_key`s (`REF_DEFAULT_*`).
3. **Post a document.** Saving a non-draft invoice/expenditure/credit note/debit note fires
   `sync-document-with-voucher-entries` in `serana`, which calls the
   `sync-accounting` service to create (or patch) a voucher entry in Saturn.
4. **Record a payment.** Payment records sync through `sync-payments`, hitting the payment/receipt
   voucher books and settling the party ledger.
5. **Reconcile the bank.** Upload a statement (PDF/Excel/CSV) → parse into `bank_transactions` →
   match against `bank_books` → resolve each row to a reconciliation status.
6. **Read reports.** Trial Balance, Balance Sheet, Income & Expense, P&L, Day Book, Cash Flow,
   All-Ledgers — see [reports.md](reports.md).
7. **File GST** (India). GSTR-1 preparation, GSTR-2B fetch + reconciliation, GSTR-3B, filing
   status tracking.

## Status lifecycles

- **Sync status** (`businessConfigurations.syncAccounting.<docType>.status`):
  `NONE` → `REQUESTED` → `SCHEDULED` → `DONE`, or `FAILED`.
- **Voucher entry**: created at `version` 1; corrections bump `version` and link back via
  `original_voucher_entry`. Reversal sets `reversed` + `reversal_entry` rather than deleting.
- **Bank statement** (`bankStatementStatus`): `UPLOADED` → `PROCESSING` → `REVIEW_PENDING` →
  `ADDING_ALL_BANK_BOOK` → `ADDED_TO_BANK_BOOK` → `RECONCILIATION_IN_PROGRESS` →
  `RECONCILIATION_COMPLETED`; failure branches `FAILED`, `ADDING_ALL_BANK_BOOK_FAILED`,
  `RECONCILIATION_FAILED`, `REJECTED`.
- **Reconciliation** (`reconciliationStatus`): `MATCHED` · `MISSING_IN_LEDGER` ·
  `MISSING_IN_BANK_BOOK` · `DISCARDED` · `MARKED_FOR_LATER` · `RECONCILED`.

## Known edge cases

- **Drafts never post.** `sync-document-with-voucher-entries` returns early when
  `status === 'DRAFT'`. A `DRAFT → UNPAID` finalize is detected specially (`isDraftFinalized`),
  because status is often computed server-side and absent from the patch payload.
- **Sync is opt-in and per-document-type.** A business can have invoices syncing and expenditures
  not. Never assume a posted document implies books exist.
- **`syncBreak` halts syncing for a document.** Once broken, the document stops syncing until
  explicitly repaired. Break reasons (`syncBreakReasons`): `REVERSAL_VOUCHER_ENTRY_CREATED`,
  `REVERSAL_PAYMENT_VOUCHER_ENTRY_CREATED`, `DOCUMENT_CANCELED`, `DOCUMENT_SOFT_DELETED`,
  `DOCUMENT_HARD_DELETED`.
- **Edits only resync when accounting-relevant fields change.** The hook diffs a fixed field list
  and, for line items, compares only `name`, `amount`, `subTotal`, `total`, `discount`, `igst`,
  `cgst`, `sgst`, `gstRate`, `itc`, `ledgerId`, `custom` — UI-only fields (images, SKU, thumbnails)
  are deliberately ignored to avoid false-positive resyncs.
- **Amounts are integers.** Saturn stores money as `bigInteger`/`integer` minor units, not floats.
  Every read needs the currency's precision applied.
- **Two currencies on every leg.** `amount`/`currency` is the transaction currency; `book_amount`/
  `book_currency` is the business's book currency, converted at the line item's `forex_rate`. FX
  differences post to a dedicated Forex ledger (`REF_DEFAULT_Forex`).
- **Back-dated entries and voucher-entry editing are separately gated** by
  `syncAccounting.allowBackDateEntries` and `allowVoucherEntryEdit`.
- **Nothing is hard-deleted.** Every Saturn table carries `is_hard_removed` + `hard_removed_at`;
  reversal, not deletion, is the correction mechanism (same philosophy as
  `inventorytransactions` — see [../inventory/transactions.md](../inventory/transactions.md)).
- **Inventory valuation / COGS is NOT live.** There is a `costOfGoodsSold` account group and a
  `REF_DEFAULT_Cost_Of_Goods_Sold` ledger key in `fence`, but system-computed COGS and inventory
  asset valuation are a **prototype** — see
  [../../../features/inventory-valuation/PRD.md](../../../features/inventory-valuation/PRD.md).
