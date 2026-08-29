# inventory-net-price-on-transactions — Decision Log

### D1 — Phase 1 scope: line-item discount only (2026-08-08)

**Context:** `inventorytransactions.costPrice`/`sellingPrice` are set from the line item's gross
`rate`, ignoring both line-item `discount{discountType,amount}` and document-level `discount`/
`additionalCharges`. Fixing all of it at once requires an apportionment rule for document-level
amounts across lines.

**Options:** (a) line-item discount only, (b) line-item + document-level discount/charges together.

**Decision:** (a). Document-level discount/additional-charges apportionment is not in this
feature at all — not even flagged as a deferred phase.

**Why & trade-off:** Line-item discount is mechanically unambiguous — the net figure
(`lineItem.amount`) already exists per line. Document-level apportionment is a separate design
problem (needs a per-line allocation rule) that would block shipping the clear, uncontroversial
fix.

**Refs:** spec.md "Mechanism" §1; talos/src/helpers/invoiceItems.js.

---

### D2 — No historical backfill; forward-only (2026-08-08)

**Context:** Existing `inventorytransactions` rows and existing `avgCostPrice`/`avgSellingPrice`
values are wrong (gross, not net) for any business that used line discounts. A full backfill
would resolve every existing item/warehouse/batch average by replaying corrected transactions.

**Options:** (a) full historical backfill + recompute, (b) forward-only — new field populated
only on transactions created after ship, old data left as-is.

**Decision:** (b) forward-only.

**Why & trade-off:** Too many existing inventory transactions across too many businesses to
safely and cheaply replay. Existing averages stay wrong until diluted by new (correct) activity
— slow-movers may carry a stale average for a long time. Accepted trade-off given the backfill's
operational cost/risk at current data volume.

**Refs:** spec.md Open Question 2.

---

### D3 — Field shape: `netCostPrice`/`netSellingPrice`, no audit snapshot (2026-08-08)

**Context:** Needed a schema shape for the new net price on `inventorytransactions`, and whether
to snapshot the applied discount for later explainability.

**Options:** (a) `netCostPrice`/`netSellingPrice` pair mirroring `costPrice`/`sellingPrice`, or a
single `netRate`; snapshot `discount{discountType,amount}` into `params` or not.

**Decision:** `netCostPrice` + `netSellingPrice` (mirrors the existing pair). No discount
snapshot into `params` — not required for audit right now.

**Refs:** talos/src/inventorytransactions.js.

---

### D4 — Report display: engineering judgment, not specified here (2026-08-08)

**Context:** Reports currently surfacing `avgCostPrice`/`avgSellingPrice` or raw
`costPrice`/`sellingPrice` could switch to net, stay gross, or show both.

**Decision:** Left to engineering judgment. Not specified as a requirement in this task.

**Refs:** spec.md Open Question 8. See also D6 — reports are a separate task entirely.

---

### D5 — Multi-batch line items: net price applied uniformly per line (2026-08-08, code-verified)

**Context:** A document line item's quantity can be split across multiple batches via
`item.allocations[]`, producing multiple `inventorytransactions` rows from one line.

**Verified in code:** `serana/src/hooks/manage-linked-document-inventory-transaction.js` —
`createTransactionPayload({inventory, sourceItem, quantity, ...})` is invoked once per
allocation/batch (varying `quantity` and `batch`), but always with the **same `sourceItem`**, so
every batch-split transaction from one line already receives the identical `sourceItem.rate`
today.

**Decision:** Net price is computed once per line item (`sourceItem.amount / sourceItem.quantity`)
and applied identically to every `inventorytransactions` row that line generates — mirroring
exactly how gross `rate` is applied today. No new per-batch logic.

**Refs:** manage-linked-document-inventory-transaction.js:5-43, 335-380 (allocation loop calling
`createTransactionPayload` per batch).

---

### D6 — Report corrections are a separate task (2026-08-08)

**Context:** Once `netCostPrice`/`netSellingPrice` exist and averages are computed from them
going forward, existing reports that surface `avgCostPrice`/`avgSellingPrice` or raw
`costPrice`/`sellingPrice` are unaffected by this task's code — they keep reading whatever they
read today.

**Decision:** Updating reports to prefer/display net price is explicitly out of scope for this
task. Sequenced as a separate follow-up task, not even referenced as a next phase here.

---

### D7 — BLOCK transactions are in scope; mirror today's mechanism exactly (2026-08-08, code-verified)

**Context:** Asked whether `avgCostPrice`/`avgSellingPrice` recompute on every transaction or only
`UPDATE`. Verified in `serana/src/hooks/manage-inventory-stock.js`: the gate at
`executeInventoryUpdate` line 702 is `if (['BLOCK', 'UPDATE'].includes(transactionFlag))` —
both `UPDATE` and `BLOCK` transactions feed the average today. `IGNORE`/`BLOCK_IGNORE` never do.
Inside `adjustInventoryStock()` (line 265-343), the average computation itself is unconditional
once the function is called — only the on-hand `stock`/`stockInHand` fields are further gated to
`UPDATE`. So average-price gating and stock-quantity gating are two different, already-decoupled
rules in the existing code.

**Decision:** Net price must feed the average for exactly the same transaction types that already
feed it today — `UPDATE` and `BLOCK`, not `UPDATE` alone. `IGNORE`/`BLOCK_IGNORE` continue to
never affect either average. No change to this gating logic; the fix only swaps which price
(gross → net) the already-averaged types contribute. The net price field itself is still computed
and stored on every transaction row with a source line item regardless of type — mirroring how
the existing gross `costPrice`/`sellingPrice` fields are already populated today, unconditional on
`transactionType` — but only `UPDATE`/`BLOCK` rows feed it into the average.

**Why & trade-off:** "Keep the mechanism the same as today" — this is a price-source correction,
not a change to which transactions are considered stock-affecting or average-affecting. Extending
net-price coverage to `BLOCK` (e.g. sales-order/quotation reservations) closes the same gap for
reserved-stock pricing that Phase 1 already closes for confirmed sales/purchases, using the
existing gating rule rather than inventing a new one.

**Refs:** serana/src/hooks/manage-inventory-stock.js:265-343 (`adjustInventoryStock`), :702
(`executeInventoryUpdate` gate).
