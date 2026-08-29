# [Enhancement] Inventory: store the conversion rate on every inventory transaction

**Companions:** TESTS (attached) · PRD, Handoff, decisions D1–D27, ADR 0001/0002 in the repo

## Summary

An inventory transaction stores its price and its currency. It does not store the conversion rate to
the business currency. Three gaps follow:

- **A report mixes currencies.** The party transaction report totals prices without converting. 100
  USD and 100 INR add up to 200.
- **Averages use the wrong conversion rate.** Average cost and selling price convert at a freshly
  fetched market conversion rate, not the conversion rate on the document. A conversion rate the
  user typed by hand is honoured on the invoice and in the books, and ignored by stock.
- **Failures are silent.** If the conversion rate cannot be fetched, the price counts unconverted. A
  100 USD purchase enters the average as 100 INR. Nothing is logged.

**After this ships, every inventory transaction carries the conversion rate it was valued at and the
currency it was valued into, taken from its source document — so stock valuation, the invoice and
the books agree, and every stock report totals in one currency.**

## User Stories

- As a business trading in USD, I want my average cost in my own currency, so the margin I price
  against is real.
- As a business trading only in its own currency, I want no stock number to change at all.

## Scope

### In scope

- **Source documents** — every document that creates an inventory transaction
  - Invoice, expenditure, purchase order, proforma, quotation, sales order, delivery challan, credit
    note, debit note
  - Both entry paths — saved directly, and created by converting another document
  - **Every stock effect, including `IGNORE`.** The conversion rate goes on every transaction.
    Whether a transaction feeds an average is a separate question, and unchanged
- **Inventory flows**
  - Document create, edit, delete, cancel
  - Conversion, and the reservation release on it
  - Reversals
  - Manual and bulk manual adjustment
  - Reconciliation
  - Item creation with opening stock
- **Levels** — averages at all three
  - Item
  - Per-warehouse cache
  - Batch
- **Consumers that read a transaction price**
  - Inventory reports — Party transaction, Product wise P&L, All transaction
  - Client-wise sales
  - Inventory-transactions API and batch export — must expose the conversion rate so a consumer can
    convert
  - **The stock-integrity job that recomputes averages**
- **History**
  - Fill an old transaction's conversion rate when it is patched or reversed for some other reason
- **Glossary** — add the new terms

> **Do not skip the integrity job.** It recomputes and rewrites the same averages with its own copy of
> the conversion logic. If it is not changed with everything else, it will overwrite the corrected
> averages on its next run and the fix will silently undo itself.

### Out of scope

- **Warehouse transfer** — deliberately excluded
  - Already stores no price at all: zero cost and selling price, no currency
  - Already excluded from every average — only quantity moves between warehouses
  - **Do not add a conversion rate, and do not add a price to justify one.** That would start feeding
    averages that are deliberately untouched today
- **Documents and accounting**
  - How documents store or fetch their own conversion rates — unchanged, this feature only reads
    them
  - Accounting postings — no ledger, voucher or tax behaviour is touched
- **Other inventory work**
  - FIFO/LIFO valuation
  - Net / discount-adjusted price — separate task
  - Reports built on an item's or a batch's price, such as Stock value and Batch expiry
- **Existing data**
  - Any migration, backfill or background sweep
- **User-facing**
  - Telling users which transactions are not yet filled — open, see OQ2

> **Collision:** the net-price-on-transactions task changes the same record, the same two entry paths
> and the same averaging logic. Sequencing is open — see Handling.

## Verified Current Behaviour

What a user sees today. Checked against live code, not assumed.

- The party transaction report shows a total that is the sum of two currencies. It never converts,
  so 100 USD and 100 INR are added as 200 and presented as one figure. Its average unit price is
  derived from that same mixed total.
- The average cost of an item **is** converted into the business currency — but at a market
  conversion rate looked up at the time, not the one on the document. So a conversion rate the user
  typed on an invoice applies to the invoice and to the books, and is silently ignored for stock.
  The same sale is worth two different amounts depending on where you look.
- When the conversion rate cannot be fetched, the foreign price is counted as though it needed no
  conversion. A 100 USD purchase lands in the average as 100 INR. Nothing on screen and nothing in
  the logs says so.
- Creating an item with opening stock in another currency stores the average correctly, but the
  screen shows the unconverted number until the item is reloaded.
- An item can be priced in one currency while its average is held in another, with nothing saying
  which is which. The document's currency always wins for the stock entry, even when the item is
  priced in a different one.
- A warehouse transfer carries no price and never changes any average. Only quantity moves.

## Required Behaviour

**Every inventory transaction must record the conversion rate it was valued at, and the business
currency it was valued into.** Everything below follows from that.

**Which conversion rate applies — the first rule that matches**

1. The transaction is already in the business currency → the conversion rate is 1.
2. The source document carries a conversion rate for the business currency → use it. This is the
   conversion rate the invoice total and the accounting entry already used, including one the user
   set by hand.
3. Otherwise → look up the conversion rate for the transaction's own date.
4. Nothing usable, including a missing or future date → see **OQ1**. Treating it as 1 is ruled out.

**How each inventory flow must behave**

