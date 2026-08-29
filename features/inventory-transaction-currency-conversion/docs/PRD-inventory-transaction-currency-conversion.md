# Inventory: currency conversion rate on stock movements — PRD

| | |
|---|---|
| **Status** | Draft — for review |
| **Owner** | Jeet (Product) |
| **Modules** | Inventory (primary) · Workflow & Documents (reads only) |
| **Asana** | *not yet created* |
| **Companions** | [TESTS](TESTS-inventory-transaction-currency-conversion.md) · [TASK](TASK-inventory-transaction-currency-conversion.md) · [HANDOFF](HANDOFF-inventory-transaction-currency-conversion.md) |
| **Grounding** | [code-findings.md](code-findings.md) (F1–F17; F7 corrected 2026-08-18) · [decisions.md](decisions.md) (D1–D27) · [ADR 0001](adr/0001-inventory-values-a-movement-at-the-documents-rate.md) · [ADR 0002](adr/0002-store-the-rate-not-the-converted-price.md) |
| **Related** | [inventory-net-price-on-transactions](../../inventory-net-price-on-transactions/) — same record, same builders, same averaging engine. See D16. |

## How to read this doc

Three words are used in one fixed meaning each. They are not interchangeable.

| Term | Means |
|---|---|
| **transaction currency** | The currency a stock movement happened in. Today's `currency` field. It comes from the source document. |
| **business currency** | The business's own currency — the one reports and averages are expressed in. Stored on a movement as `bookCurrency`. |
| **conversion rate** | Business-currency units per 1 unit of transaction currency. Stored as `conversionRate`. So `book value = price × conversionRate`. Always this direction, everywhere in this doc. |

Two cautions. **Never say just "rate"** — a document line has its own `rate` field, which is its
**unit price**, nothing to do with currency. This doc says "conversion rate" or "unit price", never
the bare word. And the business's own currency is called **business currency** throughout;
`bookCurrency` is only the field name for it.

Division of labour, stated once. This PRD owns behaviour.
[TESTS](TESTS-inventory-transaction-currency-conversion.md) owns the test cases.
[HANDOFF](HANDOFF-inventory-transaction-currency-conversion.md) owns why each choice was made.

## What we're building

Every stock movement will record the rate it was valued at, and the currency it was valued into. The
rate comes from the document that created the movement. That is the same rate the invoice total and
the accounting entry already used.

Reports then convert from that stored rate. They stop adding mixed currencies together, and stop
fetching a rate per row. Averages apply and unwind at one recorded rate, so an edit or a return
leaves the average exactly where it should be.

One live fault is fixed alongside: a failed rate lookup no longer values a foreign price as if it
needed no conversion.

## Problem

A business selling in a currency other than its own gets stock numbers it cannot trust.

When a foreign-currency invoice or purchase moves stock, the movement records how much moved and in
which currency. It does not record what that was worth to the business. Nothing on the movement says
how to convert it.

Four things follow.

- **A report adds currencies together.** The party transaction report totals prices across movements
  without converting any of them. 100 dollars and 100 rupees are added as 200. The total is not in any
  currency at all.
- **The same sale is worth three different things.** The invoice shows one value. The books show the
  same value. The item's average cost shows a third, because stock valuation looks up its own market
  rate. If the user set the rate by hand to what their bank gave them, stock ignores it.
- **A failed rate lookup goes unnoticed.** When the rate cannot be fetched, the price enters the
  average as though no conversion were needed. A 100 dollar purchase counts as 100 rupees. Nothing is
  logged.
- **An item's own price and its average disagree, silently.** An item can be priced in one currency
  while its average is held in another. Nothing on the record says which is which.

None of this is visible. The numbers look ordinary. They are simply not true.

## Why it matters

- **These numbers set prices.** Average cost drives margin and reorder decisions. A wrong average is
  a wrong price.
- **Stock is an asset.** Stock value that disagrees with the ledger is a year-end problem, and the
  difference cannot be explained, because the rate used was never written down.
- **Nobody can catch it.** The user cannot see it. Support cannot reconstruct it, for the same
  reason.
- **It blocks later work.** FIFO/LIFO valuation cannot be built on movements with no reliable value.
- **It is not rare.** Roughly 40% of users are outside India, and cross-border trade is ordinary for
  the rest.

