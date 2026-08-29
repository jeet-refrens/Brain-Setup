# Decisions

Append-only log of decisions made during matchday runs and other planning sessions. A later reversal is a new entry that supersedes, never an edit to an existing one.

### D1 — isStockManaged hard-locked one direction from itemType (2026-07-31)

**Context:** Today isStockManaged is a fully independent boolean on every inventory item, settable regardless of itemType (Product/Service). This lets Services carry stock-managed behavior that shouldn't apply to them.

**Options:**
- Fully derive isStockManaged from itemType (Product=true, Service=false, neither editable)
- Asymmetric lock: Service always isStockManaged=false (locked); Product remains user-toggleable
- Leave as-is

**Decision:** Asymmetric lock. Service is hard-locked to isStockManaged=false. Product keeps free choice (true or false).

**Why & trade-off:** Fully deriving from itemType would force every Product into stock management, breaking legitimate non-stock-managed Products (digital licenses, made-to-order items) and likely pushing businesses back to mislabeling items as Service to escape it — recreating the exact ambiguity this initiative removes. Locking only the Service side is the minimal hard link that satisfies the original intent ("don't allow isStockManaged: true for services") without over-constraining Product.

**Refs:** [inventories.js](../../../talos/src/inventories.js) (isStockManaged field, line ~89)

---

### D2 — strictControl requires isStockManaged=true (2026-07-31)

**Context:** strictControl is independently settable today; businesses can turn it on even when isStockManaged is false, which is meaningless (nothing to block negative stock on).

**Decision:** strictControl can only be true when isStockManaged is true. If isStockManaged is false, strictControl is locked to false and not user-editable (hard block at API/schema level, not just a UI-side reset).

**Why & trade-off:** strictControl has no linked historical data (no child collection), so a hard lock has no data-loss risk — simpler and safer than a soft "reset on toggle-off" approach that would allow a transient invalid state.

**Refs:** [inventories.js](../../../talos/src/inventories.js) (strictControl field, line ~93)

---

### D3 — item/batch warehouses[] (materialized stock cache) gated on adoption by isStockManaged; existing data frozen, not cleared, on toggle-off (2026-07-31, corrected 2026-07-31)

**Context:** item.warehouses[] and batch.warehouses[] hold the *materialized/cached current stock* per warehouse, populated only by UPDATE-type inventorytransactions. Separately, inventorytransactions.warehouse already records which warehouse a transaction touched even for non-stock-managed items, tagged transactionType=IGNORE, purely for traceability — this already works correctly today and needs no change.

**Decision:** The gate applies only to *new* adoption, not retroactively:
1. **Gate (adoption):** an item that has never had isStockManaged=true cannot start populating warehouses[] — nothing to materialize while only IGNORE transactions can occur for it.
2. **No forced clearing on toggle-off:** if an item already has populated warehouses[] (built up while isStockManaged was true) and isStockManaged is later toggled to false, that existing data is **not** cleared — it's frozen in place (no further writes, since no more UPDATE transactions will target it), matching the general non-destructive freeze-not-strip principle.

So it is *not* universally true that non-stock-managed items have empty warehouses[] — only true for items that never had stock managed. The inventorytransactions log itself is untouched either way — it keeps recording IGNORE-type entries with a warehouse reference exactly as today.

**Why & trade-off:** Keeps the historical audit trail and existing per-warehouse balances fully intact while preventing a *brand-new* stock-cache array from being populated where it would always read as all-zeros and add no value, only confusion.

*(Corrected from an earlier draft of this entry that wrongly stated warehouses[] must always be empty for non-stock-managed items — that was true only as an adoption gate, not as a retroactive clearing rule.)*

**Refs:** [helpers/warehouseSchema.js](../../../talos/src/helpers/warehouseSchema.js), [inventorytransactions.js](../../../talos/src/inventorytransactions.js) (transactionType enum + comment, line ~73-83)

