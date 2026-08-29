# Inventory: currency conversion rate on stock movements — Test Cases

| | |
|---|---|
| **PRD** | [PRD-inventory-transaction-currency-conversion.md](PRD-inventory-transaction-currency-conversion.md) |
| **Task** | [TASK-inventory-transaction-currency-conversion.md](TASK-inventory-transaction-currency-conversion.md) |
| **Handoff** | [HANDOFF-inventory-transaction-currency-conversion.md](HANDOFF-inventory-transaction-currency-conversion.md) |

Every flow in the PRD implies its failure-mode tests as well as its happy path. Test ids are stable
once written: retire a group with a strikethrough and a reason, never renumber.

Throughout, unless a case says otherwise: the business currency is **INR**, the document currency is
**USD**, and the rate in play is **83.00**.

---

## Group A — Rate resolution when a document creates a movement

### TC-A1 — Same currency resolves to 1
- **Setup:** INR business, INR invoice, one stock-managed item.
- **Action:** Save the invoice so it moves stock.
- **Expected:** The movement has `conversionRate` = `1` and `bookCurrency` = `INR`.

### TC-A2 — A document's stored rate is used
- **Setup:** INR business, USD invoice carrying `conversionRates.INR` = `83.00`.
- **Action:** Save the invoice.
- **Expected:** The movement has `conversionRate` = `83.00`, `currency` = `USD`, `bookCurrency` = `INR`.
  No rate lookup is made.

### TC-A3 — A user's override wins over the market rate
- **Setup:** INR business, USD invoice where the user overrode `conversionRates.INR` to `82.50`. The
  rate service would return `83.17` for that date.
- **Action:** Save the invoice.
- **Expected:** The movement has `conversionRate` = `82.50`. `83.17` appears nowhere.

### TC-A4 — No document rate falls back to a lookup
- **Setup:** INR business, USD invoice with `conversionRates` empty. Rate service returns `83.17` for
  the invoice date.
- **Action:** Save the invoice.
- **Expected:** The movement has `conversionRate` = `83.17`, looked up for `transactionDate`.

### TC-A5 — A stored rate of zero is treated as absent
- **Setup:** INR business, USD invoice with `conversionRates.INR` = `0`. Rate service returns `83.17`.
- **Action:** Save the invoice.
- **Expected:** `conversionRate` = `83.17`. The `0` is not stored and not used.

### TC-A5b — A negative stored rate is treated as absent
- **Setup:** INR business, USD invoice with `conversionRates.INR` = `-83.00`. Rate service returns
  `83.17`.
- **Action:** Save the invoice.
- **Expected:** `conversionRate` = `83.17`. Rule 2 accepts only a value greater than `0`.

### TC-A5c — A missing transaction date routes to the no-rate path
- **Setup:** INR business, USD document with no usable `transactionDate` and no stored rate.
- **Action:** Save it.
- **Expected:** Rule 4 is reached and FL9 applies. No rate is guessed.

### TC-A6 — Book currency is stamped from the business
- **Setup:** A business whose currency is `AED`. A USD invoice.
- **Action:** Save the invoice.
- **Expected:** `bookCurrency` = `AED`, and the rate converts USD into AED — not into INR.

### TC-A7 — Converted documents stamp the rate too
- **Setup:** INR business. A USD quotation converted into a USD invoice at rate `83.00`.
- **Action:** Complete the conversion.
- **Expected:** The movement carries `conversionRate` = `83.00` and `bookCurrency` = `INR`, same as a
  directly saved document.

### TC-A8 — The movement agrees with the document
- **Setup:** INR business, USD invoice, one line of 10 units at 100 USD, rate `83.00`.
- **Action:** Save the invoice.
- **Expected:** `sellingPrice × quantity × conversionRate` equals that line's business-currency value on
  the document, within floating-point tolerance.

### TC-A9 — Purchases resolve the same way
- **Setup:** INR business, USD purchase or expenditure at rate `83.00`.
- **Action:** Save it.
- **Expected:** A `BUY` movement with `costPrice` in USD, `conversionRate` = `83.00`, `sellingPrice` = `0`.

### TC-A10 — A document with no currency
- **Setup:** A document carrying no `currency`, for a stock-managed item.
- **Action:** Save it through the direct path, then the converted-document path.
- **Expected:** Both paths resolve `currency` and `conversionRate` identically. (They differ today — PRD
  EC8, OQ4.)