## Acceptance criteria

- [ ] **AC1** — A stock movement created from a foreign-currency document is valued at that
      document's rate. Its business-currency value matches the document total. Where accounting
      posting is enabled for that business and document type, it also matches the accounting entry
      for the same line.
- [ ] **AC2** — A user's rate override on a document is used by stock valuation, not just by the
      invoice and the books.
- [ ] **AC3** — Every stock report states its totals in the business currency. No report adds two
      currencies together.
- [ ] **AC4** — Deleting, cancelling or editing a document returns the item's average cost and
      selling price to exactly the value they held before it, to within floating-point tolerance.
- [ ] **AC5** — Correcting the rate on a document restates the movements it created, and the averages
      they fed.
- [ ] **AC6** — Creating an item with opening stock in another currency returns the same
      `avgCostPrice` in its response as a later read of that item returns. Both are in the business
      currency.
- [ ] **AC7** — A business that trades only in its own currency sees no change to any stock number,
      report or average.

## Desired behaviour

### FL1 — Valuing a movement created from a document

The movement stores `conversionRate` and `bookCurrency`, alongside the existing transaction currency
(`currency`), `costPrice` and `sellingPrice`.

**(normative) Rate resolution order.** Apply the first rule that matches.

| # | Condition | `conversionRate` |
|---|---|---|
| 1 | Transaction currency equals business currency | `1` |
| 2 | Source document has `conversionRates[bookCurrency]` set and greater than `0` | That value |
| 3 | Otherwise | A rate lookup for `transactionDate`, converting the transaction currency into the business currency |
| 4 | The lookup returns nothing usable — including when `transactionDate` is missing, or is in the future and the service has no rate for it | See **FL9** |

**(normative)** `bookCurrency` is the business currency at the moment the movement is written.

**(normative)** `conversionRate` and `bookCurrency` are stored on **every** movement, whatever its
`transactionType` — `UPDATE`, `BLOCK`, `BLOCK_IGNORE` or `IGNORE`. `transactionType` governs
whether a movement feeds an average (FL3) and whether it moves stock. It **never** governs whether
the rate is recorded. A movement's `transactionType` can change after it is written, so a
conditionally-stored rate would be missing when FL4 needs it. See D27.

**(normative) Direction.** `book value = price × conversionRate`. This is the direction the existing
average calculation already multiplies by, so no arithmetic changes meaning.

**(normative)** This applies to both ways a document creates a movement: a document saved directly,
and a document created by converting another one.

### FL2 — Valuing a movement with no document

**(normative)** `MANUAL`, `BULKMANUAL` and `RECONCILE` movements resolve by the FL1 table. Having no
document, they can only reach rule 1 or rule 3.

**(normative)** `TRANSFERSTOCK` movements are **excluded**. A transfer already carries a cost and
selling price of zero and no currency, and is gated out of every average at item, warehouse and batch
level. There is nothing to convert. A transfer must not be given a `conversionRate`, and must not be
given a price in order to justify one. See **EC15** and D25.

### FL3 — Feeding the averages

**(normative)** The item's `avgCostPrice` and `avgSellingPrice`, the per-warehouse pair, and the
per-batch pair are all computed from `price × quantity × conversionRate`.

**(normative)** Which movements feed an average is unchanged. `UPDATE` and `BLOCK` do. `IGNORE` and
`BLOCK_IGNORE` do not. This feature changes only the rate applied — never which movements are
averaged, and never which move stock.

**(normative)** An item created with opening stock already stores its opening average as
`price × conversionRate` — this is existing, correct behaviour and must not regress. What changes
is that the **create response** must report that same stored value, rather than the raw unconverted
price it reports today. This is AC6.

### FL4 — Reversing and editing

**(normative)** A reversal unwinds using the `conversionRate` stored on the movement it reverses. It never
looks a rate up again.

This is what makes AC4 hold. The same number that went in comes out, whatever has happened to market
rates or to the rate service since.

### FL5 — Correcting a document's rate