---

### D4 — trackingMethod gated on adoption by isStockManaged; already permanently immutable once non-NONE, independent of any record actually existing (2026-07-31, corrected 2026-07-31)

**Context:** trackingMethod (NONE/BATCH/SERIAL) is independently settable today regardless of isStockManaged. Separately — and this is existing, already-shipped product behavior, not a new rule invented here — once an item's trackingMethod is BATCH or SERIAL, it cannot be switched to another method (or back to NONE) on edit.

**Decision:** Two rules, orthogonal:
1. **Gate (adoption):** trackingMethod can only be set to BATCH or SERIAL while isStockManaged=true; forced to NONE otherwise (applies only to items still at NONE that have never adopted tracking).
2. **Immutability (existing behavior, kept as-is):** once trackingMethod is BATCH or SERIAL, it is already permanently locked on edit — the trigger is the field's *current value*, not whether any batch/serial record has actually been created under it, and it holds regardless of what isStockManaged does afterward.

**Why & trade-off:** The gate alone would suggest forcing trackingMethod back to NONE the moment isStockManaged goes false, but that would contradict this already-existing immutability behavior. We keep the existing immutability rule as-is and layer the isStockManaged gate only on top for items that haven't adopted tracking yet, rather than inventing a new "has linked records" condition.

**Corollary:** an item whose trackingMethod is currently BATCH/SERIAL can never have its itemType changed to Service (Service requires trackingMethod=NONE, which conflicts with the immutable non-NONE value). The engineering plan should surface a clear validation error for this case rather than allowing a silent conflict.

*(Corrected from an earlier draft of this entry that conditioned immutability on "a batch/serial record has ever been linked" — the actual existing behavior is simpler: immutability is keyed off the trackingMethod field value itself, not the presence of linked records.)*

**Refs:** [inventorybatches.js](../../../talos/src/inventorybatches.js), [inventoryserials.ts](../../../talos/src/inventoryserials.ts)

---

### D5 — Migration: misconfigured Service items are reclassified to Product, not stripped (2026-07-31)

**Context:** Existing Service items may already have isStockManaged=true, strictControl=true, trackingMethod!=NONE, and/or populated warehouses[] — all now invalid for Service under D1-D4.

**Options:**
- Auto-correct in place: force isStockManaged=false, strictControl=false, trackingMethod=NONE, clear warehouses[]
- Reclassify itemType to Product instead, preserving all existing behavior
- Grandfather silently, enforce only on future edits

**Decision:** Reclassify: change itemType to Product for any Service item whose existing configuration is only valid for Product under the new rules. Behavior is fully preserved; the business can manually switch it back to Service later if they genuinely don't want stock tracking.

**Why & trade-off:** Clearing the data (option 1) would be destructive and silently change real business behavior (stock stops being tracked on items that were actively being tracked). Reclassifying itemType was confirmed to have no tax/compliance side effect — HSN/SAC usage on invoices is not restricted or derived from itemType/hsn field configuration on the item, so this is a safe, behavior-preserving fix. Grandfathering (option 3) was rejected because it leaves the exact inconsistency this initiative exists to remove.

**Open item:** whether to notify affected businesses (banner/email) after migration is still TBD — being checked separately for feasibility.

**Refs:** [inventories.js](../../../talos/src/inventories.js) (itemType field, line ~27)

---

### D6 — Migration for Products with isStockManaged=false but stock-managed dependents set (2026-07-31)

**Context:** A Product can independently have isStockManaged=false while strictControl=true, trackingMethod set, and/or warehouses[] populated — inconsistent under D2-D4.

