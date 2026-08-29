# Inventory: net (discount-adjusted) price on transactions

## Problem

When a document (invoice, purchase order, expenditure, credit/debit note, etc.) with a
**line-item discount** creates an `inventorytransactions` row, the row's `costPrice`/`sellingPrice`
is set from the line's gross `rate` — the discount is dropped entirely. `avgCostPrice` /
`avgSellingPrice` on the item (and mirrored per-warehouse and per-batch) are computed as a
quantity-weighted moving average of these gross prices, so any business that applies line
discounts ends up with:

- `avgCostPrice` / `avgSellingPrice` systematically overstated (buy side) / overstated (sell side)
  relative to what was actually paid/received.
- No field anywhere on `inventorytransactions` recording the price the item actually transacted
  at — only the pre-discount rate.
- Every downstream inventory report (profitability, valuation-adjacent figures, item-level
  reporting) inherits the error, with no way to reconstruct the true figure after the fact
  because discount data lives only on the document, not on the transaction.

## Scope

### In scope (Phase 1)

- Add a **net, discount-adjusted, pre-tax unit price** to `inventorytransactions`, computed from
  the source line item (`lineItem.amount / lineItem.quantity`).
- Switch the averaging engine (`avgCostPrice` / `avgSellingPrice` at item, warehouse, and batch
  level) to compute from this net price instead of gross `costPrice`/`sellingPrice`.
- Cover every transaction-creation path that currently sets `costPrice`/`sellingPrice` from a
  line item: the primary document flow (invoice/PO/expenditure/etc.) and the linked/converted
  document flow.
- Cover reversal/edit transactions (net price must reverse the same way gross does today) so the
  weighted average unwinds correctly.
- Manual/bulk-manual adjustments: no document line exists, so net price = gross price (no discount
  concept applies).
- Backfill historical transactions where the source line item is still resolvable, and recompute
  stored averages from the corrected data.
- Keep the existing gross `costPrice`/`sellingPrice` fields as-is (unchanged meaning) — this is
  additive, not a replacement.

### Out of scope (Phase 1) — flagged as Phase 2 / open questions below

- Document-level `discount` and `additionalCharges` (apportioned across line items) — only
  **line-item** discount is in scope for Phase 1.
- Any change to full inventory valuation (FIFO/LIFO layers, valuation runs) — that's a separate,
  currently-prototype initiative (`features/inventory-valuation/`).
- Any change to accounting postings — this is a stock-valuation correction only, not a
  ledger/tax change.
- Any change to the document/invoice schema or discount UX itself.

## Affected modules & entities

**Inventory** (primary):
- `inventorytransactions` — new field(s) for net price (see Open Questions on naming/shape).
  Existing fields involved: `costPrice`, `sellingPrice`, `type` (BUY/SELL), `lineItem` (already a
  ref back to the source document line — usable to resolve discount during backfill),
  `transactionType` (only `UPDATE` rows move stock/feed averages), `isReversed`/`reversedTransaction`.
- `inventories` — `avgCostPrice`, `avgSellingPrice` (computation source changes, no schema change).
- `warehouses[]` cache on `inventories` — same two fields, per-warehouse.
- `batches` — `avgCostPrice`, `avgSellingPrice` mirrored at batch level; same fix needed there.

**Workflow & Documents** (read-only dependency, not modified):
- Line item shape (`invoiceItems` helper on `invoices`): `rate` (gross unit price), `discount
  {discountType, amount}`, `subTotal` (gross), `amount` (net, pre-tax) — `amount / quantity` is
  the per-unit net price this feature needs. Confirmed relationship:
  `amount = subTotal − discount.amount` and `rate = subTotal / quantity`.

## Cross-module impacts

From `docs/cross-module-links.md`, the two trigger rows this feature affects:

| Trigger Event | Existing Inventory Impact | What changes here |
|---|---|---|
| Sales invoice finalised (DRAFT→UNPAID) | Stock-out `UPDATE` movements for stock-managed line items | The `sellingPrice`-derived average now also gets fed a net (discount-adjusted) price |
| Purchase / expenditure recorded | Stock-in `UPDATE` movements; avg cost updated | The `costPrice`-derived average now also gets fed a net (discount-adjusted) price |

No Accounting or CRM cells in that table are affected — this is purely a correction to what the
Inventory-column impact is *based on*, not a new cross-module effect. Credit note / delivery
challan / sales order flows that also touch `inventorytransactions` should be checked during
implementation for the same gross-vs-net gap, even though they're not called out with a discount
example in the links table.

## Mechanism (grounded in code, session of 2026-08-08)

Traced end-to-end against live `refrens/talos` and `refrens/serana` source via the GitHub API:

1. **Line item math** (`talos/src/helpers/invoiceItems.js`, confirmed by
   `serana/src/helpers/getInvoiceItem.js:80-82`):
   ```
   item.amount   = total / (1 + gstRate)       // net-of-tax, post-discount
   item.subTotal = amount + discount.amount    // gross-of-discount, net-of-tax
   item.rate     = subTotal / quantity         // gross per-unit rate
   ```
   So `item.amount / item.quantity` is the actual net per-unit price — it already exists, just
   never reaches Inventory.

2. **Transaction creation** (`serana/src/hooks/manage-linked-document-inventory-transaction.js:25-26`):
   ```js
   sellingPrice: !isPurchaseDoc ? sourceItem.rate : 0,
   costPrice:    isPurchaseDoc  ? sourceItem.rate : 0,
   ```
   Only the gross `rate` is copied onto the transaction. This is the linked/converted-document
   builder; the equivalent assignment in the **primary** (non-converted) document flow exists
   somewhere in `serana` but wasn't pinned down by this session's code search — **first
   implementation task**.

3. **Averaging** (`serana/src/hooks/manage-inventory-stock.js`):
   - `calculateAveragePrice({currentPrice, currentQuantity, price, quantity, priceFactor,
     isReverse})` — a quantity-weighted moving average; `priceFactor` is FX-conversion only
     (business-currency exchange rate), not discount-related.
   - Called by `adjustInventoryStock()` (item-level `avgCostPrice`/`avgSellingPrice`) and
     `updateWarehouseData()` (per-warehouse `avgCostPrice`/`avgSellingPrice`), both reading
     `costPrice`/`sellingPrice` straight off the transaction (`executeInventoryUpdate`, lines
     ~544-545).
   - The `isReverse` branch subtracts the same `price × quantity × priceFactor` term used on
     the way in — whatever price field we switch to must be present and correct on reversal rows
     too, or reversals will unwind the average incorrectly.
   - Batch-level averages go through an equivalent path in `inventory-batches.hooks.js` /
     `createTransactionOnBatchCreation.js` (not yet read line-by-line — verify during
     implementation that it mirrors the same pattern).

4. Reports and integrity tooling that read these averages (not yet enumerated exhaustively):
   `serana/src/services/inventory-reports/class.js`, `expenditures-reports`, `invoice-reports`,
   and the drift-correction cron `serana/src/commands/crons/integrity/inventorystockintegrity.js`
   (this is also the natural home for the recompute step of the backfill).

## Open questions

1. **Net of what, exactly?** Net of **line-item discount only** (recommended for Phase 1), or
   should document-level discount / additional-charges apportionment also fold in from the start?
   Recommendation: line-discount-only first — document-level apportionment is materially more
   complex (needs a per-line allocation rule) and can follow as Phase 2 once the simpler case is
   validated in production.

2. **Backfill strategy.** Full historical backfill (resolve each transaction's source line via
   `lineItem`/`docId`, recompute net price, then replay to recompute stored averages at item/
   warehouse/batch level) vs. forward-only (new field only populated going forward, old averages
   stay as-is until naturally diluted by new transactions). Recommendation: full backfill —
   otherwise every existing report stays wrong indefinitely for slow-moving items, and the whole
   point of the feature is report correctness.

3. **Field shape.** Two new fields mirroring the existing pair — `netCostPrice` / `netSellingPrice`
   — vs. a single `netRate` (direction implied by `type: BUY/SELL`, same pattern the existing
   `costPrice`/`sellingPrice` pair already avoids). Recommendation: mirror the existing pair
   (`netCostPrice`/`netSellingPrice`) for consistency with `costPrice`/`sellingPrice` and to keep
   the BUY/SELL-conditional-zero pattern intact.

4. **Audit trail.** Should the transaction snapshot the `discount {discountType, amount}` that
   was applied (e.g. into the existing `params` Mixed field), so the net price is explainable
   later without re-joining to the (mutable-via-versioning) source document? Recommendation: yes,
   low cost, high value for support/debugging.

5. **Naming in the glossary.** No existing term for "discount-adjusted per-unit price" — once the
   field name is locked in (`netCostPrice`/`netSellingPrice` or otherwise), add it to
   `docs/glossary.md` so it doesn't get reinvented elsewhere.

6. **Primary (non-linked) transaction builder location.** Needs to be found in `serana` before
   implementation can start on that path — the linked-document builder was located this session,
   its non-converted-document counterpart was not.

7. **Batch-level path parity.** Confirm `inventory-batches.hooks.js` /
   `createTransactionOnBatchCreation.js` follow the same `costPrice`/`sellingPrice` →
   `calculateAveragePrice` pattern as the item/warehouse path, or whether batch averages are
   computed differently and need a distinct fix.

8. **Report semantics.** For each report currently surfacing `avgCostPrice`/`avgSellingPrice` (or
   raw `costPrice`/`sellingPrice`) — should it display net, gross, or both? Needs a report-by-report
   decision once the report inventory is enumerated (see Mechanism §4).
