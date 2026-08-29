# Code findings — read before drafting

Read from live source on 2026-08-17 via the GitHub REST API. Every claim below carries a
`file:line`. Where this disagrees with `docs/modules/...`, the code wins.

## F1 — The transaction stores a currency but no rate

`talos/src/inventorytransactions.js:20-23` has `currency` (String, enum from
`fence/currencies/index.json`). `costPrice` and `sellingPrice` (`:29-30`) are amounts **in that
currency**. There is no rate field and no business-currency amount field.

The module doc's curated field list left `currency` out. It is there. Jeet's read is right: the row
knows *which* currency, never *what it was worth*.

The schema is `strict: 'throw'` (`:135`), so a new field needs a real schema change. `params`
(Mixed, `:82`) and `lineItem` (ObjectId, `:81`) already exist.

## F2 — Documents store the rate. They do not recompute it.

`talos/src/helpers/documentCommonFields.js:787-808` — every document carries `currency` (String
enum) and `conversionRates` (Mixed), both editable by the client/vendor.

**Shape:** a map keyed by **business currency code** → rate. A USD invoice in an INR business holds
`conversionRates.INR = 83.2`. **Direction:** rate = business-currency units per 1 unit of document
currency, so `business amount = document amount × rate`. This follows from
`getCurrencyConversion(bizCurrency, currency, ...)` passing `base: currency` and
`currency: bizCurrency` (`serana/src/helpers/getCurrencyExchange.js:12-16`).

The rules, all in `serana/src/hooks/update-invoice-with-biz-currency.js`:

- **The submitted rate is trusted.** The form sends the rate for the document's own `invoiceDate`,
  or the user's deliberate override. The hook only fills a **missing** rate. Its own comment:
  "Only fill a MISSING rate here - never override what was sent." (`:31-33`)
- **Same currency means 1.** A cloned document that carried a foreign rate is stripped back to 1
  (`:16-25`).
- **A failed lookup is never stored.** `getCurrencyConversion` returns 0 on failure. The hook skips
  the write and raises Sentry instead, because storing 0 "silently makes the business-currency total
  zero" (`:44-51`).
- **Each money event carries its own rate at its own date** — payments (`:54-88`), credit claims
  (`:90-114`), wallet transactions (`:116-148`). One document, several rates.

`serana/src/hooks/update-conversion-rates.js:17-46` re-resolves the rate when the document currency
changes, then refreshes the business-currency totals.

## F3 — Inventory recomputes the rate live, and ignores the document's rate

`serana/src/hooks/manage-inventory-stock.js:586-594`:

```js
const { currency: businessCurrency = 'INR' } = businessRecord;
const exchangeRate = await getCurrencyConversion(
  businessCurrency, currency, transactionDate, context.app,
);
const priceFactor = exchangeRate || 1;
```

The document's `conversionRates` is never read here. Two consequences:

1. A user's deliberate rate override applies to the document and the books, and is **thrown away**
   for inventory.
2. The item average is converted at a market rate the document itself does not use. The same sale
   can value differently in the item average than on the invoice and in the ledger.

## F4 — When the rate lookup fails, the average silently uses 1

`getCurrencyExchange.js:20-27` returns **0** on a failed or non-ok lookup. Then
`priceFactor = exchangeRate || 1` (`manage-inventory-stock.js:594`) turns that 0 into **1** — a USD
price is added to an INR average as if 1 USD were 1 INR.

This is the exact failure the document hook refuses to allow (F2). Two paths, opposite guards, no
alert on the inventory side.

**Precision, from the same helper.** On success it returns `round(data.conversionRate, 6)` (`:22`), so
every rate is recorded to **six decimal places**. This is the precision PRD EC12 and TC-K6 depend on.

## F5 — The factor is applied on the way in and on the way out

`manage-inventory-stock.js:30-64` — `calculateAveragePrice` adds `price × qty × factor` forward and
subtracts `price × qty × factor` on reverse. The reverse uses the factor resolved **at reversal
time**, not the one used originally. Same `transactionDate` normally yields the same rate, so this
usually agrees — but if the lookup failed on one leg and not the other (F4), the average never
unwinds correctly. Nothing detects that.