**Decision (per-field):**
- **strictControl:** force to false. No linked historical data at risk — pure behavior flag, safe to reset.
- **isStockManaged itself:** do NOT force to true. Promoting it would start actively maintaining stock/transactions for an item the business explicitly opted out of — a real behavioral change the business never asked for, unlike the Service→Product reclassification which is a label change only.
- **trackingMethod:** unaffected by this migration. Per D4 (corrected), trackingMethod's existing immutability is keyed off the field's current value, not batch/serial record existence — if it's already BATCH/SERIAL it simply stays as-is; no migration action needed here.
- **warehouses[]:** frozen, not cleared — per D3 (corrected), this is a standing rule (not migration-specific): existing data is never wiped, only new writes stop.

**Why & trade-off:** Consistent "non-destructive migration" philosophy — never force a new active behavior the business didn't request, and never destroy real linked/historical data, but do clear pure flags that carry no data risk.

---

### D7 — Warehouse data freeze-not-clear is a standing rule, not just a one-time migration step (2026-07-31)

**Context:** Originally raised only for the Product/isStockManaged=false migration case, but confirmed to apply generally — including to ordinary future user action (a business toggling isStockManaged off on an item), not only the one-time historical-data migration.

**Decision:** Whenever isStockManaged goes from true to false on an item — whether during the one-time migration or any time afterward via normal editing — existing warehouses[] stock data is never wiped/reset. Historical per-warehouse snapshots are frozen in place. Going forward, no new writes/updates occur to that array (no UPDATE transactions can target it), but nothing existing is deleted. This is the same rule as D3 (corrected); D3 is the canonical statement of it, this entry just confirms its scope is ongoing behavior, not migration-only.

**Why & trade-off:** Matches the existing, already-shipped behavior of the business-level inventoryOptions.manageWarehouses flag (see D8) — turning that off today already freezes rather than clears existing warehouse balances. This decision generalizes the same non-destructive principle to the itemType-driven case, and clarifies it's a permanent product rule, not a migration-only carve-out.

**Refs:** [businessConfigurations.ts](../../../talos/src/businessConfigurations.ts) (inventoryOptions.manageWarehouses, line ~642)

---

### D8 — Business-level inventoryOptions flags confirmed as non-destructive, transaction-time gates (2026-07-31)

**Context:** businessConfigurations.inventoryOptions carries its own manageWarehouses and strictInventoryControl booleans, separate from item-level isStockManaged/strictControl/warehouses[] — raised as a possible second layer of the same inconsistency problem.

**Decision:** No change needed — confirmed this already works correctly today for both flags:
- **strictInventoryControl:** business-level master switch. Item-level strictControl values are never mutated by toggling it; every transaction checks the business-level flag first before applying strict enforcement. Re-enabling the business flag restores previous item-level enforcement automatically (since the item value was never touched).
- **manageWarehouses:** for new items, warehouse-level configuration is simply hidden/unavailable when off. For existing items with prior warehouse-level data, turning manageWarehouses off does not clear that data — new transactions just stop targeting a warehouse (stock becomes "unassigned"), and turning the business flag back on resumes warehouse-level behavior using the preserved data.

**Why & trade-off:** This existing behavior is the pattern D7's grandfathering principle was generalized from — confirming it also validates that no retrofit is needed at the business-config layer for this initiative.

**Refs:** [businessConfigurations.ts](../../../talos/src/businessConfigurations.ts) (inventoryOptions block, line ~631-661)

---

### D9 — itemType becomes required; fallback chain for existing null values (2026-07-31)

**Context:** itemType is currently nullable with no default (`enum: Object.keys(itemType).concat([null])`), which is ambiguous under a model where the whole hard-link chain depends on knowing Product vs Service.

**Decision:** itemType becomes required going forward. Existing items with itemType=null are migrated using this fallback chain: `businessConfigurations.inventoryOptions.defaultItemType` → if unset, default to Product. trackingMethod always falls back to NONE regardless of this migration (no special-casing).

