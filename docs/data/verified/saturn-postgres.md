# Verified fields — db 4 `Saturn` (Postgres)

The accounting service. Ordinary SQL. 33 tables, which is small enough to hold in
your head, unlike db 2.

Read the product side first:
[../../modules/accounting/overview.md](../../modules/accounting/overview.md).
Posting to the books is **opt-in per business per document type**, so Saturn does not
contain everything that exists in Mongo.

Last updated: **19 August 2026**.

## The one rule

**Filter on `business`.** On every business-scoped table the only indexed columns are
`id` and `business` (confirmed 19 Aug 2026 from Metabase index metadata). Filtering on
anything else scans the table.

`business` is a `varchar` holding the Mongo `businesses._id` as a 24-character hex
string. Confirmed by sampling `public.financial_years` on 19 Aug 2026.

## Tables

Business-scoped, all carrying `business`:

| Table | Columns | What it is |
|-------|---------|-----------|
| `public.vouchers` | 16 | The accounting entries |
| `public.voucher_entries` | 66 | Per-voucher detail. Wide, many columns are one per currency (`currency_wise_total.INR`, `.AED`, `.USD` and so on) |
| `public.lineitems` | 31 | Line-level detail, carries `voucher_id` and `financial_year_id` |
| `public.ledgers` | 21 | The chart of accounts |
| `public.accountgroups` | 14 | Ledger grouping |
| `public.financial_years` | 17 | Financial years per business. 62,250 rows on 19 Aug 2026 |
| `public.fy_wise_ledgers_data` | 28 | Year-scoped ledger balances |
| `public.fy_wise_vouchers_data` | 17 | Year-scoped voucher data |
| `public.bank_books` | 27 | Bank book |
| `public.bank_statements` | 83 | Imported statements. The widest table here |
| `public.bank_transactions` | 47 | Transactions |
| `public.reconciliations` | 18 | Reconciliation runs |
| `public.reconciliation_bank_books` | 12 | |
| `public.reconciliation_lineitems` | 12 | |

Not for product questions: `public.users` (3 columns, service accounts),
`knex_migrations`, `knex_migrations_lock`, everything under `columnar`, `partman` and
`cron`.

**Refused by the script:** `query_performance_logs` (108 columns of diagnostics),
`pg_stat_statements`, `pg_stat_statements_info`, `pg_buffercache`,
`cron.job_run_details`.

## Keys

- `id` — uuid, primary key, indexed on every table.
- `business` — varchar, indexed, the Mongo business id.
- `voucher_id` — uuid, on `lineitems` and `voucher_entries`. **Not indexed.** Reach it
  through `business` first.
- `financial_year_id` — uuid, on `lineitems`, `fy_wise_ledgers_data`,
  `fy_wise_vouchers_data`. **Not indexed.**
- `financial_year` — uuid on `voucher_entries`. Note the different name for what looks
  like the same thing. **Not yet checked** whether they mean the same thing.

## Multi-currency

`voucher_entries` carries a separate total column per currency, at least: AED, AUD,
BDT, BHD, BND, CAD, EUR, GBP, GHS, HKD, IDR, INR, KES, KWD, LKR, LYD, MVR, MYR, NGN,
NPR and more. A total that only reads `currency_wise_total.INR` silently drops the
roughly 40% of users outside India.

## About Citus

The Citus and pg_partman extensions are installed, but `public.citus_tables` returned
**zero rows** on 19 Aug 2026, so no table is distributed today. Treat these as plain
Postgres tables. Do not write a query that depends on shard pruning, and do not repeat
the claim that Saturn is sharded without rechecking.

## Not yet checked

The column meanings inside `vouchers`, `voucher_entries` and `ledgers`, the voucher
type values, and how a Mongo document id reaches its voucher. Confirm before use.
