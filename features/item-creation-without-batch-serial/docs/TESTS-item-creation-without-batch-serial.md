# Item creation without mandatory batch / serial — Test Cases

Companion to the [Enhancement] *Allow item creation with tracking method only* Asana task.
Every check here comes from a rule in that task.

Unless a case says otherwise, the business has inventory management on, warehouse management
off, and a plan that includes batch/serial tracking.

---

## Group A — Batchwise item with no batches

### TC-A1 — Creates with zero batches
**Action:** Set **Item Type** to Product, pick **Tracking Method = Batchwise**, add no batches, save.
**Expected:** Item is created, no error. It has `trackingMethod = BATCH`, `stock = 0`, `stockInHand = 0`, no batches.

### TC-A2 — No opening stock input
**Action:** In the new item form, switch **Tracking Method** from **None** to **Batchwise**.
**Expected:** The **Opening Stock** input disappears. Anything typed there is dropped. The item is created with `initialStock = 0`.

### TC-A3 — Batches still work when given
**Action:** Pick **Batchwise**, add one batch with a code, a name, and quantity 25. Save.
**Expected:** Item is created with one batch and `stockInHand = 25`. Unchanged from today.

### TC-A4 — Duplicate batch codes still rejected
**Action:** Pick **Batchwise**, add two batches with the same batch code. Save.
**Expected:** Refused, with today's duplicate-batch-code error.

---

## Group B — Serial No. item, warehouse management OFF

### TC-B1 — Creates with zero serials
**Action:** Set **Item Type** to Product, pick **Tracking Method = Serial No.**, add no serials, save.
**Expected:** Item is created, no error. It has `trackingMethod = SERIAL`, `stock = 0`, `stockInHand = 0`, no serials.

### TC-B2 — Serials still work when given
**Action:** Pick **Serial No.**, enter three valid serials. Save.
**Expected:** Item is created with three serials at `AVAILABLE` and `stockInHand = 3`.

### TC-B3 — Bad serial format still rejected
**Action:** Pick **Serial No.**, enter one serial that breaks the format or length rule. Save.
**Expected:** Refused, with today's invalid-serial error naming that serial.

### TC-B4 — Duplicate serials still rejected
**Action:** Pick **Serial No.**, enter the same serial twice. Save.
**Expected:** Refused, with today's serial-uniqueness error.

---

## Group C — Serial No. item, warehouse management ON

### TC-C1 — Warehouse row with no serials
**Setup:** Warehouse management on, one warehouse.
**Action:** Pick **Serial No.**, choose the warehouse, leave its serial list empty. Save.
**Expected:** Item is created. The warehouse row stays at quantity 0, with no error.

### TC-C2 — Serials on one warehouse only
**Setup:** Warehouse management on, two warehouses.
**Action:** Add both rows. Enter two serials on the first, none on the second. Save.
**Expected:** Item is created. First warehouse: two serials, quantity 2. Second: zero.

### TC-C3 — Serials still unique across warehouses
**Setup:** As TC-C2.
**Action:** Enter the same serial on both warehouse rows. Save.
**Expected:** Refused, with today's cross-warehouse uniqueness error.

### TC-C4 — Batch item ignores warehouse rows
**Setup:** Warehouse management on.
**Action:** Pick **Batchwise** with no batches. Save.
**Expected:** Item is created with no warehouse rows. Unchanged from today.

---

## Group D — Guards that must survive

### TC-D1 — Plan gate still applies
**Setup:** Plan without batch/serial tracking, not on trial.
**Action:** In the new item form, pick **Batchwise**. Repeat with **Serial No.**
**Expected:** Upgrade prompt appears. Tracking method resets to **None**. Neither method can be used.

### TC-D2 — Server refuses when the form is bypassed
**Setup:** Plan without batch/serial tracking.
**Action:** Create an item with `trackingMethod = BATCH` and no batches through the API.
**Expected:** Refused, with today's feature-access error.

### TC-D3 — Non-product types still refused
**Action:** Create an item with **Item Type = Service** and `trackingMethod = SERIAL`, no serials.
**Expected:** Refused, with today's "only available for products" error.

### TC-D4 — Packages still refused
**Action:** Create a package item with `trackingMethod = BATCH` and no batches.
**Expected:** Refused, with today's "not available for packages" error. **Serial No.** also stays disabled for package child items.

### TC-D5 — Inventory management off still refused
**Setup:** Inventory management off.
**Action:** Create an item with `trackingMethod = BATCH`, no batches, through the API.
**Expected:** Refused, with today's "inventory management is required" error.

### TC-D6 — Warranty rules unaffected
**Action:** Create a **Serial No.** item with no serials and a warranty period of 0 months.
**Expected:** Refused, with today's warranty-duration error.

---

## Group E — Filling the item later

### TC-E1 — Add a batch from the item
**Setup:** Empty batch item from TC-A1.
**Action:** Open its batches view, add a batch of quantity 40.
**Expected:** Batch is created, `stockInHand = 40`, stock status recalculates against the item's thresholds.

### TC-E2 — Add serials from the item
**Setup:** Empty serial item from TC-B1.
**Action:** Open its serials view, add two serials.
**Expected:** Both serials are created at `AVAILABLE` and `stockInHand = 2`.

### TC-E3 — Add a batch through a purchase
**Setup:** Empty batch item from TC-A1. Purchases update stock.
**Action:** Raise a purchase for it, creating a batch inline for quantity 15.
**Expected:** Batch is created, `stockInHand = 15`, movement recorded against the purchase.