---

## Group B — Movements with no document

### TC-B1 — Manual adjustment in the business currency
- **Setup:** INR business, item priced in INR.
- **Action:** Adjust stock manually.
- **Expected:** `conversionRate` = `1`, `bookCurrency` = `INR`. No lookup.

### TC-B2 — Manual adjustment in another currency
- **Setup:** INR business, item priced in USD.
- **Action:** Adjust stock manually.
- **Expected:** `conversionRate` is the looked-up rate for `transactionDate`. No document rate is consulted,
  because there is no document.

### TC-B3 — A warehouse transfer gets no rate and moves no average
- **Setup:** INR business, item priced in USD, two warehouses. Record every average first.
- **Action:** Transfer stock between them.
- **Expected:** Neither movement carries a `conversionRate` or a price. Item, warehouse and batch
  averages are all unchanged. Only quantity moved. (PRD FL2, EC15.)

### TC-B4 — Bulk adjustment and reconciliation
- **Setup:** INR business, item priced in USD.
- **Action:** Run a bulk manual adjustment, then a reconciliation movement.
- **Expected:** Both resolve by the same rules as TC-B2.

---

## Group C — Feeding the averages

### TC-C1 — Average cost is in business currency
- **Setup:** INR business, item with no stock.
- **Action:** Buy 10 units at 100 USD, rate `83.00`.
- **Expected:** `avgCostPrice` = `8300`, not `100`.

### TC-C2 — Average selling price is in business currency
- **Setup:** INR business, item with stock.
- **Action:** Sell 5 units at 120 USD, rate `83.00`.
- **Expected:** `avgSellingPrice` = `9960`.

### TC-C3 — Per-warehouse averages convert
- **Setup:** INR business with warehouses enabled, USD purchase into one warehouse.
- **Action:** Save it.
- **Expected:** That warehouse's `avgCostPrice` is converted, and matches the item-level average for
  the same movements.

### TC-C4 — Per-batch averages convert
- **Setup:** INR business, batch-tracked item, USD purchase into one batch.
- **Action:** Save it.
- **Expected:** The batch's `avgCostPrice` is converted, and agrees with the item-level average.

### TC-C5 — Which movements feed an average is unchanged
- **Setup:** INR business. USD documents producing one movement each of `UPDATE`, `BLOCK`, `IGNORE`,
  `BLOCK_IGNORE`.
- **Action:** Create all four.
- **Expected:** `UPDATE` and `BLOCK` change the averages. `IGNORE` and `BLOCK_IGNORE` do not. All four
  carry a `conversionRate`.

### TC-C6 — Opening stock is converted, in the response as well as the record
- **Setup:** INR business.
- **Action:** Create an item priced in USD at 100, with opening stock of 10, rate `83.00`. Read the
  create response, then refetch the item.
- **Expected:** Both report `avgCostPrice` = `8300`. The stored value is already correct today; the
  response is not, and must be.

### TC-C9 — A document in the business currency against an item priced in another
- **Setup:** INR business, item priced in USD, INR invoice.
- **Action:** Save the invoice.
- **Expected:** The transaction carries `currency` = `INR` and `conversionRate` = `1`. The average is
  in INR. The item keeps `currency` = `USD` and its USD `costPrice` (PRD EC14).

### TC-C10 — The integrity job agrees with the live path
- **Setup:** An item with a mix of INR and USD transactions, averages already correct.
- **Action:** Run the stock-integrity job.
- **Expected:** Every average is unchanged. It must not revert them to market-rate values.

### TC-C11 — The integrity job never substitutes a rate of 1
- **Setup:** A cross-currency transaction with no usable rate, and the rate service failing.
- **Action:** Run the stock-integrity job.
- **Expected:** It does not count the foreign price as if it were already in the business currency.

### TC-C12 — A rate survives a change of stock effect
- **Setup:** A `BLOCK` movement from a foreign-currency proforma, carrying a rate.
- **Action:** Convert the proforma so the movement becomes `BLOCK_IGNORE`, then delete the invoice.
- **Expected:** The movement keeps its original rate throughout, and the reversal unwinds at it. The
  rate is never dropped because the stock effect changed (PRD FL1, D27).

### TC-C13 — An unmanaged item's movement still carries a rate
- **Setup:** INR business, USD invoice, a line item that is **not** stock-managed — so its
  movement resolves to `IGNORE`.
