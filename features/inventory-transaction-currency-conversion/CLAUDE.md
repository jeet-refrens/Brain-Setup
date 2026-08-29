# inventory-transaction-currency-conversion — working context

## What this is about

An `inventorytransactions` row stores `costPrice` / `sellingPrice` in the **source document's
currency**. It does not store the conversion rate to the business currency, and it does not store
the business-currency value of that price. So any report that reads prices straight off
transactions mixes currencies and gives wrong numbers.

The item's `avgCostPrice` / `avgSellingPrice` are believed to be right, because the averaging
engine applies an FX factor at compute time (`priceFactor` in `calculateAveragePrice`) — but that
factor is never written to the row, so it cannot be reproduced or audited later.

## Modules touched

- **Primary: Inventory** — `inventorytransactions` schema; the averaging engine in
  `serana/src/hooks/manage-inventory-stock.js` (`calculateAveragePrice`, `adjustInventoryStock`,
  `updateWarehouseData`); item, per-warehouse and per-batch `avgCostPrice` / `avgSellingPrice`;
  every inventory report built on those.
- **Upstream: Workflow & Documents** — the document holds the currency and the rate. Inventory
  reads it. Document schema and behaviour do not change.
- **Reference only: Accounting** — already solves this exact problem for ledger lines
  (`amount`/`currency` plus `book_amount`/`book_currency` at a stored `forex_rate`). Use it as the
  naming and shape precedent. No posting change here.
- Not touched: CRM.

## Docs read for this kickoff (2026-08-17)

- [docs/modules/inventory/overview.md](../../docs/modules/inventory/overview.md) — core entities,
  append-only transaction log, valuation is prototype-only.
- [docs/modules/inventory/schema.md](../../docs/modules/inventory/schema.md) —
  `inventorytransactions` fields. ⚠️ **Its curated list is incomplete**: the row *does* carry a
  `currency` field. Corrected in [docs/code-findings.md](docs/code-findings.md) F1. What is missing
  is the rate, not the currency.
- [docs/modules/inventory/transactions.md](../../docs/modules/inventory/transactions.md) — the
  `type` (BUY/SELL) and `transactionType` (IGNORE/BLOCK/BLOCK_IGNORE/UPDATE) axes, the
  reversal-based edit model, and the "Valuation impact" note that `costPrice`/`sellingPrice` drive
  the averages.
- [docs/modules/workflow-documents/schema.md](../../docs/modules/workflow-documents/schema.md) —
  `invoices` holds every document type. **Gap: the curated field list does not name the currency or
  conversion-rate fields.** Get the exact names from `talos/src/invoices.js` before writing any
  requirement.
- [docs/modules/accounting/overview.md](../../docs/modules/accounting/overview.md) (lines 117-120)
  and [schema.md](../../docs/modules/accounting/schema.md) — the two-currency rule on every ledger
  leg, and the `REF_DEFAULT_Forex` ledger for FX differences.
- [docs/cross-module-links.md](../../docs/cross-module-links.md) — the rows for "Sales invoice
  finalised", "Purchase / expenditure recorded", "Document edited after posting" and "Document
  cancelled / deleted". All four already produce Inventory movements; this feature changes what is
  stored on them, not when they fire.
- [docs/glossary.md](../../docs/glossary.md) — see canonical terms below.
- [docs/repo-map.md](../../docs/repo-map.md) — `riften` is the real-time Forex rates API.

## Canonical terms to reuse (do not invent synonyms)

- **bookAmount / bookCurrency** (Accounting) — "the business-currency value of a line item,
  converted from `amount`/`currency` at `forex_rate`." This is the house pattern for
  "same number, in business currency."
- **forex_rate** (Accounting, `saturn.lineitems`) — the stored per-line conversion rate.
- **transactionType** — `IGNORE` · `BLOCK` · `BLOCK_IGNORE` · `UPDATE`. Only `UPDATE` and `BLOCK`
  feed the averages.
- **docType** — the source document type on a movement.
- There is **no** existing glossary term for a conversion rate on an inventory movement. Whatever
  name is chosen must be added to `docs/glossary.md`.

## Sibling feature — read it first

[features/inventory-net-price-on-transactions/](../inventory-net-price-on-transactions/) is the
same table, the same averaging engine, and the same "reports read the wrong price" problem, one
step earlier (gross vs. discount-adjusted price). Its `spec.md` and `docs/decisions.md` already
trace the code path end to end and are the fastest way in. Decisions worth knowing:

- **D2 — forward-only, no historical backfill.** Too many rows across too many businesses to
  replay safely. Precedent, not a rule — but a different answer here needs a reason.
- **D3 — mirror the existing field pair** (`netCostPrice` / `netSellingPrice`) rather than invent a
  new shape.
- **D7 — `UPDATE` and `BLOCK` both feed the averages** (gate at `manage-inventory-stock.js:702`);
  `IGNORE` / `BLOCK_IGNORE` never do. Price fields are written on every row regardless of type.
- Its `spec.md` records that `calculateAveragePrice`'s `priceFactor` **is** the FX conversion —
  the single most important existing finding for this feature.

The two features touch the same fields and the same builders. Check sequencing and conflicts before
either ships.

## Code entry points

**Superseded by [docs/code-findings.md](docs/code-findings.md)**, which was read from live source on
2026-08-17 and carries a `file:line` for every claim. Read that instead of this list. Two things it
settled that were open before:

- The **primary** (non-converted) document builder is `serana/src/helpers/onDocumentUpdate.js:483-505`.
  This also closes open question 6 in the sibling feature.
- Document currency and rate are `currency` + `conversionRates` on
  `talos/src/helpers/documentCommonFields.js:787-808`, not on `invoices.js` directly.

## Reminders

- Reference `.env` secrets (`GITHUB_PAT`, etc.) **by name only**. Never print or paste a value.
- `gh` is **not installed**. Read repo source via the GitHub REST API with `GITHUB_PAT`.
- ~40% of users are outside India (Saudi Arabia, UAE, Malaysia, USA, UK). Multi-currency is a
  mainstream case here, not an edge case.
- Inventory valuation (FIFO/LIFO, valuation runs) is a **prototype**, not live —
  `features/inventory-valuation/`.
