# Learnings

Dated log of mistakes, surprises, and things that cost time. Newest first.

Add an entry when:

- a query was wrong
- a guardrail fired, for a good reason or a bad one
- a field did not mean what its name suggested
- anything took longer than it should have

When a learning becomes a permanent fact, move it to where it belongs.
[verified/](verified/) for fields. [join-map.md](join-map.md) for links.
[guardrails.md](guardrails.md) for rules. `scripts/mb.py` for anything a machine can
enforce.

---

## 20 August 2026 — building the activation model

**Four fields look like a conversion date. None of them is one.**

- `subscriptions.createdAt` and `subscriptions.startDate` are the **signup** date.
  Checked against the business `_id` ObjectId timestamp on 6 businesses. They match to
  the second or the minute.
- `premium.trialActivatedAt` is also signup. It matches the business ObjectId time exactly.
- `premium.trialEndedAt` is **trial expiry**, not payment. It came before the first
  payment in 574 of 574 cases. Median gap 11.7 days, p90 66 days. It is missing for
  39.8% of converters.
- There is no `premiumStartDate`. Not on `businesses`, not anywhere in db 2 or db 4.
  Checked the field index and dumped every root key matching `premium|start` on live docs.

The conversion moment lives in two places. They agree to within 8 seconds:

1. `subscriptions.recurrences[]`, the element whose `activationType` is `PAYMENT`,
   `PAYMENT_RC` or `PAYMENT_MANUAL`. Use that element's `createdAt`.
2. The paid invoice's `createdAt`.

Prefer `recurrences`. It is one collection and the filter fields are indexed.

**`premium.enabled: true` does not mean paid.** Take the 59,754 businesses created Mar to
May 2026. Of those, 48,127 carry `premium.enabled: true` and `premium.onTrial: true`.
None of them has a `premium.endDate` at all. That is an auto-trial that never expires.
Reading `premium.enabled` as paid overstates customers by roughly 50x.

Paid definitions scored against "has at least one paid invoice", on 63,605 businesses
created Jan to Mar 2026:

| Definition | Found | Recall | Extra |
|---|---|---|---|
| `premium.enabled: true` and `onTrial != true` | 963 | 92.7% | 8.3% |
| `subscriptions.activationType` in PAYMENT / PAYMENT_RC / PAYMENT_MANUAL | 980 | 97.6% | 5.1% |
| `premium.paymentActivated: true` | 1,041 | 99.9% | 8.5% |
| At least one paid invoice | 953 | 100% | - |

`premium.enabled: true` and `onTrial != true` answers **who is paying today**. It drops
businesses that paid and then lapsed. 68 of its 70 misses were exactly that. The miss
grows as a cohort ages. So never use it to compare cohorts of different ages.

`premium.paymentActivated: true` answers **who ever paid**. Use it for cohort work. It is
not indexed, but it is safe next to an indexed `createdAt` match.

**`businessacquisitions.createdAt` is not the business creation date.** July 2026 holds
64,459 rows against about 17,000 new businesses. Anchor every cohort on
`businesses.createdAt`.

**`featureUsage.firstUsedAt` starts on 12 June 2026.** That is the earliest value anywhere.
6,475 rows carry `backfilledByCommand: true`. So `usedInLifetime` works as a boolean.
`firstUsedAt` only tells the truth for a first use after 12 June 2026.

**`featureUsage.expenses` under-reports.** It showed 354 businesses. Counting expense
documents directly showed 1,117 businesses in 30 days. The feature is new and the tracker
is behind. Count expenses on `invoices` with `isExpenditure: true`. Expenses are
`billType: INVOICE`, not their own `billType`.

**`VIEW_premium_paid_invoice.invoiceDate` carries a fake time.** The times run 00:00:29,
00:00:30, 00:00:31 in invoice-number order. The day is right. The time is generated. For
real timing, join on `_id` back to `invoices.createdAt`.

**Querying `recurrences` is cheap if you filter first.**

- `clientBusiness` and `createdAt` are both indexed on `subscriptions`.
- The array holds 2 to 3 elements, so `$unwind` roughly doubles the rows.
- A cohort query over 55,659 subscriptions ran in 336 ms.
- For one flag per business, skip `$unwind`. Use `$filter` inside `$addFields`. That ran
  in 335 ms over the same cohort.