- **Action:** Save the invoice, then open the All transaction report.
- **Expected:** The movement carries a `conversionRate` and `bookCurrency`, no average moves, and the
  report can show what the row was worth.

### TC-C7 — Opening stock in the business currency is unaffected
- **Setup:** INR business.
- **Action:** Create an item priced in INR at 8300, with opening stock of 10.
- **Expected:** `avgCostPrice` = `8300`, identical to today.

### TC-C8 — A package writes the rate on the parent and on every child
- **Setup:** INR business, a package item whose children are stock-managed, on a USD invoice at rate
  `83.00`.
- **Action:** Save the invoice.
- **Expected:** The package's own movement **and** every child movement carry `conversionRate` =
  `83.00` and `bookCurrency` = `INR`. No child is written without a rate. (PRD EC11, F17.)

---

## Group D — Reversing and editing

### TC-D1 — Deleting a document restores the average exactly
- **Setup:** INR business. Buy 10 at 100 USD, rate `83.00`. Record `avgCostPrice`.
- **Action:** Buy 5 more at 110 USD, rate `84.00`. Then delete the second purchase.
- **Expected:** `avgCostPrice` returns to its recorded value, to within floating-point tolerance.

### TC-D2 — Cancelling a document restores the average exactly
- **Setup:** As TC-D1.
- **Action:** Cancel the second purchase instead of deleting it.
- **Expected:** Same as TC-D1.

### TC-D3 — Editing quantity unwinds and reapplies
- **Setup:** INR business, USD purchase of 10 units at rate `83.00`.
- **Action:** Edit the quantity to 6.
- **Expected:** The average equals what it would be had the purchase been for 6 units from the start.

### TC-D4 — Reversal uses the stored rate, not today's
- **Setup:** A USD purchase at rate `83.00`. The rate service now returns `90.00` for that date.
- **Action:** Delete the purchase.
- **Expected:** The average unwinds at `83.00` and returns to its exact prior value. `90.00` is never
  used.

### TC-D5 — Reversal works while the rate service is unavailable
- **Setup:** A USD purchase at rate `83.00`. The rate service is then made to fail every call.
- **Action:** Delete the purchase.
- **Expected:** The reversal succeeds and the average returns to its exact prior value. No lookup is
  attempted.

---

## Group E — Correcting a document's rate

### TC-E1 — A rate edit restamps the movements
- **Setup:** INR business, USD invoice at rate `83.17`, stock moved.
- **Action:** Change `conversionRates.INR` to `82.50`.
- **Expected:** The invoice's movements now carry `conversionRate` = `82.50`.

### TC-E2 — A rate edit restates the averages
- **Setup:** As TC-E1.
- **Action:** Change the rate.
- **Expected:** The averages equal what they would be had the invoice been saved at `82.50` from the
  start.

### TC-E3 — Repeated rate edits stay correct
- **Setup:** As TC-E1.
- **Action:** Change the rate three times, ending at `82.00`.
- **Expected:** The final averages equal those for a single invoice saved at `82.00`. No drift
  accumulates.

### TC-E4 — Changing the document currency still works
- **Setup:** INR business, USD invoice with stock moved.
- **Action:** Change the document currency to EUR.
- **Expected:** The movements restamp with the new currency and a rate for that currency. This
  behaviour exists today and must not regress.

---

## Group F — Releasing a reservation on conversion

### TC-F1 — The release unwinds at the reserving document's rate
- **Setup:** INR business. A proforma reserving stock (`BLOCK`) at rate `83.00`.
- **Action:** Convert it fully into an invoice whose rate is `84.00`.
- **Expected:** The reservation is released using `83.00`. The invoice's own movement applies
  `84.00`.

### TC-F2 — The net result after conversion is correct
- **Setup:** As TC-F1.
- **Action:** Complete the conversion.
- **Expected:** The averages equal those of an invoice at `84.00` alone, with no residue left by the
  released reservation.

---

## Group G — Reports

### TC-G1 — A mixed-currency report totals in business currency
- **Setup:** INR business with movements in INR, USD and AED.
- **Action:** Run every stock report that totals prices across movements.
- **Expected:** Each total is the sum of `price × quantity × conversionRate`, in INR. No total mixes
  currencies.

