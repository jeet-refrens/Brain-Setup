# saturn

An advanced accounting / bookkeeping backend for Refrens. Implements double-entry accounting on PostgreSQL — ledgers, voucher entries, financial years, bank books, and bank-statement reconciliation — and keeps accounting in sync with payments.

**Tech:** Feathers v5 (Koa), TypeScript, PostgreSQL (Knex), Redis + BullMQ
**Tags:** backend, backend-core, full-stack

## What it contains

- `vouchers` service — core double-entry accounting documents (journal, payment, receipt vouchers) and ledger entries.
- `bank-books` service — bank and cash account management.
- Financial-year and FY-wise ledger services.
- `reconciliations` service — matching bank statements against recorded Refrens transactions.
- Accounting / payments sync — keeping the accounting ledger consistent with payment data.

## When to reach for it

- Changing accounting logic — vouchers, ledgers, double-entry balances, or bank/cash books.
- Working on financial years or FY-wise ledgers.
- Building or fixing bank-statement reconciliation flows.
- Adjusting accounting / payments sync.