- Never `$unwind` before the opening `$match`.

**`recurrences[].reason` records which paywall the user hit.** 62 values, including
`AUTO_TRIAL_INVOICE`, `AUTO_TRIAL_QUOTATION`, `Sidebar`, `Book Keeping`, `Inventory` and
`Gst Lookup`. It is known on day one for every business.

---

## 19 August 2026 — first questions run through the setup

**`businesses.country` holds ISO two-letter codes.** `IN`, `US`, `PK`, `MY`, `AE` and
so on. Not country names. Filtering on `"India"` would return zero rows, which reads
like a real answer. Recorded in [verified/refrens-mongo.md](verified/refrens-mongo.md).

**The old dump was stale, and the drift was large.** `_tmp_mb2.json` said `invoices`
had 911 field paths. The live sync says **1,169**. `leads` moved from 323 to 260.
Numbers taken from a cached dump need the sync date attached, or they quietly go
wrong.

---

## 19 August 2026 — setting this up

**The API key cannot write to the intended collection.** The key in `.env` acts as
user *Jeet, id 109, not an admin*. It has no personal collection, and collection 56
returns 403. It can only write to `root`, `70` and `134`. Until a key from the right
account exists, always ask before saving a question. See
[metabase-map.md](metabase-map.md).

**Metabase records which Mongo fields are indexed.** `database_indexed` is populated
for db 2: 304 indexed fields out of 12,781. This is what makes the "your filter must
hit an index" guardrail real rather than a guess. It is also true for Saturn, where it
showed that only `id` and `business` are indexed.

**`ObjectId(...)` and `ISODate(...)` are not valid JSON.** The house style, and the
Metabase editor, both accept them. A validator that runs `json.loads` rejects your own
working queries. `scripts/mb.py` now converts them to extended JSON to check the
query, then converts them back before sending.

**Azure resets connections in front of Metabase.** `POST /api/dataset` failed with
WinError 10054 roughly one call in three, while the same request through `curl`
worked. It was not the user agent. `scripts/mb.py` retries three times with backoff.
If a call fails once, retry before believing it.

**Metadata endpoints are slow.** `GET /api/database/10/metadata` timed out at two
minutes. db 2 returns about 15 MB. This is why the field index is cached locally and
not fetched per question.

**Saturn is not sharded.** The Citus extension is installed, so it looks distributed,
but `public.citus_tables` returns zero rows. Earlier notes claiming Citus sharding
were wrong. Treat it as plain Postgres.

**The first probe was useless.** It dumped five whole documents, which for `invoices`
is a wall of 100+ columns. Counting the documents the opening `$match` selects is the
number that actually tells you the cost. Changed.

**A stale metadata dump was sitting at the repo root.** `_tmp_mb2.json`, 15 MB,
untracked and unnamed. It is now generated properly into `docs/data/cache/`.

**Unrelated but important:** the Metabase API key is written out in plain text inside
about eight permission rules in `.claude/settings.local.json`. It should be rotated
and those rules rewritten so they do not contain it.

## 19 August 2026 — days for Refrens counts are cut on IST, not UTC

Counting businesses created "in the last 7 days including today" on UTC day
boundaries splits every Indian evening across two days. About 74% of new businesses
are Indian, so the daily numbers come out wrong in a way that is hard to see.

Fix: group with `"timezone": "Asia/Kolkata"` in `$dateToString`, and write the start
of an IST day as `T18:30:00Z` on the day before.

Also confirmed the same day:

- `businesses.isHardRemoved` exists but is **not indexed**. It is safe to add to a
  `$match` next to `createdAt` and `isRemoved`, which are.
- A `$facet` passes the guardrails and gives the total, the daily split and the
  country split in one pass over the same matched set. Cheaper than three queries.
- `businesses` runs about **4,000 new rows a week** (19 Aug 2026). Small. A month or
  a quarter is fine to query directly.

## 20 August 2026 — matching document line items across a conversion

Building the line item wise sales order to invoice report
([query-library/so-to-invoice-lineitem](query-library/so-to-invoice-lineitem.md))
turned up four things worth keeping.

