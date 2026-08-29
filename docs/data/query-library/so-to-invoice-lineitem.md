# Sales order to invoice, line item wise

**Question:** for one business, how much of each sales order line is invoiced, and how
much is still open?

**Database:** 2 `refrens` (MongoDB) · **Collection:** `invoices`
**Live in Metabase:** question **5017**, `[BEP] Order Management`, root collection
**Query:** [so-to-invoice-lineitem.json](so-to-invoice-lineitem.json)
**To paste into Metabase:** [so-to-invoice-lineitem.paste.json](so-to-invoice-lineitem.paste.json)
**Built for business:** `6a8444b1b7fa0c0025af333e` ("Test Report")
**Last verified:** 25 August 2026

## Run it

```bash
python scripts/mb.py run --db 2 --file docs/data/query-library/so-to-invoice-lineitem.json --collection invoices
```

To point at another business, change the `ObjectId` in **two** places: the opening
`$match`, and the `businessconfigurations` sub-pipeline that resolves tag names.

## Two copies of the same query

| File | Shape | Use it for |
|------|-------|------------|
| `so-to-invoice-lineitem.json` | 1,043 lines, indented | reading and editing |
| `so-to-invoice-lineitem.paste.json` | **one line, 6.4 KB** | pasting into Metabase |

Both are copied from live card 5017. Paste the one-line copy. A 1,043-line paste that arrives
truncated fails with a JSON error pointing at whatever key sits at the cut, which reads
like a bug in the query and is not one.

In Metabase: new question, Native query, database `refrens`, collection `invoices`,
then paste. Select all in the editor and replace, rather than pasting into whatever is
already there.

## What it does

One row per sales order **line item**. A sales order with 5 lines gives 5 rows. So the
same sales order number shows up more than once. That is on purpose.

It follows the live **order management report**:

- Backend: `serana/src/services/order-management/order-management.class.js`
- Line item matching: `lydia/src/pages/app/[business]/reports/order-management.tsx`,
  in `renderRowSubComponent`

Source documents are `billType: "SALESORDER"` owned by the business. Drafts, cancelled
and deleted documents are left out. Invoices are found through `linkedDocuments` **and**
`linkedInvoices`, then cut down to `billType: "INVOICE"`. Both lists are needed. Many
sales orders keep the invoice in `linkedDocuments` only.

## How the live report matches line items

The backend does **no** line matching. It only compares `totals.total` of the order
against the sum of `totals.total` of the linked documents. It ships both `items` arrays
to the browser and lets the frontend do the rest.

The frontend builds a map keyed on **`items[].inventory`**, the `inventories` id:

```js
acc[docItem.inventory] = (acc[docItem.inventory] || 0) + (docItem.quantity || 0);
```

This query uses the same key. Three deliberate differences are listed below.

## Columns

| # | Column | Where it comes from |
|---|--------|---------------------|
| 1 | SO Number | `invoiceNumber` |
| 2 | SO Date | `invoiceDate` |
| 3 | Custom PO No | `vendorFields.r_str_001` |
| 4 | PO Date | `vendorFields.r_date_001` |
| 5 | Customer UniqueKey | `clients.uniqueKey`, joined on `invoices.client` |
| 6 | Customer Name | `billedTo.name` |
| 7 | Customer State | `billedTo.state` |
| 8 | Customer GSTIN | `billedTo.gstin` |
| 9 | Sales Person | `vendorFields.r_str_002` |
| 10 | Tags | `tags[]`, resolved through `businessconfigurations.labels` |
| 11 | Currency | `currency` |
| 12 | Category | `inventories.vendorFields.r_str_001`, joined on `items[].inventory` |
| 13 | SKU | `items[].sku` |
| 14 | Item Name | `items[].name` |
| 15 | Qty | `items[].quantity` |
| 16 | Unit | `items[].unit` |
| 17 | Rate | `items[].rate` |
| 18 | Discount % | from `items[].discount` |
| 19 | Discount Amount | from `items[].discount` |
| 20 | Gross Value | `items[].amount` |
| 21 | Tax Value | `items[].igst` |
| 22 | Total Value | `items[].total` |
| 23–26 | The same four, summed over the linked invoices | |
| 27–30 | Order minus invoiced | |
| 31 | Estimate | `vendorFields.r_num_001` |