**(normative)** Changing `conversionRates` on a document re-runs its stock movements. This matches
what changing the document's `currency`, or a line's unit price (the line's own `rate` field),
already does.

**(normative)** The movements restamp to the new rate. The averages unwind at the old rate and
re-apply at the new one.

### FL6 — Releasing a reservation on conversion

When a reserved document (`BLOCK`) converts into one that moves stock (`UPDATE`), the reservation is
released as `BLOCK_IGNORE`.

**(normative)** That release unwinds at the rate stored on the original reserving movement, per FL4.
It does not use the new document's rate. The new document's movement then applies its own rate under
FL1.

### FL7 — Reports

**(normative)** This flow governs any report that reads a price off a movement — today Party
transaction, Product wise P&L and All transaction (F15). Reports built on an item's or a batch's own
price, such as Stock value and Batch expiry, are **out of its scope** and unchanged.

**(normative)** A movement's stored rate is **usable** when `conversionRate` is set **and**
`bookCurrency` equals the business's current currency.

**(normative)** Where the rate is usable, the report multiplies by it before summing, and states its
totals in `bookCurrency`. Reports that fetch a rate per row today read the stored rate instead, which
removes a network call per row.

**(normative)** **No report ever excludes a movement.** Where the rate is not usable — unfilled,
or stored against a previous business currency — the report falls back to exactly what it does
today:

| Report path | Fallback |
|---|---|
| The party transaction aggregation | Rate `1`. Unchanged from today, which does not convert at all. |
| The paths that loop per row (Product wise P&L, client-wise sales) | Keep today's live rate lookup. **Dropping these to `1` would be a regression** on reports that convert history correctly now. |

This is why a report window spanning a change of business currency (**EC13**) is safe: it contains
movements under two `bookCurrency` values, and both contribute.

### FL8 — Filling in historical movements

Movements written before this ships have no `conversionRate`. There is **no migration and no
background sweep**. History is left alone.

**(normative)** Filling happens in exactly one place: when an existing movement is patched or
reversed for any other reason, it fills its `conversionRate` and `bookCurrency` on the way through.
Filling resolves the rate by the FL1 table.

**(normative)** A movement needs filling when `currency` is set, differs from `bookCurrency`, and
`conversionRate` is unset.

**(normative)** Filling never happens during a report read.

**(normative)** A movement that is never touched again is never filled. It is read under the FL7
fallback for ever, which is safe by construction. See **OQ2** on whether to say so on screen.

### FL11 — Any job that recomputes averages

**(normative)** The stock-integrity job recomputes `avgCostPrice` and `avgSellingPrice` at item,
warehouse, batch and batch-warehouse level and writes them back. It must resolve the rate by the same
rules as FL1 and FL3, reading the rate stored on each transaction.

**(normative)** It must not substitute `1` for a missing rate, for the same reason as FL9.

**(normative)** After a run, the averages it produces must equal the averages the live path produces
for the same transactions. If they disagree, one of the two implementations is wrong.

### FL9 — No rate available (negative flow)

**(normative)** When rule 4 of the FL1 table is reached, the movement is still written and stock
quantity still moves. A stock movement is never blocked because a rate could not be fetched.

**(normative) What is not allowed:** silently substituting `1` for a failed lookup on a
cross-currency movement. That is the current behaviour, and it is a defect.

**Working default, pending OQ1 (open, @engineering).** Write the movement with `conversionRate` unset.
Raise a Sentry alert naming the currencies and the movement, matching the pattern the document path
already uses. Let stock quantity move. Do not feed the movement into the average.

**(normative)** Filling that movement's rate later does **not** add it to the average retroactively.
Filling corrects reports, never stored averages — the same rule as FL8 and EC10. The movement enters
the average only if its document is edited, which re-runs FL5. Only the ruling-out of a silent `1` is
settled. The rest of this working default may change when **OQ1** resolves.

### FL10 — A single-currency business (negative flow)

**(normative)** A business whose documents are all in its own currency resolves every movement to
rate `1` by rule 1. Averages, reports and stock numbers are arithmetically identical to today. No
migration touches its data, because no movement matches the FL8 filling condition.

## Scope

### In

| Area | What changes |
|---|---|
| Movement record | Add `conversionRate` and `bookCurrency`. `currency`, `costPrice`, `sellingPrice` unchanged. Warehouse transfers excluded (D25). |
| Both movement builders | Resolve and stamp the rate (FL1). |
| Averaging engine | Use the stored rate. Apply and unwind at the same rate (FL3, FL4). |
| Warehouse and batch averages | Same treatment (FL3). |
| Document rate edits | Re-trigger the stock path (FL5). |
| Failed lookups | Stop the silent substitution of `1` (FL9). |
| Opening stock | Convert the opening average (FL3). |
| Inventory reports | Convert from the stored rate (FL7). Mapped in F15: only **Party transaction**, **Product wise P&L** and **All transaction** read a transaction price. Party transaction is the only one whose numbers visibly change. **Stock value**, **Batch expiry** and **Stock status** read item or batch prices and are untouched. |
| Client-wise sales, transactions API, batch export | Same rule; the API and export must expose the rate so consumers can convert. |
| Stock-integrity job | Recomputes the same averages with its own copy of the logic. Must be corrected in step (**FL11**). |
| History | Lazy filling (FL8). |
| Glossary | Add `conversionRate` and `bookCurrency` to `docs/glossary.md`. |

### Out

- **How documents store or fetch rates.** Unchanged. This feature reads what is already there.
- **Accounting postings.** No ledger, voucher or tax change.
- **Full inventory valuation** (FIFO/LIFO, valuation runs). Separate, prototype-only work.
- **Net / discount-adjusted price on movements.** Separate task — see D16 and the warning below.
- **Document-level discount apportionment.** Out of both tasks.
- **A one-shot historical migration.** Rejected in D5.
- **Showing users which movements are not yet filled.** OQ2, not committed here.

> **Collision warning.** [inventory-net-price-on-transactions](../../inventory-net-price-on-transactions/)
> adds fields to the same record, and edits the same two builders and the same averaging engine.
> Sequencing is unresolved (**OQ3**). Whoever picks up either task must read the other's spec first.

## Edge cases and break risks

| # | Case | Handling |
|---|---|---|
| **EC1** | The business changes its business currency after movements exist. | `bookCurrency` records which currency each movement was valued into, so a switch cannot silently reinterpret history. Restating those movements is **not** in scope. The field makes the problem detectable, not fixed. |
| **EC2** | A credit note is raised later, at a different rate than the original sale. | The credit note uses its own rate (D13). **Accepted, not fixed:** a full return at a different rate does not restore the average exactly. The gap is a real exchange effect, not an error. |
| **EC3** | A document's rate is edited many times. | Each edit re-runs FL5. Averages churn accordingly. Accepted. |
| **EC4** | One document line is split across several batches. | Each resulting movement carries the same rate, mirroring how the line's price is already applied per batch. |
| **EC5** | A rate lookup succeeds when a movement is created and fails when it is reversed. | Cannot corrupt the average. FL4 reuses the stored rate and never looks up again. This is the failure that makes FL4 non-negotiable. |
| **EC6** | A movement is filled by the sweep while a report is running. | Reports never write (FL8). The only effect is that the same report can give a different total before and after filling. Expected during the fill period. |
| **EC7** | A stored rate is `0` or negative. | Neither is a valid rate. Rule 2 of FL1 accepts only a value greater than `0`; anything else falls through to rule 3. Documents never persist a failed lookup at all (F2), so there is no stored-`0` convention to copy — this rule is the inventory-side equivalent, not a mirror of it. `conversionRates` is editable by the client or vendor, so a malformed value is a realistic input. |
| **EC8** | A document has no currency at all. | One builder already falls back to the item's currency and the other does not. The two must agree. See **OQ4**. |
| **EC9** | A movement is created before the business has any currency set. | Business currency defaults to `INR` in the existing code path. `bookCurrency` records that, so the assumption is explicit on the row. |
| **EC10** | Existing averages are wrong today and are not recomputed. | Under D5 they stay wrong until diluted by new activity, or corrected by a later edit. **Known, accepted, and must be said out loud** to anyone reading a stock report during the fill period. |
| **EC11** | Package and group items. | A package on a document creates a movement for the parent **and** one per child (F17). **(normative)** All of them carry the same rate: the children inherit the parent's `currency`, so the rate follows. The child payload is an **allow-list of fields copied from the parent** — `conversionRate` and `bookCurrency` must be added to it, or every package child is written without a rate. Packages still never move `stockInHand`; per D27 that does not exempt them from carrying the rate. |
| **EC12** | A very small or very large rate. | The existing lookup records rates to six decimal places (F4). Storing the rate rather than a converted price means precision is not lost at write time. |
| **EC15** | Someone later "completes" the feature by stamping a rate on a warehouse transfer. | **Ruled out (D25).** A transfer has a zero price and is excluded from every average by design, so a rate would be meaningless. Giving it a price to make the rate meaningful would start moving warehouse averages that are deliberately stable. Separately, and out of scope: because a transfer carries no cost, stock moving between warehouses does not carry its cost basis with it. |
| **EC14** | An item is priced in one currency, and a document for it is raised in another — including when the document's currency equals the business currency. | The document's currency wins for the transaction, so the average is correct. **Accepted, not fixed:** the item record is left holding a price in the item's currency and an average in the business currency, with no label on either. Naming that on the record is **OQ6**, not this task. |
| **EC13** | A report covers a period that spans a change of business currency. | **Handled by FL7 (D23).** EC1 keeps each movement's original `bookCurrency`, so such a report holds movements under two of them. Rows matching the current currency convert; the rest fall back to today's behaviour. **No row is excluded** — an incomplete report is worse than an imprecise one. |

**Break risk.** The averaging engine is shared by every stock movement in the product, including
single-currency businesses that have none of this problem. AC7 holds that line. The regression suite
must prove a single-currency business is untouched.

## What to test

Test cases live in [TESTS-inventory-transaction-currency-conversion.md](TESTS-inventory-transaction-currency-conversion.md),
which is normative for coverage.

Convention: every flow above implies its failure-mode tests as well as its happy path. Every
acceptance criterion and edge case maps to at least one test case.

## Technical design (brief)

**Chosen approach.** Two new fields on the movement record — `conversionRate` (Number) and `bookCurrency`
(currency enum). The rate is resolved from the source document and stamped at write time.

**Why the rate and not the converted price.**
[ADR 0002](adr/0002-store-the-rate-not-the-converted-price.md). In short: converted prices need a
twin for every price field on a record that is about to gain more; the rounding argument that
justifies storing converted totals in accounting does not apply to unit prices; and a stored derived
value can drift from what it derives from.

**Why the document's rate and not a market rate.**
[ADR 0001](adr/0001-inventory-values-a-movement-at-the-documents-rate.md).

**Rejected alternatives.**

- *Recompute the rate on read instead of storing it* — cannot work. The report paths that are most
  wrong aggregate inside the database, where there is nothing to recompute from.
- *Store converted prices as well* — ADR 0002.
- *One-shot backfill of history* — D5. Volume.
- *Merge with the net-price task* — D16. That task is already being estimated.

**Key insight.** The party transaction report adds currencies together not through carelessness, but
because a database aggregation cannot multiply by a rate that is not a field on the row. Storing the
rate is what makes it fixable at all.

**Standing constraint.** The movement log is append-only. Edits and deletes happen by reversal. Any
rate rule must therefore be exact in both directions, which is what FL4 enforces.

## Open questions

| # | Question | Owner | Working default |
|---|---|---|---|
| **OQ1** (D4) | What happens when no rate can be resolved for a cross-currency movement? | Engineering | `conversionRate` unset, alert raised, stock quantity still moves, movement kept out of the average until filled. Silently substituting `1` is ruled out. |
| **OQ2** (D6) | Should reports tell the user that some movements are not yet converted, rather than counting them at rate `1`? | Jeet + team | Count at rate `1` with no user-facing note, matching today exactly. |
| **OQ3** (D16) | Does this ship before or after [inventory-net-price-on-transactions](../../inventory-net-price-on-transactions/)? | Jeet | Undecided. Both edit the same two builders and the same averaging engine. Whichever is second rebases. |
| **OQ4** (D17) | When a document has no currency at all, do both builders fall back to the item's currency? | Engineering | Yes — make the two builders agree, since they differ today (EC8). |
| **OQ6** (D21) | Should the item record say which currency its averages are in (EC14, F12)? | Jeet | Not in this task. Averages are always in the business's current currency; the transaction's new `bookCurrency` makes that checkable per row. Adding a label to the item itself is a separate change. |