**`$lookup` with `$expr: { $in: ["$_id", "$$ids"] }` does not use the `_id` index.**
It scans the whole `invoices` collection once per source document. The same query took
**878 ms** with `localField` / `foreignField` and **over 150 seconds** with `$expr`.
Use the concise correlated form: `localField` + `foreignField` + `let` + `pipeline`.
It uses the index and still lets the sub-pipeline filter.

**Match document line items across a conversion on `items[].inventory`, not `items._id`.**
`items._id` does survive a conversion often enough to look right, which is the trap. It
is a Mongo subdocument id, and nothing guarantees it is carried. Measured on 289
converted sales orders and 1,274 invoice line items, counting invoice lines that find a
match on their source order: `sku` 99.5%, **`inventory` 99.2%**, `name` 98.4%,
`items._id` 95.3%, `items._id` + `name` 94.3%. `items._id` is the worst of the six. A
missed match is silent, and it overstates the open balance.

`inventory` is also what the live order management report uses. The matching is **in the
frontend**, not the backend: `lydia/src/pages/app/[business]/reports/order-management.tsx`,
in `renderRowSubComponent`. The backend only compares `totals.total` at document level
and ships both `items` arrays to the browser. Look there before assuming a report has no
line-item logic.

That frontend map is keyed on `inventory` alone, so an order with two lines of the same
item shows the **combined** invoiced quantity on **both** rows. About 6.6% of orders hit
this. Splitting the matched total across those lines in proportion to ordered quantity
fixes it and keeps the order total right.

**`items[].params.linkedLineItemId` is empty in production.** The code that sets it is
in `serana/src/services/my-clone-invoice/clone-invoice.class.js`. Six real converted
documents were checked and none had it. Do not build on it without checking again.

**`igst` on a document and on a line item is the whole tax.** `cgst` and `sgst` are the
split halves of the same number, not extra tax. `total` = `amount` + `igst`. Summing
`igst + cgst + sgst` doubles the tax.

## 25 August 2026 — `vendorFields` means different things on different entities

`vendorFields` (the team calls them **private custom fields**) exists on both `invoices`
documents and `inventories` items, with the same `r_str_001` / `r_str_002` /
`r_date_001` / `r_num_001` key shape. **The same key means different things on each.**
On a sales order for business `6a8444b1b7fa0c0025af333e`, `r_str_001` is Custom PO No.
On that business's inventory items, `r_str_001` is the item category. Check which entity
you are reading before trusting a key.

The built-in `inventories.category` field looks like the right place for a category and
is **empty**. It is a 16-value enum from `fence/inventory/categories.json`, null on the
items checked, and typed all-null by Metabase's field index across its whole sample.
Businesses put the category in a private custom field instead.

**An uncorrelated `$lookup` is executed once and cached.** A `$lookup` with only a
`pipeline` — no `localField` / `foreignField`, no `let` — is an uncorrelated subquery.
Joining `invoices` to the 1,405-field `businessconfigurations` document to resolve tag
names took **458 ms** uncorrelated versus **1,528 ms** correlated on
`owner` → `business`, over 1,331 rows. The cost is a business id hardcoded in the
sub-pipeline, so the id then lives in two places in the query.

**Document tags are ids, not names.** `invoices.tags` holds label ids like
`7ub2dCJn1ir5AEtGDu1mc`. Names live in `businessconfigurations.labels`, an array of
`{ _id, name, color, isArchived }`, one document per business (`business` is indexed).

## 25 August 2026 — `billedTo` is a snapshot and it can go blank

`invoices.billedTo` is copied onto the document at creation. Editing the client later
does **not** update old documents, and for `uniqueKey` it **clears** the value on them.
Reproduced on business `6a8444b1b7fa0c0025af333e`: after the keys were renamed, two
sales orders carried the new name and a third carried nothing, for the same client.

Measured over 8,933 sales orders (May to Aug 2026): **100%** have `client` set, only
**70%** have `billedTo.uniqueKey`. Join `invoices.client` to `clients._id` and read the
live field. Keep `billedTo.*` as a fallback so the join can only add values.

The same warning applies to every other `billedTo.*` field: name, state, gstin, address.
They are all snapshots.

**Metabase can filter a native MongoDB question.** Use the saved question as the source
of a GUI question; filters, breakouts and aggregations then work on the returned
columns. Confirmed on card 5017. The filter runs on the pipeline's **output**, so it
never narrows the opening `$match` and never makes the query cheaper.
