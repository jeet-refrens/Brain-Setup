# Accounting — Reports

> Grounded in `saturn/src/services/reports/` (`reports.class.ts`, `reports.query.ts`, `types.ts`)
> and the `serana` report services, verified **2026-08-15**.

Reports split into two families with different owners:

1. **Books reports** — served by `saturn`'s `reports` service off `lineitems` / `fy_wise_ledgers_data`.
2. **Document & compliance reports** — served by `serana` off Mongo documents (`invoices`,
   `paymentrecords`, `clients`) and the GST services.

## Books reports (`saturn`)

Single Feathers service, `find` + `get` only. `find` returns the headline list
(`trialbalance`, `balancesheet`, `incomeexpense`); `get(<id>)` runs a specific report.

| Report id | What it is | Required query params |
|---|---|---|
| `trialbalance` | Trial Balance — every ledger's Dr/Cr closing position | `start_date`, `end_date`, `fy_id`, `currency` |
| `balancesheet` | Balance Sheet, nested account type → group type → group → ledger | `fy_id`, `currency` |
| `incomeexpense` | Income & Expense statement | `fy_id`, `currency` |
| `pl` | Profit & Loss across **multiple comparison periods** | `periods[]` (each `{start_date, end_date, period_order}`), `currency` |
| `daybook` | Chronological listing of entries for a date | `start_date`, `currency` |
| `cashflow` | Cash Flow | `start_date`, `end_date`, `fy_id`, `currency` |
| `all-ledgers` | Paginated ledger listing with balances | `start_date`, `end_date`, `fy_id`, `currency` |

Common query options:

- `currency` is **always required** (no implicit default at the service boundary; `all-ledgers`
  falls back to `INR` internally).
- `skipZeroEntries=true` hides zero-balance rows.
- `all-ledgers` also accepts `$limit`/`$skip`, `type_ids`, `category_ids`, `account_group_id`,
  and `namesOnly=true` (id+name only, for pickers).
- Date validation: end date must be ≥ start date; `pl` requires `periods` to be an array and every
  period to carry `period_order`.

**Shape.** Balance-sheet-family reports return nested `subRows` (account type → account group type →
account group → ledger), each row carrying `balance`, `type`, optional `percent`. P&L rows carry
`{name, amount, currency, crdr}` plus the grouping key. See `saturn/src/services/reports/types.ts`.

**Performance note.** Balances come from the per-FY rollups (`fy_wise_ledgers_data`) rather than
summing all `lineitems`; several 2025 migrations exist purely to index `lineitems`, `vouchers`,
`ledgers` and the FY tables. A report that suddenly scans `lineitems` directly is a red flag.

## Document & receivables reports (`serana`)

| Service | What it answers |
|---|---|
| `client-ledger` | Per-client statement of account (shareable via a signed token / `shareId`; rendered to PDF through `dibella`) |
| `client-outstanding-report` | What each client currently owes |
| `client-ageing-report` | Receivables bucketed by age |
| `ledger-statement` | Statement for a single Saturn ledger |
| `invoice-reports`, `paymentreceipt-reports`, `paymentrecords-reports`, `expenditures-reports` | Document-level aggregations |
| `lead-reports` | CRM funnel reporting — see [../crm/overview.md](../crm/overview.md) |

`clients.balance` on the Mongo client doc caches per-document-type totals (`invoice`, `proforma`,
`creditNote`, `paymentReceipt`, `debitNote`, `salesOrder`, `invoicePayment`, `proformaPayment`,
`expenditure`, `expenditurePayment`, `creditConsumed`) in one `currency` — useful for list views,
but it is a **cache**, not the authoritative books balance. For real balances, read Saturn.

## GST / compliance reports (India)

| Service | What it does |
|---|---|
| `gst-reports` | GSTR-1 preparation. Table structure in `fence/gstReports/gstr1Tables.json`: `4A`, `4B`, `4C`, `5A`, `5B`, `6A`, `6B`, `6C`, `7A`, `7B`, `8A`–`8D`, `9B`; each has a `label` and a `userSelectable` flag |
| `gstr2b-reports`, `gstr2b-reconciliation`, `gstr2b-entries` | Pull inbound GSTR-2B, reconcile against recorded purchases for ITC |
| `gstr3b-reports` | GSTR-3B summary |
| `gst-returns`, `gst-return-downloads`, `gst-filings` | Filed-return artifacts and filing-history/compliance-score tracking |
| `gst-validations`, `gstn-sessions` | GSTIN validation and portal session handling |
| `gstr-vendors` | Vendor-side GSTIN tracking |

**International note.** These are India-only. ~40% of the user base is outside India and files VAT /
SST / PPN / HST instead — there is no equivalent return-filing service for those jurisdictions, only
the tax **ledgers** (see [schema.md](schema.md) § Default chart of accounts). Check this before
assuming a compliance flow generalises.

## Source of truth

- **`refrens/saturn`** — `src/services/reports/reports.class.ts` (report dispatch, ~line 757
  onward), `reports.query.ts` (SQL), `types.ts` (response shapes);
  `src/helpers/compute-ledger-balance.ts`.
- **`refrens/serana`** — `src/services/client-ledger/`, `client-outstanding-report/`,
  `client-ageing-report/`, `ledger-statement/`, `invoice-reports/`, `gst-reports/`,
  `gstr2b-reconciliation/`, `gstr3b-reports/`.
- **`refrens/fence`** — `gstReports/gstr1Tables.json`,
  `accounting/voucher-entry-ledger-filters.json`, `accounting/voucherEntriesCsvHeaders.json`,
  `accounting/ledgersCsvHeaders.json`.
