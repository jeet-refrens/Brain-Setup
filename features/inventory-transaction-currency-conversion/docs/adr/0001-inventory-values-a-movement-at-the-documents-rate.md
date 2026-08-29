---
status: accepted
---

# Inventory values a stock movement at the source document's rate

An inventory movement in a foreign currency has to be converted into the business currency to feed
`avgCostPrice`/`avgSellingPrice` and every report. Until now the averaging engine fetched its own
live rate from riften, keyed on `transactionDate`, and never looked at the source document
(`serana/src/hooks/manage-inventory-stock.js:586-594`). We decided a movement must instead use the
rate stored on its source document — `conversionRates[businessCurrency]` — and fall back to a riften
lookup only when the document has no rate, or when there is no document at all.

## Considered options

- **The document's rate, riften as fallback.** Chosen.
- **Keep the live riften lookup and simply persist it.** Rejected: it writes down the disagreement
  rather than fixing it.
- **The document's rate strictly, no fallback.** Rejected: older foreign-currency documents and
  document-less movements would produce permanently unvalued rows.

## Why this is worth recording

A future reader will look at inventory reaching into a document field for a rate and reasonably ask
why it doesn't just call the FX service — that is the simpler-looking code, and it is what the code
did before. The answer is that the document's rate is **not always the market rate**. The submitted
rate is deliberately trusted: the form sends the rate for the document's own `invoiceDate`, or the
user's own override, and
`serana/src/hooks/update-invoice-with-biz-currency.js:31-33` only ever fills a *missing* rate — it
never overrides what was sent. That same rate produced the invoice total and the accounting voucher.
Calling the FX service independently means the same sale values one way on the invoice, the same way
in the ledger, and a third way in stock.

## Consequences

- Inventory now depends on a document field it did not previously read. A document carrying a bad
  rate produces a bad stock valuation. That is the intended coupling: the invoice is the source of
  truth for what the sale was worth.
- Editing the rate on a document must re-trigger the inventory path, or the first rate correction
  reintroduces the disagreement (decision D9).
- Reversals must reuse the rate stored on the row rather than re-resolving it, or averages stop
  unwinding exactly (decision D8).