### TC-G2b — Each named report behaves as mapped
- **Setup:** INR business with INR and USD transactions, and a recorded baseline of all six reports.
- **Action:** Run Party transaction, Product wise P&L, All transaction, Stock value, Batch expiry and
  Stock status.
- **Expected:** Party transaction changes materially. Product wise P&L changes only where a document
  rate was overridden. All transaction shows the same figures plus the rate. **Stock value, Batch
  expiry and Stock status are byte-identical** — they read item or batch prices, not transactions.

### TC-G2 — The previously unconverted aggregation now converts
- **Setup:** INR business, one INR movement of 100 and one USD movement of 100 at rate `83.00`.
- **Action:** Run the party transaction report.
- **Expected:** The total is `8400`, not `200`. Its average unit price follows the corrected total.

### TC-G3 — The previously converting reports give the same answer
- **Setup:** A business whose movements all carry the `conversionRate` the rate service would have
  returned.
- **Action:** Run the reports that used to look a rate up per row.
- **Expected:** Totals identical to the previous implementation.

### TC-G4 — Reports no longer call the rate service per row
- **Setup:** A business with 500 cross-currency movements, all carrying a `conversionRate`.
- **Action:** Run a report over them.
- **Expected:** No per-row rate lookup is made.

### TC-G5 — Single-currency reports are unchanged
- **Setup:** An INR-only business, with a recorded baseline of every stock report before the change.
- **Action:** Run the same reports after.
- **Expected:** Byte-identical figures.

### TC-G7 — A row stored against a previous business currency still counts
- **Setup:** An INR business with movements carrying `bookCurrency` = `INR`. Switch it to AED.
- **Action:** Run a report covering both periods.
- **Expected:** The INR-stamped rows are **not** excluded. They fall back per FL7 — rate `1` in the
  database aggregations, today's live lookup in the per-row paths.

### TC-G8 — The converting reports do not regress on unfilled rows
- **Setup:** Unfilled cross-currency movements, and a baseline of what the per-row report paths return
  for them today.
- **Action:** Run those reports after the change.
- **Expected:** Identical figures to the baseline. They must not drop to rate `1`.

### TC-G6 — A report spanning a change of business currency
- **Setup:** A business with INR movements, which then switches to AED and records more.
- **Action:** Run a stock report covering both periods.
- **Expected:** Per **OQ5**'s working default, only movements matching the current business currency
  are totalled, and the report states how many it excluded. Never one summed figure.

---

## Group H — Filling in history

### TC-H1 — A cross-currency historical row is selected for filling
- **Setup:** An existing movement with `currency` = `USD`, no `conversionRate`, in an INR business.
- **Action:** Run the selection that identifies rows needing a fill.
- **Expected:** The row is selected.

### TC-H2 — A same-currency historical row is left alone
- **Setup:** An existing movement with `currency` = `INR`, no `conversionRate`, in an INR business.
- **Action:** Run the same selection.
- **Expected:** The row is not selected and is never written to.

### TC-H3 — Patching an old movement fills its rate
- **Setup:** An unfilled cross-currency movement.
- **Action:** Patch it for any unrelated reason.
- **Expected:** It comes out carrying a `conversionRate` and a `bookCurrency`.

### TC-H4 — A reversal fills the rate too
- **Setup:** An unfilled cross-currency movement.
- **Action:** Reverse it.
- **Expected:** It carries a rate resolved by the PRD's FL1 table — from its document where one
  exists, otherwise a lookup at `transactionDate`.

### TC-H5 — A report read never fills
- **Setup:** Unfilled cross-currency movements.
- **Action:** Run every stock report over them.
- **Expected:** No movement is written to. The unfilled count is unchanged.

### TC-H6 — An unfilled row is never dropped
- **Setup:** One unfilled USD movement of 100 in an INR business.
- **Action:** Run every stock report.
- **Expected:** It appears in all of them. In the party transaction aggregation it contributes `100`,
  as today. In the per-row paths it converts via today's live lookup.

### TC-H7 — Nothing fills history on its own
- **Setup:** Unfilled cross-currency movements. No document is edited and no reversal is made.
- **Action:** Let the system run, including any scheduled jobs.
- **Expected:** The movements stay unfilled. There is no migration and no background sweep.

