---
status: accepted
---

# Store the rate on a stock movement, not the converted price

Accounting's house pattern puts both sides of a conversion on every ledger leg: `amount`/`currency`
alongside `book_amount`/`book_currency`, with the `forex_rate` that links them
(`saturn.lineitems`). We deliberately did **not** mirror that on `inventorytransactions`. A movement
stores `conversionRate` and `bookCurrency` only. `costPrice` and `sellingPrice` stay in the transaction
currency, and anything that wants a business-currency figure multiplies.

## Why this is worth recording

Someone comparing the two modules will see inventory storing half of what accounting stores and
assume it is an oversight to be tidied up. It is not. Three reasons:

1. **Converted prices do not scale with price fields.** `features/inventory-net-price-on-transactions/`
   is adding `netCostPrice`/`netSellingPrice` to this same row. A book variant of every price field
   means eight price fields to keep in sync instead of four, and the next price field makes it
   twelve. One rate converts all of them, now and later.
2. **Accounting's reason does not transfer.** `book_amount` is an integer in minor units on a
   **total**. Rounding has to be fixed once at write time or two reports disagree by paise.
   Inventory stores **unit prices** as floats, which are then multiplied by quantity and averaged.
   Rounding a converted unit price would introduce error rather than remove it.
3. **A stored derived value drifts.** Any patch that changes `costPrice` without recomputing its
   book twin leaves the row quietly self-contradictory. A rate cannot drift from itself.

## Consequences

- Every reader of a price on this row must multiply by `conversionRate`. That obligation is real, and it
  is the reason the report paths are fixed in the same task rather than deferred.
- The two Mongo `$group` report paths that currently sum unconverted prices become fixable —
  `$multiply` by a stored field works inside a pipeline, which is precisely what was impossible
  before.
- `bookCurrency` is stored even though it is usually the business's current currency, because a
  business can change its base currency. Without it, a currency switch silently reinterprets every
  historical row.