## F6 — Reports are split, and the raw ones cannot convert

`serana/src/services/inventory-reports/class.js`:

- **Converting path:** `:110-163` calls `getCurrencyConversion` per transaction and multiplies
  before summing. One remote call per row; one report caches by
  `currency-currency-date` (`:962-968`).
- **Non-converting path:** `:846-856` sums `price × quantity` inside a **Mongo `$group`** with no
  conversion at all. Currencies are added straight together. This is the **Party transaction report**.

> **Corrected 2026-08-18.** An earlier version of this finding claimed **two** non-converting
> aggregations, citing `:530-537` as the second. That one belongs to the **Batch expiry report**,
> which aggregates the **`batches`** collection, not `inventorytransactions` (`:719-721`). It reads a
> batch's own `costPrice`, not a transaction's. Jeet caught this. See F15.

The remaining path cannot be fixed as written: a `$multiply` by the rate is impossible in the
pipeline **because the rate is not a field on the row**. One example is enough to settle
store-versus-recompute, and this is it.

## F7 — CORRECTED. The stored average **is** converted; only the response is stale.

> **This finding was wrong in its first version and is corrected here (2026-08-18).** Jeet tested it
> in product: an INR business, an item priced in USD with opening stock, and `avgCostPrice` came out
> in INR at the converted value. He is right. The original claim — that the average is seeded
> unconverted — does not hold.

What actually happens, in order:

1. `create-manual-inventory-transaction.js:22-38` builds a `MANUAL` transaction whose `currency` is
   the **item's** currency, and creates it.
2. That create fires `manageInventoryStock`, which resolves `priceFactor` and writes the
   **converted** average to Mongo via `_findOneAndUpdate` (`manage-inventory-stock.js:899-907`).
3. **Only then** does `create-manual-inventory-transaction.js:95, 187, 226` run
   `result.avgCostPrice = costPrice`.

Step 3 sits in an `alterItems` after-hook on `inventories` create
(`serana/src/services/inventories/inventories.hooks.js:191-195`). It mutates `context.result` and
nothing re-saves it, so it changes the **create response only**. The database already holds the
converted value.

**The real defect is much smaller.** The response to item-create reports an unconverted
`avgCostPrice`. A client that renders straight from that response shows a wrong number until it
refetches. That is a display bug, not data corruption.

## F12 — Three currencies meet on one item record, and only two are labelled

| Currency | Field | Set from | Labels |
|---|---|---|---|
| Business | `businesses.currency` | business setup | `avgCostPrice` / `avgSellingPrice` at item, warehouse and batch — **always, and never labelled** |
| Item | `inventories.currency` (`inventories.js:57-60`) | item creation, else the first document's currency. Never overwritten later — `invCurrency \|\| currency` (`onDocumentUpdate.js:367`) | `inventories.costPrice` / `sellingPrice`, and the keys of `currencyRates` / `costCurrencyRates` |
| Transaction | `inventorytransactions.currency` (`inventorytransactions.js:20-23`) | the **document's** currency for document-created rows (`onDocumentUpdate.js:493`); the **item's** currency for `MANUAL` rows (`create-manual-inventory-transaction.js:30`) | that row's `costPrice` / `sellingPrice` |

The document's currency always wins for a document-created row, even when it differs from the item's.
So an INR invoice against a USD item in an INR business produces a transaction in INR, `priceFactor`
of 1, and a correct average.

But the item record is then self-inconsistent, and nothing on it says so:

```
inventories.currency       USD
inventories.costPrice      100        <- USD
inventories.avgCostPrice   8300       <- INR, unlabelled
inventories.currencyRates  { USD: 100, INR: 8300 }
```

`onDocumentUpdate.js:456-462` writes `currencyRates[currency] = rate` using the **document's**
currency, so the map accumulates keys in currencies the item is not priced in. And
`onDocumentUpdate.js:445-451` only fills `costPrice`/`sellingPrice` when they are empty, so the
item's own price stays in its original currency for ever.