**Why & trade-off:** Falling back to the business's own configured default (rather than a hardcoded value) respects businesses that have already expressed a preference via defaultItemType; Product is the safe universal fallback since it's the more permissive bucket (allows, but doesn't require, stock management).

**Refs:** [inventories.js](../../../talos/src/inventories.js) (itemType field, line ~27-30), [businessConfigurations.ts](../../../talos/src/businessConfigurations.ts) (defaultItemType, line ~651)

---

### D10 — Scope: backend + frontend both included; packages/groups out of special-case scope (2026-07-31)

**Context:** Needed to bound the size of this initiative.

**Decision:**
- **Backend + frontend both in scope.** Backend/schema-level validation is the source of truth (covers all clients including API integrations); frontend is updated to hide/disable controls that are no longer valid for the current itemType/isStockManaged state, so users aren't shown options that will just get rejected.
- **Package/group items (isPackage) need no special new rules.** A package is just another inventories document with isPackage=true; the same itemType→isStockManaged→{strictControl,trackingMethod,warehouses} hard-link already applies independently to the package item and to each child item via their own fields. Confirmed this aligns with existing cascading behavior (parent's own flag governs parent-level stock, each child's own flag governs child-level stock) — no change needed here.
- **isSalesItem** was noted during exploration but not raised as related to this coupling — left untouched, out of scope.

**Refs:** [inventories.js](../../../talos/src/inventories.js) (isPackage/items/groups fields, line ~174-208; isSalesItem, line ~335)

---

### D11 — Package itemType carve-out: keep itemType=null for packages (2026-07-31)

**Context:** D9 makes itemType required, but scouting during /tactics-board found packages (isPackage=true) are hard-forced to itemType=null in three places today (serana before-manual-inventory-create.js:119-121, before-manual-inventory-patch.js:109-111, lydia InventoryForm.jsx:287). D9's blanket "no more null" collides with this directly.

**Options:**
- Keep itemType=null as a documented carve-out for packages (talos: `required: function () { return !this.isPackage; }`, null retained in enum; migration's null-itemType phase excludes isPackage:true docs)
- Force packages to itemType='product', delete the three `= null` assignments

**Decision:** Keep the carve-out (option 1) — "package item should work as is, if it doesn't break anything." The implementer must still verify during implementation that nothing else (list filters, defaults logic, cascades) depends on packages having a non-null itemType, but the decision itself is locked, not open.

**Why & trade-off:** Forcing packages to 'product' would change existing package behavior in ways D10 explicitly didn't scope ("packages need no special new rules"), and risks unaudited side effects in code that branches on `itemType == null` for packages. The carve-out is the smaller, safer change and doesn't conflict with D10's spirit — a package's own fields still independently follow the same hard-link rules; only the itemType label itself stays nullable for this one document type.

**Refs:** serana `before-manual-inventory-create.js:119-121`, `before-manual-inventory-patch.js:109-111`; lydia `InventoryForm.jsx:287`

---

### D12 — Create-time default when itemType and isStockManaged are both omitted: confirmed as a non-issue (2026-07-31)

**Context:** During /tactics-board, live production testing showed creating an item with neither itemType nor isStockManaged supplied results in itemType='product', isStockManaged=true. This appeared to contradict a static read of serana's create.js (which predicted itemType='service' when isStockManaged is falsy and unset).

**Finding:** Resolved by tracing, not by decision — lydia's client-side form schema (`src/schemas/inventory.js:39`) already defaults itemType to 'product' before the request is even sent, so the UI never actually omits it. That alone explains the observed result.

**Decision:** No behavior change required. Product + isStockManaged:true is already a valid state under D1 (rule 1), so the observed default isn't a violation. The only obligation is a regression test confirming the new centralized `resolveItemType` (D9's fallback chain) reproduces this same observed result and doesn't regress it.

**Refs:** lydia `src/schemas/inventory.js:39`; serana `before-manual-inventory-create.js:104-117`

---

### D13 — Service migration matrix, locked precisely (2026-07-31)

**Context:** D5/D6 established the general Service-reclassification and Product-cleanup migration philosophy, but didn't fully specify every combination reachable by a Service item independently. This entry is the exact, final matrix, confirmed during /tactics-board plan review.

**Decision:**
- Service + isStockManaged=true → reclassify to Product (unchanged from D5).
- Service + isStockManaged=false + strictControl=true as the **only** violation → clear strictControl to false, item **remains Service**. This must route through the migration's strictControl-reset phase, never the reclassify phase — a Service item whose only defect is strictControl must never be relabeled to Product.
- Service + isStockManaged=false + trackingMethod other than NONE → reclassify to Product. This is intentional: per D4's immutable non-NONE trackingMethod, such an item can never validly be a Service (D4's corollary), so Product is the only self-consistent label.
- Service + isStockManaged=false + trackingMethod=NONE → remains Service, with strictControl cleared if it was set.