### TC-H8 — Filling a rate does not recompute stored averages
- **Setup:** An item whose average was computed before this change, with unfilled movements.
- **Action:** Fill those movements.
- **Expected:** The item's stored `avgCostPrice` is unchanged. Filling corrects reports, not history.
  (PRD EC10 — accepted.)

---

## Group I — When no rate can be resolved

> These assert the one rule that is settled. The rest of the behaviour is **OQ1** and follows the
> PRD's stated working default; revise this group if OQ1 resolves differently.

### TC-I1 — Stock still moves
- **Setup:** INR business, USD invoice with no stored rate, rate service failing.
- **Action:** Save the invoice.
- **Expected:** The movement is written and `stock`/`stockInHand` change as normal. Saving is not
  blocked.

### TC-I2 — A failure is never silently treated as rate 1
- **Setup:** As TC-I1.
- **Action:** Save the invoice.
- **Expected:** The movement does **not** carry `conversionRate` = `1`. A USD price is not counted as an
  INR price. This is the current defect and must not survive.

### TC-I3 — A failure raises an alert
- **Setup:** As TC-I1.
- **Action:** Save the invoice.
- **Expected:** A Sentry alert is raised naming the currencies and the movement.

### TC-I4 — The average is not corrupted
- **Setup:** As TC-I1, with a known `avgCostPrice` beforehand.
- **Action:** Save the invoice.
- **Expected:** The average does not absorb an unconverted foreign price.

### TC-I5 — Filling a rate later does not add the movement to the average
- **Setup:** A movement written with no rate under TC-I1, and a known `avgCostPrice`.
- **Action:** Fill that movement's rate by sweep or patch.
- **Expected:** The average is unchanged. Filling corrects reports, not stored averages (PRD FL9).

---

## Group J — Single-currency businesses must not change

### TC-J1 — A full lifecycle is numerically identical
- **Setup:** An INR-only business, with a recorded baseline of every average, stock count and report
  figure.
- **Action:** Run a full lifecycle — purchase, sale, edit, credit note, delete, manual adjustment,
  transfer.
- **Expected:** Every figure matches the baseline exactly.

### TC-J2 — No filling job touches it
- **Setup:** The same business.
- **Action:** Run the fill selection and the sweep.
- **Expected:** Nothing is selected and nothing is written.

---

## Group K — Edge cases

### TC-K1 — Changing the business currency leaves a record
- **Setup:** An INR business with movements carrying `bookCurrency` = `INR`.
- **Action:** Change the business currency to AED, then create a new movement.
- **Expected:** Old movements still read `INR`; the new one reads `AED`. Old rows are not restated.
  (PRD EC1.)

### TC-K2 — A credit note stamps its own rate
- **Setup:** A USD sale at rate `83.00`.
- **Action:** Raise a credit note against it later, at rate `85.00`.
- **Expected:** The credit note's movement carries `85.00`, not `83.00`.

### TC-K3 — A full return at a different rate leaves a residue
- **Setup:** As TC-K2, returning the full quantity.
- **Action:** Complete the credit note.
- **Expected:** The average does **not** return to its pre-sale value. The gap matches the rate
  difference. Asserted as correct, not a bug. (PRD EC2.)

### TC-K4 — A line split across batches carries one rate
- **Setup:** A USD invoice line whose quantity is allocated across three batches.
- **Action:** Save the invoice.
- **Expected:** All three movements carry the same `conversionRate`.

### TC-K5 — A business with no currency set
- **Setup:** A business record with no `currency`, a USD invoice.
- **Action:** Save it.
- **Expected:** `bookCurrency` records the default the code applies (`INR`) rather than being left
  empty, so the assumption is explicit on the row.

### TC-K6 — Rate precision is preserved
- **Setup:** A currency pair whose rate has six decimal places, for example `0.011947`.
- **Action:** Create a movement.
- **Expected:** The stored `conversionRate` keeps all six decimal places.

### TC-K7 — Totals may move during the fill period
- **Setup:** A business with unfilled cross-currency movements. Record a report total.
- **Action:** Run the sweep, then re-run the report.
- **Expected:** The total changes, and the new figure is the correct converted one. (PRD EC6.)

---

## Coverage matrix

Every requirement maps to at least one test, and every test maps back to a requirement.