This is the gap Jeet's question exposes. It is not caused by the missing conversion rate, and storing
one does not fix it on its own — see PRD EC14 and OQ6.

## F8 — The item master already keeps prices per currency

`talos/src/inventories.js:57-73` — `currency`, plus `currencyRates` (Mixed, "last used price for
different currencies for sales transactions") and `costCurrencyRates` (the same for purchases).
`serana/src/helpers/onDocumentUpdate.js:456-462` writes `currencyRates[currency] = rate` on every
document.

But `avgSellingPrice` and `avgCostPrice` (`inventories.js:210-211`) are plain Numbers with no
currency label — implicitly business currency. One item document therefore holds prices under two
different currency conventions, and nothing marks which is which.

`serana/src/commands/fixinventorycurrencyrates.js` exists to repair rows where these maps got an
`undefined` key. So this area has already needed a repair pass once.

## F9 — The primary transaction builder is located

`serana/src/helpers/onDocumentUpdate.js:483-505` builds the transaction for the normal document
flow: `sellingPrice`/`costPrice` from the line's gross `rate`, `currency` from the document,
`transactionDate` from `invoiceDate`. **This closes open question 6 in
`features/inventory-net-price-on-transactions/`.**

`serana/src/hooks/manage-linked-document-inventory-transaction.js:18-42` is the converted/linked
equivalent. It falls back to `inventory.currency` when the document has none (`:27`); the primary
builder has no such fallback.

## F10 — A rate change alone does not re-trigger inventory

`onDocumentUpdate.js:10-30` lists the fields watched for change:

- `TXN_RELEVANT_DOC_FIELDS` = `invoiceDate`, `billType`, `isExpenditure`, `invoiceType`,
  **`currency`**, `client`, `vendor`
- `TXN_RELEVANT_ITEM_FIELDS` = `quantity`, **`rate`**, `gstRate`, `unit`, `warehouse`, `itemType`,
  `allocations`, `serials`, `batch`, `sku`

**`conversionRates` is in neither list.** Changing the document currency re-runs the inventory path;
editing only the rate does not. Whatever we store has to say what happens then.

## F11 — Every rate lookup is a network call to riften

`serana/src/services/conversion-rate/conversion-rate.service.js:14` proxies the `conversion-rate`
service to riften. So today each average computation, and each row of a converting report, makes a
remote call. Storing the rate removes that call from the read path.

## F13 — A warehouse transfer carries no price, and never touches an average

`serana/src/services/inventory-batch/class.js:1954-1985` builds the two transactions a transfer
creates. Both are explicit:

```
type: 'SELL'  (from)  /  type: 'BUY' (to)
sellingPrice: 0
costPrice: 0
transactionType: 'UPDATE'
docType: 'TRANSFERSTOCK'
params.transferStock: true
```

There is **no `currency` field at all**, and both prices are hard zeros.

`params.transferStock` then gates the averaging. In `manage-inventory-stock.js`, every call to
`adjustInventoryStock` is wrapped in `if (!transferStock)` — at item level (`:669`, `:735`) and at
batch level (`:637`, `:704`) — and `updateWarehouseData` receives the same flag and skips its own
average update on it (`:161`, `:177`).

So a transfer moves **quantity between warehouses and nothing else**. No price, no currency, no
average at any level.

**Consequence for this feature:** there is nothing to convert, so a transfer needs no conversion
rate. Adding one would be meaningless, and adding a price alongside it would be actively harmful —
it would start feeding averages that are deliberately untouched today. See D25.

**Pre-existing limitation, out of scope:** because a transfer carries no cost, moving stock from one
warehouse to another does not carry its cost basis with it. The destination warehouse's average cost
does not reflect the stock arriving. That is a real gap in per-warehouse valuation, it predates this
work, and nothing here changes it.

## F14 — Every consumer that reads a price off an inventory transaction

Enumerated by searching every reference to the `inventorytransactions` collection in `serana`
(24 hits) and checking each for price reads and currency handling.

### Must change

| Consumer | What it does today | Effect of this feature |
|---|---|---|
| `services/inventory-reports/class.js:846-856` — **Party transaction** | Sums `price × quantity` in a Mongo `$group` with **no conversion** — currencies added together | **Totals change materially.** A USD 100 line stops counting as 100. ⚠️ An earlier version of this row also cited `:530-537`; that is Batch expiry, which aggregates `batches` and reads no transaction. See F15. |
| `services/inventory-reports/class.js:110-163`, cache `:962-968` | Live `getCurrencyConversion` per row, then multiplies | Same figures except where a user overrode a document rate; loses one network call per row |
| `hooks/get-sales-client-transactions.js:39-81` | Live lookup per row; `sellingPrice × quantity × exchangeRate`, plus a GST-inclusive figure built on the same rate | Same, and both figures inherit it |
| `services/api/inventory-transactions/inventory-transactions-api.class.js:224-227` | Returns `currency`, `costPrice`, `sellingPrice` — **no rate** | Additive: must also expose the rate and book currency, or an API consumer cannot convert what it receives |
| `services/inventory-batch/class.js:77-79`, `:158-160` | Batch listing / CSV export carries currency and prices, no rate | Additive, same reasoning |

### Must change, and it is not a report — the highest-risk item in this feature

**`commands/crons/integrity/inventorystockintegrity.js` is a second, independent implementation of
the averaging maths.** It recomputes `avgCostPrice` and `avgSellingPrice` at item, warehouse, batch
and batch-warehouse level (`:60-184`) using:

- its own `getCurrencyConversion` call (`:60`),
- its own `const priceFactor = quantity * (exchangeRate || 1)` (`:66`) — **the same silent
  rate-of-1 bug as F4**,

and then **writes the result back**: `app.service('inventories')._patch(inventoryId, payload)`
(`:426`) and the batch equivalent (`:381`), both gated only by `dryrun`.

Two consequences:

1. If the live path is fixed and this is not, **the cron overwrites corrected averages with
   market-rate values on its next run.** The feature would silently undo itself.
2. The `|| 1` corruption can already reach stored averages through this path today, independently of
   `manage-inventory-stock.js`.

It must apply the same rule as the live path: use the rate stored on the transaction, and never
substitute `1`.

### Checked and not affected

- `services/invoice-reports/class.js` and `services/expenditures-reports/expenditures.class.js` —
  both surface in a text search, but neither queries `inventorytransactions`. Their currency handling
  is over `invoices`.
- `services/profile-reports/class.js` — does not query the collection at all.

## F15 — The six inventory reports, by their on-screen names

> **Rewritten 2026-08-18.** The first version of this table was wrong about **Batch expiry** and
> **Stock value**. It inferred each report's data source from the field names in its pipeline instead
> of checking which collection the pipeline actually queries. Both read an **item or batch** price,
> not a transaction price, so neither is affected by this feature. Jeet caught it.

Mapped from `serana/src/services/inventory-reports/class.js`, checking the **source collection** of
each report, not just its field names.

### Affected — these read a price off an inventory transaction

| On-screen report | Source | Today | Impact |
|---|---|---|---|
| **Party transaction** | `runReportsAgg(..., 'inventory-transactions')` (`:888`) | `$group` sums `price × quantity`, **no conversion** (`:846-856`) | **The only report whose numbers visibly change.** `totalAmount` and the derived `avgUnitPrice` are currency-mixed today. |
| **Product wise P&L** | `inventory-transactions._find` (`:58`) | Converts per row with a live lookup (`:110-163`) | **Small.** Moves only where a user overrode a document rate. `avgCostPrice`, `avgSellingPrice`, `avgLandedCost` and `grossProfitMargin` (`:176-186`) inherit it. Loses one remote call per row. |
| **All transaction** | `inventory-transactions._find` (`:1290`) | A listing. Each row carries its own `currency` and `price` (`:1199-1200`). No totals | **Additive only.** No existing number changes; it gains the rate so a foreign row's worth is visible. |

### Not affected — these read an item or batch price

| On-screen report | Source | Why it is untouched |
|---|---|---|
| **Stock value** | `inventories._find` (`:957`) | Values stock at the **item's** `costPrice`, converted from the **item's** currency via `getCachedCurrencyConversion` (`:1014-1019`). No transaction is read. |
| **Batch expiry** | `batches` model aggregate (`:719-721`) | Sums `quantity × costPrice` from the **batch**, falling back to the **item** (`:530-537`). No transaction is read. |
| **Stock status** | — | Never reads a price. Quantities and thresholds only. |

Also not affected, none read a price: `inventoryTransactionsSummary` (`:1601`),
`inventoryTransactionsGraph` (`:1681`), `batchSummary` (`:1827`).

### A separate gap this exposed — not fixed here

**Batch expiry mixes currencies too, for an entirely different reason.** `batches` has no `currency`
field at all, so a batch's `costPrice` is implicitly in its item's currency. The report sums those
across items with **no conversion**. For a business with items priced in different currencies, the
value per expiry bin is currency-mixed.

Same symptom as the transaction problem, different root cause: this is the **item-price** currency
gap (F12), and storing a rate on transactions does nothing for it. It belongs with **OQ6**, not with
this task.

## F16 — `IGNORE` rows carry prices, are listed in a report, and change type over time

Three facts that together settle whether the rate belongs on non-stock-moving rows.

**1. Price and currency are already written on every row, whatever the stock effect.**
`onDocumentUpdate.js:483-505` builds one payload carrying `costPrice`, `sellingPrice`, `currency`
**and** `transactionType` together. `transactionType` is resolved separately at `:385-429` and can
land on `IGNORE` for an unmanaged item, an ignored document type, or a business with inventory off.
Nothing gates the price fields on it.

**2. The All transaction report lists `IGNORE` rows.** Of the three reports that read transactions:

- `salesReport` filters `transactionType: ['UPDATE']` (`:34`)
- `partyTransactionsReport` filters `transactionType: 'UPDATE'` (`:831`)
- `inventoryTransactionsReport` filters **nothing** — it selects `transactionType` as an output
  field (`:1262`) and returns every row (`:1290`)

So an `IGNORE` row appears on screen with a foreign price and, without a rate, no way to convert it.

**3. A row's `transactionType` changes over its life.**

- `BLOCK` → `BLOCK_IGNORE` when a reserved document is converted
- anything → `IGNORE` when a row is soft-removed (`onDocumentUpdate.js:86` patches
  `{ transactionType: 'IGNORE' }`)
- a change to the document's `advanceOptions.manageInventory` re-runs the whole inventory effect,
  which can move a row in either direction

The averaging gate itself is `['BLOCK', 'UPDATE'].includes(transactionFlag)`
(`manage-inventory-stock.js:702`) and is unchanged by this feature.

**Consequence:** a rate stored only on stock-moving rows would disappear exactly when a reversal
needs it — a `BLOCK` row demoted to `BLOCK_IGNORE` still has to unwind at its original rate (D8).
Store it on every row. See D27.

## F17 — A package item creates a transaction for the parent **and** one per child

`serana/src/hooks/manage-group-inventory-childitems.js` is an **after-hook on inventory-transaction
create**. When the item on the document `isPackage` and has `items[]`, it creates one further
transaction per child (`:180-215`).

**The child payload is an explicit allow-list copied from the parent transaction** (`:183-198`):

```
type, docId, docType, transactionDate, currency, gstRate, client, action,
modifiedBy, reason, group: <parent inventory id>, transactionType, lineItem,
params, warehouse
```

Child `costPrice`/`sellingPrice` are computed per child and passed in separately (`:20-21`), so a
child carries **its own price but the parent's `currency`**.

**Two consequences for this feature:**

1. Because the currency is inherited, the **same conversion rate applies to the parent and to every
   child**. There is nothing extra to resolve — the rate follows from the currency and the
   document, which are identical across the set.
2. **The allow-list is the trap.** `conversionRate` and `bookCurrency` must be added to it. If the
   new fields are added to the transaction schema and the builders but not to this list, **every
   package child transaction is written without a rate** — silently, and only for businesses that
   use package items.

Note also that `adjustInventoryStock` skips `isPackage` items, and packages never move
`stockInHand`. That does not change the rule: per D27 the rate is stored on every transaction
whatever its stock effect.