### TC-E4 — Add stock through an adjustment
**Setup:** Empty batch item from TC-A1.
**Action:** Adjust stock, adding a batch of quantity 10 with a reason.
**Expected:** `stockInHand = 10` and a manual movement is recorded with that reason.

### TC-E5 — Wrong tracking method still refused
**Setup:** Empty serial item from TC-B1.
**Action:** Try to add a *batch* to it.
**Expected:** Refused: "batches can only be edited if the tracking method is Batchwise". Serials on a batch item fail the same way.

---

## Group F — Documents, unchanged

### TC-F1 — Empty batch item on an invoice
**Setup:** Empty batch item from TC-A1. Invoices update stock.
**Action:** Add it to an invoice line. Open batch selection.
**Expected:** No batch is offered, but the user can create one inline. The invoice will not save without one.

### TC-F2 — Empty serial item on an invoice
**Setup:** Empty serial item from TC-B1. Invoices update stock.
**Action:** Add it to an invoice line. Open serial selection.
**Expected:** The empty state shows. Save is blocked until a serial is picked.

### TC-F3 — Batch optional where stock is ignored
**Setup:** Empty batch item from TC-A1. Quotations ignore stock, `batchOptionalFlag` default.
**Action:** Add it to a quotation. Save.
**Expected:** The quotation saves with no batch picked.

---

## Group G — What must not move

### TC-G1 — Tracking method stays permanent
**Setup:** Empty batch item from TC-A1.
**Action:** Edit the item, look at the **Tracking Method** control.
**Expected:** Disabled. It cannot go back to **None** or over to **Serial No.**, even at zero stock.

### TC-G2 — Editing an empty item needs no batch
**Setup:** Empty batch item from TC-A1.
**Action:** Change its name and selling price. Save.
**Expected:** Saves with no batch required. Matches today's edit behaviour.

### TC-G3 — Bulk upload unchanged
**Action:** Bulk-upload an item sheet with a `trackingMethod` column set to `BATCH`.
**Expected:** The column is ignored. Every uploaded item lands with tracking method **None**.

### TC-G4 — Switch-to-Batch guard still holds
**Setup:** Existing item, **None**, `stockInHand = 30`.
**Action:** Edit it to **Batchwise** with a first batch of quantity 10.
**Expected:** Refused: "first batch quantity must be at least equal to current stock in hand".

### TC-G5 — Batch + Serial stays off
**Action:** Look at the **Batch + Serial No.** option in the new item form.
**Expected:** Still disabled. This change does not turn it on.

### TC-G6 — Untracked items unchanged
**Setup:** Warehouse management on.
**Action:** Create an item with **Tracking Method = None** and no warehouse picked.
**Expected:** Refused, with today's "warehouse is required" error.

---

## Group H — Creating over the API

### TC-H1 — Batch item over the API
**Action:** POST an item with `trackingMethod = BATCH`, no `initialStock`, no warehouse `quantity`.
**Expected:** Created. It has `trackingMethod = BATCH`, `stock = 0`, `stockInHand = 0`, no batches.

### TC-H2 — Serial item over the API
**Action:** POST an item with `trackingMethod = SERIAL`, no `initialStock`, no warehouse `quantity`.
**Expected:** Created. It has `trackingMethod = SERIAL`, `stock = 0`, `stockInHand = 0`, no serials.

### TC-H3 — initialStock rejected
**Action:** POST an item with `trackingMethod = BATCH` and `initialStock = 50`.
**Expected:** Refused. The error names `initialStock` and says stock comes from batches or serials.

### TC-H4 — initialStock of 0 also rejected
**Action:** POST an item with `trackingMethod = BATCH` and `initialStock = 0`.
**Expected:** Refused, same error. The rule is on the field being sent, not its value.

### TC-H5 — Warehouse quantity rejected
**Setup:** Warehouse management on.
**Action:** POST an item with `trackingMethod = SERIAL` and one warehouse row carrying `quantity = 5`.
**Expected:** Refused. The error names `quantity`.

### TC-H6 — Warehouse thresholds still allowed
**Setup:** Warehouse management on.
**Action:** POST an item with `trackingMethod = SERIAL` and a warehouse row carrying only `reorderPoint` and `overstockPoint`.
**Expected:** Created, with those thresholds saved.

### TC-H7 — batches and serials still outside the contract
**Action:** POST an item with `trackingMethod = BATCH` and a `batches` array. Repeat with `serials`.
**Expected:** Refused both times, with today's unexpected-field error.

### TC-H8 — initialStock still fine for untracked items
**Action:** POST an item with `trackingMethod = NONE` and `initialStock = 50`.
**Expected:** Created with `stockInHand = 50`. The new rule applies only to tracked items.

### TC-H9 — Fill a batch item through the batches API
**Setup:** Empty batch item from TC-H1.
**Action:** POST a batch against it for quantity 20 through the batches API.
**Expected:** Batch is created and `stockInHand = 20`.

### TC-H10 — Tracking method still not patchable
**Setup:** Empty batch item from TC-H1.
**Action:** PATCH it with `trackingMethod = NONE`.
**Expected:** Refused: "trackingMethod cannot be updated via API".

---

## What mocks can't verify

- **Plan gate (TC-D1, TC-D2)** reads live entitlement. Check on a real business without batch/serial tracking, then on one with it.
- **Documents (Group F)** depend on how the business sets stock effect per document type. Check on stock-updating invoices, and on quotations that ignore stock.
- **Stock status (TC-E1)** reads the item's thresholds at write time. Confirm an item filled after creation reports the same status as one created with that stock.
- **API cases (Group H)** need a real external app token against a business with the tracking plan. Mocks cannot prove the token path applies the same rules.