| Requirement | Verified by |
|---|---|
| AC1 — movement agrees with document and ledger | TC-A2, TC-A8 (document half). **Ledger half is deliberately not unit-tested** — accounting is a separate service behind an opt-in gate; covered by the live check in *What mocks cannot verify*. |
| AC2 — user override is honoured | TC-A3 |
| AC3 — reports total in business currency | TC-G1, TC-G2, TC-G2b, TC-G7, TC-G8 |
| AC4 — edits and deletes restore the average exactly | TC-D1, TC-D2, TC-D3, TC-D4, TC-D5 |
| AC5 — a rate correction restates stock | TC-E1, TC-E2, TC-E3 |
| AC6 — opening-stock response matches the record | TC-C6 |
| AC7 — single-currency businesses are untouched | TC-A1, TC-C7, TC-G5, TC-J1, TC-J2 |
| FL1 — rate resolution order | TC-A1, TC-A2, TC-A3, TC-A4, TC-A5, TC-A5b, TC-A5c, TC-A6, TC-A7, TC-A8, TC-A9, TC-A10, TC-C12, TC-C13 |
| FL2 — movements with no document | TC-B1, TC-B2, TC-B3, TC-B4 |
| FL3 — feeding the averages | TC-C1, TC-C2, TC-C3, TC-C4, TC-C5, TC-C6, TC-C7, TC-C8, TC-C9 |
| FL11 — jobs that recompute averages | TC-C10, TC-C11 |
| FL4 — reversing and editing | TC-D1, TC-D2, TC-D3, TC-D4, TC-D5 |
| FL5 — correcting a document's rate | TC-E1, TC-E2, TC-E3, TC-E4 |
| FL6 — releasing a reservation | TC-F1, TC-F2 |
| FL7 — reports | TC-G1, TC-G2, TC-G3, TC-G4, TC-G5, TC-G6, TC-G7, TC-G8 |
| FL8 — filling in history | TC-H1, TC-H2, TC-H3, TC-H4, TC-H5, TC-H6, TC-H7, TC-H8 |
| FL9 — no rate available | TC-I1, TC-I2, TC-I3, TC-I4, TC-I5 |
| FL10 — single-currency business | TC-J1, TC-J2 |
| EC1 — business changes business currency | TC-K1 |
| EC2 — credit note at a different rate | TC-K2, TC-K3 |
| EC3 — repeated rate edits | TC-E3 |
| EC4 — line split across batches | TC-K4 |
| EC5 — lookup succeeds in, fails out | TC-D4, TC-D5 |
| EC6 — filling during a report | TC-H5, TC-K7 |
| EC7 — a stored rate of zero or negative | TC-A5, TC-A5b |
| EC8 — document with no currency | TC-A10 |
| EC9 — business with no currency | TC-K5 |
| EC10 — existing averages stay wrong | TC-H8 |
| EC11 — package and group items | TC-C8 |
| EC12 — rate precision | TC-K6 |
| EC13 — report spanning a business-currency change | TC-G6, TC-G7 |
| EC14 — item currency differs from document currency | TC-C9 |
| EC15 — a rate must not be added to a warehouse transfer | TC-B3 |

## What mocks cannot verify

| Assertion | Why a mock cannot prove it | Live check |
|---|---|---|
| The movement's business-currency value equals the accounting entry's for the same line (AC1). | Accounting is a separate PostgreSQL service, and posting is opt-in per business and document type. A mocked ledger proves nothing about the real one. | On a staging business with accounting sync enabled, raise a foreign-currency invoice and compare the movement's converted value against the posted voucher line. |
| Rates and shapes returned by the live rate service. | Tests mock the service, so they prove our handling, not its behaviour. A real six-decimal rate, a missing date, or an unsupported pair are not exercised. | Query the live service for an exotic pair and a weekend date; confirm the resolution table (FL1) holds for what comes back. |
| The sweep's real cost and duration at production volume. | Test datasets are far smaller than production, so throughput and lock behaviour cannot be observed. | Run the sweep against a production-sized copy, measure lookups per minute and elapsed time before enabling it. |
| That no other report anywhere reads a price off a movement without converting. | Only the reports we know about are under test. Others may exist outside inventory. | Search every repository for reads of `costPrice` / `sellingPrice` on this collection and confirm each one converts or deliberately does not. |
| That averages agree across item, warehouse and batch on real historical data. | Fixtures start clean; production data carries years of drift from the defects being fixed. | Run the existing integrity check on a production copy after the change and compare drift against a before baseline. |