**Why & trade-off:** Precisely bounds which Service documents get relabeled vs. just flag-cleaned, preventing the migration from over-reclassifying items whose only issue is a single cleanly-resettable flag.

---

### D14 — Enforcement-layer mechanics, transaction-path backdoor fix, and Elastic sync strategy are engineering decisions, not product decisions (2026-07-31)

**Context:** The engineering plan raised three implementation-level questions during /tactics-board: (a) whether cross-field validation lives in a shared hook-layer module vs. a Mongoose pre('validate') hook, (b) how to close the isStockManaged-promotion backdoor at serana's manage-inventory-stock.js:371 (a transaction-path write that bypasses item-CRUD validation), (c) how the migration keeps Elastic's mirrored index consistent with raw Mongo bulk writes.

**Decision:** Explicitly deferred to the engineering team during implementation ("Engineers will plan themselves. Don't include in plan.") — not a product/planning-stage decision, and not gated on human sign-off here. The underlying risks are still recorded as context in the engineering plan so no information is lost, but no specific technical approach is prescribed at this stage.

---

### D15 — Warehouse initial-stock table is create-only, confirmed as existing behavior (2026-07-31)

**Context:** Raised as an open UX question during /tactics-board (should editing an item with frozen warehouse data show it read-only, or stay hidden as today).

**Decision:** Confirmed via code (lydia `StockManagementDetailsForm.jsx:218-220` gates the warehouses FieldArray on `isWarehouseManaged && !inventoryId`; `src/schemas/inventory.js:270-271` gates the strict warehouses collection on `isWarehouseManaged && !isEdit`) — the warehouse initial-stock table is already create-only, full stop, regardless of trackingMethod or isStockManaged state. This is existing behavior to preserve as-is; no new read-only rendering variant is needed.

---

### D16 — D-3a: frozen warehouses[] alone does not trigger Service→Product reclassification (2026-07-31)

**Context:** The original task brief listed "populated warehouses[]" as one of the OR conditions for reclassifying a misconfigured Service to Product (alongside isStockManaged=true and trackingMethod!=NONE). D13's locked matrix, worked out independently, implies the opposite for the specific cohort of Service + isStockManaged=false + trackingMethod=NONE + non-empty warehouses[] (frozen historical per-warehouse stock) — that cohort should remain Service. The two sources conflicted for exactly this narrow case.

**Options:**
- Drop warehouses[] from the reclassify-trigger OR condition — such a Service item stays Service
- Keep warehouses[] in the trigger as originally briefed — such a Service item gets reclassified to Product

**Decision:** Drop it — the item stays Service. Frozen warehouse data on a non-stock-managed item is already legal under D3/D7 (the general grandfathering principle), so this state is not actually a rule violation under the final rule set. Reclassifying would relabel a customer's item for no structural gain.

**Why & trade-off:** The counter-argument (an item that once tracked per-warehouse stock might read more clearly to users as Product) is presentational, not structural, and was judged not to outweigh minimizing how many customer items get silently relabeled during migration.

**Refs:** serana migration command `standardizeinventoryitemcoupling.js`, phase P2 query