**Customer UniqueKey** is the client's unique key, read **live from the `clients`
collection**. See [The Customer UniqueKey column](#the-customer-uniquekey-column) for why
it is not read off the document.
**Customer Name** is the name as typed onto that document, so it can drift between
documents for the same client.

**Customer State** is `billedTo.state`, the state name, e.g. `Maharashtra`. It is not
the GST state code. That is `billedTo.gstState`, a two-digit code such as `27`, and it is
not in the report.

**Customer GSTIN is empty for this business today.** The field is read correctly. None
of its clients has a GSTIN saved. The column fills itself once one does. Unlike Customer
UniqueKey, it is still read off the document snapshot, so it can drift the same way.

**Gross Value is after the line discount** (`items[].amount`). So Gross + Tax = Total,
and the columns add up.

**Discount.** `items[].discount` holds a type and an amount. When the type is
`PERCENTAGE`, the amount is the percent, and the money value is worked out from
`subTotal`. When the type is `FIXED_AMOUNT`, the amount is the money, and the percent is
worked out instead. Both columns are always filled.

## The private custom field columns

`vendorFields` on the document is what the team calls **private custom fields**. It is a
flat key-value object, read straight off the sales order:

```
{ "r_str_001": "23445657/01", "r_str_002": "Nale Renuka R",
  "r_date_001": "2026-08-23T18:30:00.000Z", "r_num_001": 26231 }
```

**The key-to-label mapping is per business.** `r_str_001` means "Custom PO No" for
business `6a8444b1b7fa0c0025af333e` and can mean something else for anyone else. Recheck
the labels before pointing this query at another business.

**`r_date_001` is stored as a string, not a BSON date.** The query converts it with
`$convert ... to: "date"`, so Metabase can filter and format it. A bad or missing value
gives `null` instead of failing the whole query.

That stored value is IST midnight, the same convention `invoiceDate` uses. So
`2026-08-23T18:30:00.000Z` is **24 August 2026**. PO Date and SO Date shift together in
whatever timezone Metabase renders. If PO Date looks a day out, this is why.

## The Customer UniqueKey column

**Read the unique key from `clients`, not from `billedTo.uniqueKey` on the document.**

`billedTo` is a snapshot copied onto the document when it was created. When someone edits
a client's unique key in the client dashboard, old documents are not updated. Worse, the
value is **removed** from them, so the column goes blank.

This is not hypothetical. It was reproduced on this business on 25 August 2026. The keys
had been edited from numbers to names. A00002 and A00003 carried the new names, and
A00001 carried **nothing at all**, though it is the same client as A00004.

The query joins `invoices.client` to `clients._id` and reads `uniqueKey` from there. It
falls back to `billedTo.uniqueKey` when no client row comes back, so the join can only
add values, never remove them.

### Coverage

Over 8,933 sales orders (May to Aug 2026), **100%** have `client` set, and only **70%**
have `billedTo.uniqueKey`. At line level, over 27,973 rows:

| Where the value comes from | Rows |
|----------------------------|------|
| Already on the document | 20,073 |
| Blank on the document, **recovered from `clients`** | 2,090 |
| Blank: the client exists but has no `uniqueKey` set | 5,810 |
| Client row not found | **0** |

So the join fixes 2,090 rows and loses none. The 5,810 that stay blank are clients with
no unique key saved at all. No query can fill those.

### Cost

Nothing measurable. `clients._id` is indexed, so it is a point lookup, and it runs once
per sales order because it sits before the `$unwind`. Alternating runs over 1,335 rows:

| | Runs | Median |
|---|------|--------|
| Without the `clients` join | 464, 458, 504 ms | 464 ms |
| With it | 495, 382, 510 ms | **495 ms** |

The difference is inside the noise. Four `$lookup` stages is not the thing that would
make this query heavy. Joining once per **line** instead of once per **order** would be.

### Filtering on it later

Yes. A saved native question can be used as the source for a normal GUI question, and
every returned column can then be filtered, grouped and summarised. Confirmed against
card 5017 on 25 August 2026:

- filter `Customer UniqueKey = "TATA Mot-Pune"` returns 6 rows, which is A00001 and
  A00004, three line items each
- group by `Customer UniqueKey`, summing Total Value, returns one row per customer
- filter on `SO Number` also works

Metabase types `Customer UniqueKey` as `type/Text`, so it filters as text. Note that a GUI filter
runs **after** the pipeline, on its output. It does not narrow the `$match`, so it does
not make the query cheaper.

## The Tags column

`invoices.tags` holds label **ids**, not names, e.g. `["7ub2dCJn1ir5AEtGDu1mc"]`. The
names live in one place per business: `businessconfigurations.labels`, an array of
`{ _id, name, color, isArchived }`. A document can carry more than one, so the column
joins them with `, `.

**The `$lookup` is deliberately uncorrelated.** It has a `pipeline` only, with the
business id written into its own `$match`. It has no `localField` / `foreignField` and
no `let`. MongoDB runs an uncorrelated sub-pipeline **once** and caches it for every
input document.

That matters. The correlated version, joining `invoices.owner` to
`businessconfigurations.business`, works and needs no hardcoded id, but it re-reads a
1,405-field configuration document for every sales order:

| Shape | 1,331 rows |
|-------|-----------|
| Uncorrelated, business id in the sub-pipeline | **458 ms** |
| Correlated on `owner` → `business` | 1,528 ms |

**So the business id now appears in two places.** The opening `$match`, and the
`businessconfigurations` sub-pipeline. **Changing the business means changing both.**
Change only the first and the report silently shows another business's tag names, or
none.

Tag names are resolved whether or not the label is archived. An id with no matching
label falls back to showing the raw id, so a deleted label is visible rather than blank.

## The Category column

SKU comes straight off the line item. Category does not live on the document at all. It
is fetched with its own `$lookup` into **`inventories`**, joined on
`items[].inventory`.

That lookup runs **once per sales order**, before the `$unwind`, on the pre-collected
list of inventory ids. It uses the `_id` index. Do not move it after the `$unwind`.

**Category is `inventories.vendorFields.r_str_001`, not `inventories.category`.**

`inventories.category` is the built-in field, a 16-value enum from
`fence/inventory/categories.json`. It looks like the right source and is **empty**:
null on this business's items, and typed all-null by Metabase's own field index across
its whole sample. Nobody fills it in.

What this business actually uses is a **private custom field on the inventory item**:
`vendorFields.r_str_001`, holding free text such as `Finished Product`. Same
`vendorFields` shape as on documents, different entity, so the key means something else
here. On a document `r_str_001` is Custom PO No. On an inventory item it is the
category. **Two different meanings for one key name.** Check the entity before reading a
private custom field.

Because it is free text, the value is printed as stored. There is no enum, so there is
no key-to-label mapping. An earlier version carried a 16-entry `$literal` map for
`inventories.category`; dropping it took the query from 6.8 KB to 6.2 KB.

## The join key: use `inventory`, not `items._id`

`items[]._id` survives a conversion, so it looks like a valid link. It is not. It is a
Mongo subdocument id, and nothing guarantees it is carried across.

Measured on 289 converted sales orders with 1,274 invoice line items (May to Aug 2026).
The count is how many invoice lines find a match on their source order:

| Key | Matched | Missed |
|-----|---------|--------|
| `sku` | 1,267 (99.5%) | 7 |
| **`inventory`** | 1,264 (99.2%) | 10 |
| `name`, or `sku` + `name` | 1,253 (98.4%) | 21 |
| `items._id` | 1,214 (95.3%) | 60 |
| `items._id` + `name` | 1,202 (94.3%) | 72 |

`items._id` is the **worst** of the six. A missed match is silent. It understates
invoiced quantity and overstates the balance, which is the whole point of the report.

`sku` scores 3 lines higher than `inventory` out of 1,274. That is not enough to justify
disagreeing with the live report. `sku` is also free text a user can retype. So the key
is `inventory`, falling back to `sku`, then to `name`, for the 0.15% of lines that carry
no inventory id.

`items[].params.linkedLineItemId` is set in
`serana/src/services/my-clone-invoice/clone-invoice.class.js`. It would be the correct
key. It is **empty in production**. Six real converted documents were checked. Zero had
it. Recheck before building on it.

## Where this differs from the live report

**1. Repeated items are split, not double counted.** Say one order has two lines of the
same item. The live report shows the **combined** invoiced quantity on **both** rows.
This query splits the invoiced amount across those lines in proportion to ordered
quantity. Two lines of 10 and 30, with 20 invoiced, get 5 and 15. The order total stays
right. This affects about 6.6% of orders. The test business is one of them. All three of
its lines are the same item.

**2. Draft invoices are excluded.** The live frontend filters only `CANCELED`, so a
DRAFT invoice adds to its line quantities. The backend excludes DRAFT from the
document-level amount. The live report disagrees with itself. This query excludes DRAFT
everywhere.

**3. Lines with no inventory id are kept.** The live report skips them
(`if (docItem.inventory)`). This query falls back to `sku`, then `name`.

## Watch out for

- **Negative balances are real.** Across all businesses, 160 of 27,070 rows (0.6%) show
  more invoiced than ordered. Checked by hand: orders converted to two invoices, and
  invoices billing more than ordered. `A00612` ordered 1 and invoiced 100, with one
  invoice and one match. Do not clamp these to zero. The report is right. The data is
  like that.
- **Chained conversions are missed.** Say the path is order, then delivery challan, then
  invoice. The invoice is usually not in the order's `linkedDocuments`. So its quantity
  never shows up. The live report has the same gap.
- **One invoice covering several orders.** Its lines count in full against each order it
  is linked to. No field in the data says how much of a line belongs to which order.
  `params.linkedLineItemId` was meant to solve this, and it is empty.
- **Other currencies.** An invoice in a different currency is converted with
  `conversionRates[<order currency>]` off the invoice. If that rate is missing, the query
  falls back to 1. That is wrong, and it is silent. A MongoDB pipeline cannot fetch a
  live rate.
- **Additional charge lines are kept** (`isAdditionalCharge: true`). They are rows here
  because they are rows in the document.
- **`igst` is the whole tax.** `cgst` and `sgst` are its split halves, not extra tax.
  `total` = `amount` + `igst`. Summing all three doubles the tax.
- **Grouping rows are dropped.** Lines with `group: true` are section headers.
- **The `$limit` is 5,000 rows.** Raise it for a bigger business, or add an
  `invoiceDate` filter.
- **A `$project` output column name must not contain a dot.** MongoDB reads it as a
  field path and fails with `FieldPath must not end with a '.'`. That is why the column
  is `Custom PO No`, with no full stop.

## Cost

| Scope | Rows | Time |
|-------|------|------|
| Test business, 4 orders | 10 | 380 ms via the saved card |
| One real business, 117 orders | 1,331 | 458 ms |
| Every business, May to Aug 2026 (before the Category join) | 27,070 | 5.4 s |

Three things keep it cheap:

- The opening `$match` is on `owner` and `billType`. Both are indexed.
- The `invoices`, `inventories` and `clients` joins use `localField` / `foreignField`,
  so they use the `_id` index.
- The `businessconfigurations` join is uncorrelated, so it runs once for the whole query.
- Every `$lookup` runs before the `$unwind`, so each join happens once per order, not
  once per line.

**Do not rewrite the `$lookup` as `$expr: { $in: ["$_id", "$$ids"] }`.** That form does
not use the index. It scans the whole collection once per sales order. The same query
went from **878 ms to over 150 seconds**, and had to be killed.

## Result on 25 August 2026

Business `6a8444b1b7fa0c0025af333e` now has 4 sales orders and 10 line items, and **one
of them has been invoiced**. A00003 reports Invoiced Qty 12 against Qty 12, Qty Balance
0, and Invoiced Total Value 21,240 against Total Value 21,240. A00001, A00002 and A00004
are still open and report 0 invoiced.

So the conversion matching is confirmed end to end on this business, not only on the
other business it was originally measured against.

Match quality on a real business (`65929a55e8c8f1004053f928`, 1,331 lines):

| Line state | On `inventory` | On `items._id` + `name` |
|------------|---------------|------------------------|
| Fully invoiced | 1,186 | 1,179 |
| Not invoiced | 141 | 149 |
| Part invoiced | 4 | 3 |
| More invoiced than ordered | 0 | 0 |