| Flow | Required behaviour |
|---|---|
| A document moves stock (sale, purchase, expenditure, credit or debit note) | Values at that document's conversion rate, per the rules above. |
| A document is created by converting another | Values at the new document's own conversion rate, not the source document's. |
| A reservation is released on conversion | Unwinds at the conversion rate the reservation was made at. The new document then applies its own conversion rate, so the difference lands on the invoice. |
| A document's conversion rate is corrected | Its stock entries are restated to the new conversion rate, and the averages unwind at the old one and re-apply at the new one — as correcting the currency already does. |
| A document is edited, deleted or cancelled | Unwinds at the conversion rate stored on the entry, never a freshly looked-up one. This is what makes the average return to exactly where it was. |
| Manual or bulk stock adjustment | No document, so it uses the conversion rate for its own date. |
| Reconciliation | Same as manual adjustment. |
| An item is created with opening stock | Values at the conversion rate, and the screen shows that same converted figure immediately rather than the raw price. |
| A package item is used on a document | One transaction for the package and one per child item, all at the same conversion rate — the children inherit the parent's currency. The child transactions are built by copying a fixed list of fields from the parent; the conversion rate and business currency must be added to that list, or every package child is written without one. |
| A warehouse transfer | Unchanged. No price, no conversion rate, no effect on any average. |

**How reports must use it**

This applies to any report that reads a price off an inventory transaction — today **Party
transaction**, **Product wise P&L** and **All transaction**. Reports built on an item's or a batch's
price, such as **Stock value** and **Batch expiry**, sit outside this rule and are unchanged.

What such a report must consider on each transaction:

- **Its currency and its stored conversion rate**, not just its price. The conversion rate is
  **usable** only when it exists and was stored against the business's current currency.
- **The business currency**, which every total must be stated in. A total is the sum of `price ×
  quantity × conversion rate`.
- **What to do when the conversion rate is not usable** — never leave the transaction out. Fall back
  to what that report does today. An incomplete report is worse than an imprecise one.
- **Whether it totals or lists.** A report that totals must convert. A report that lists rows must
  show the conversion rate beside the price and currency, so a reader can see what a foreign row was
  worth.

**What must not change**

Which transactions feed the averages, which ones move on-hand stock, and the fact that edits and
deletes happen by reversal rather than by rewriting history. Only the conversion rate applied
changes.

A transaction's stock effect decides whether it feeds an average. It must **never** decide whether
the conversion rate is recorded — the conversion rate goes on every transaction.

## Expected Impact

- **Party transaction is the only report whose numbers visibly change.** Product wise P&L shifts
  only where a conversion rate was overridden; All transaction gains the conversion rate and changes
  no figure.
- **Averages move to the document's conversion rate** at item, warehouse and batch level, so margin
  and pricing follow. A business trading only in its own currency sees no change anywhere.
- **Existing transactions are untouched** and stored averages are not recomputed. History corrects
  itself only as transactions are edited.
- **Nothing changes** in accounting, warehouse transfers, or any report built on item or batch
  prices.

## Risk

- The averaging logic is shared by every inventory transaction in the product. Most businesses have
  none of this problem. The regression pass must prove their numbers are untouched.
- The averaging maths exists in **two** places — the live path and the stock-integrity job. Both
  must be changed together, and they must agree afterwards, or the job reverts the fix on its next
  run.
- Correcting a conversion rate now moves averages, so a business that edits conversion rates often
  will see churn.
- A business that changes its own currency ends up with transactions valued into two currencies.
  Reports stay complete by falling back rather than excluding, but stay imprecise on the older ones.

## Handling and Tests

**Existing data — @Jeet, confirmed.** Forward-looking only. No migration, no backfill, no background
sweep. The one exception: a transaction that is patched or reversed for any other reason fills its
conversion rate on the way through, because the work is already happening.

An untouched transaction is never filled, and that is safe — reports fall back rather than dropping
it. Stored averages are **not** recomputed by filling. If history accuracy is ever raised, the first
thing to evaluate is reading the conversion rate from the source document at report time (D24) — it
needs no data change at all.

**Open items**

- **OQ1 @engineering** — what happens when no conversion rate resolves. Default: store no conversion
  rate, raise an alert, let stock quantity move, keep it out of the average. Filling later does not
  add it back.
- **OQ2 @Jeet + team** — should reports flag transactions that are not yet filled? Default: no.
- **OQ3 @Jeet** — does this ship before or after the net-price task?
- **OQ4 @engineering** — with no document currency, do both entry paths fall back to the item's
  currency? Default: yes.
- **OQ6 @Jeet** — should the item record say which currency its averages are in? An item priced in
  USD in an INR business holds a USD price and an INR average, unlabelled. Default: not in this
  task.

**Tests** — 66 cases in the attached file.

- Rate resolution across all four rules and both entry paths, plus transactions with no document —
  TC-A1 to TC-B4.
- Averages at item, warehouse and batch level, the opening average, an item priced in a different
  currency from its document, and exact unwinding on edit, delete, cancel and conversion rate
  correction — TC-C1 to TC-F2.
- Reports in one currency, the fallback that never drops a row, and a period spanning a currency
  change — TC-G1 to TC-G8.
- Filling on patch or reversal, and no conversion rate available — TC-H1 to TC-I5.
- Single-currency businesses unchanged, and edge cases — TC-J1 to TC-K7.
