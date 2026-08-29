# Inventory net price on transactions — Test Cases

Companion to the "Fix avg cost/selling price — store discount-adjusted price on inventory
transactions" Asana task. Every assertion here is grounded in a rule stated in the task
(Verified Current Behavior / The Change / Scope / Risk) — never in what "should" happen.

## Test groups

### Group A — net price computed correctly when a line discount is applied

**TC-A1 — Percentage discount, sale**
- Setup: stock-managed item; sales invoice line: quantity 10, rate ₹100, 10% percentage
  discount (line nets to ₹900).
- Action: finalize the invoice.
- Expected: the resulting SELL transaction has `netSellingPrice = 90`; `sellingPrice` remains
  `100` (unchanged existing gross value).

**TC-A2 — Fixed-amount discount, purchase**
- Setup: stock-managed item; purchase line: quantity 5, rate ₹200 (subtotal ₹1000), fixed-amount
  discount of ₹250 (line nets to ₹750).
- Action: finalize the purchase.
- Expected: the resulting BUY transaction has `netCostPrice = 150`; `costPrice` remains `200`.

### Group B — no discount on the line

**TC-B1 — Net price equals gross price**
- Setup: line item, quantity 8, rate ₹50, no discount applied.
- Action: finalize the document.
- Expected: `netSellingPrice`/`netCostPrice` (as applicable) equals `50` — identical to the gross
  price. No observable behavior change from before this task.

### Group C — line item split across multiple batches

**TC-C1 — Discount applies identically to every batch-split transaction**
- Setup: batch-tracked item; purchase line: quantity 10, rate ₹100, 10% discount (net unit price
  ₹90); allocated 6 units to Batch A and 4 units to Batch B.
- Action: finalize the purchase.
- Expected: two BUY transactions are created (quantity 6 and quantity 4); **both** carry
  `netCostPrice = 90` — the discount applies to the line, not to how its quantity happens to be
  split across batches.

### Group D — reversal / edit transactions

**TC-D1 — Quantity edited down after finalizing**
- Setup: an existing SELL transaction with `netSellingPrice = 90` for quantity 10 has already
  updated the item's `avgSellingPrice`.
- Action: the source invoice is edited to reduce the line's quantity to 8 (existing
  reversal-plus-fresh-row edit flow).
- Expected: the reversal transaction carries `netSellingPrice = 90` — the same value as the
  transaction it reverses; the new corrected transaction for quantity 8 computes and carries its
  own net price from the line's current state; `avgSellingPrice` unwinds to its pre-movement
  value before the corrected value is applied — never left holding a value derived from the
  gross price.

**TC-D2 — Invoice cancelled after finalizing**
- Setup: same starting state as TC-D1.
- Action: the invoice is cancelled entirely (full reversal, no replacement row).
- Expected: the reversal transaction carries `netSellingPrice = 90`; `avgSellingPrice` returns
  exactly to its value from before the original invoice was finalized.

### Group E — mixed old (no net price) and new transactions

**TC-E1 — Average blends pre-existing and new transactions without error**
- Setup: an item has one pre-existing transaction (created before this ships) with no
  `netSellingPrice` field, already reflected in the item's current `avgSellingPrice`.
- Action: a new sale with a line discount creates a fresh transaction with `netSellingPrice`
  populated.
- Expected: `avgSellingPrice` recomputes as a weighted blend using the pre-existing transaction's
  existing contribution unchanged, and the new transaction's net price (not its gross price) —
  no error, no `NaN`, no double-counting.

### Group F — manual and bulk-manual adjustments

**TC-F1 — Net price equals entered price**
- Setup: stock-managed item; manual stock addition of quantity 20 at entered cost ₹75.
- Action: submit the manual adjustment.
- Expected: the resulting transaction has `netCostPrice = 75`, equal to `costPrice = 75` — no
  discount concept applies since no document line exists.

### Group G — ensure the existing gross price behavior does NOT change

**TC-G1 — Gross fields and their consumers are unaffected**
- Setup: a sale with a line discount, as in TC-A1.
- Action: finalize the invoice, then read the transaction and item record back through any
  existing surface that reads the gross price fields.
- Expected: `costPrice`/`sellingPrice` values, and everything that already consumes them, behave
  identically to before this change — no observable difference.

### Group H — BLOCK-type transactions (reservations)

**TC-H1 — BLOCK transaction feeds the average from net price, same as UPDATE**
- Setup: stock-managed item; a sales order line reserves quantity 10 at rate ₹100 with a 10% line
  discount (net unit price ₹90), generating a `BLOCK` transaction.
- Action: confirm the sales order.
- Expected: the `BLOCK` transaction carries `netSellingPrice = 90` (mirroring TC-A1); the item's
  `avgSellingPrice` recomputes using ₹90 — `BLOCK` transactions already feed the average today,
  and this task doesn't change that, only the price they feed it with.

**TC-H2 — IGNORE / BLOCK_IGNORE still never affect the average**
- Setup: same discounted line as TC-H1, but on a non-stock-managed item (so the resulting
  transaction is `IGNORE`), and separately a previously-`BLOCK`ed transaction that becomes
  `BLOCK_IGNORE` (block released).
- Action: create/release each transaction.
- Expected: both transactions still compute and store `netCostPrice`/`netSellingPrice` (for
  consistency, mirroring how the existing gross price fields are already stored on every
  transaction row regardless of type) — but neither `avgCostPrice` nor `avgSellingPrice` changes
  as a result, exactly matching today's behavior for these two types.

## What mocks can't verify

The true blended-average behavior across a live business's actual historical transaction mix
(Group E) can only be fully exercised against production-shaped data — a real business with a
long, varied transaction history, not a clean two-transaction fixture. Cover Group E's mechanics
in the automated suite, but also spot-check `avgCostPrice`/`avgSellingPrice` on a sample of live
or staging businesses with heavy pre-existing transaction volume shortly after rollout, to confirm
the blend behaves sanely at real scale and doesn't drift unexpectedly.
