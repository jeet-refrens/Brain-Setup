# Verified fields — db 2 `refrens` (MongoDB)

Only things that have actually been checked. If it is not here and not in the field
index, **ask**.

The full field list is in `cache/fields.tsv`. Read it with
`python scripts/mb.py fields 2 <collection> <pattern>`. This file holds the parts the
index cannot tell you: what the values mean, which flag hides deleted rows, and what
has bitten us before.

Last updated: **20 August 2026**.

## Conventions that hold across collections

- `_id` is an ObjectId, always indexed.
- `createdAt` and `updatedAt` are the standard date fields, and are indexed on the
  collections that matter. Use `createdAt` for "when was this made".
- `business` is an ObjectId pointing at `businesses._id`. See
  [../join-map.md](../join-map.md).
- Deletion is soft. `isRemoved` and `isHardRemoved` are booleans. **A count that
  ignores them counts deleted records.**
- Nested fields are written with dots: `reminders.to.email`, `billedBy.gstState`.
  The field index already flattens them, so search for the leaf name.

## `invoices` — every business document, not just invoices

1,169 field paths. This one collection holds **all** document types.

**Indexed fields** (the only safe things to filter on first):
`_id`, `business`, `client`, `clientProfile`, `vendor`, `owner`, `creator`,
`bankAccount`, `billType`, `status`, `invoiceNumber`, `expenseNumber`, `invoiceDate`,
`createdAt`, `updatedAt`, `isRemoved`, `isHardRemoved`, `isExpenditure`,
`invoiceAccepted`, `taxType`, `placeOfSupply`, `hideTotals`, `showInSuggestion`,
`billedBy.gstState`, `billedTo.gstState`, `reminders.to.email`,
`reminders.dunningEnabled`, `recurringInvoice.nextDate`.

**`billType` values** — confirmed from live data, 19 Aug 2026, with a 7-day count so
you can see the relative sizes:

| Value | Documents in 7 days |
|-------|---------------------|
| `INVOICE` | 71,220 |
| `QUOTATION` | 20,967 |
| `CREDITNOTE` | 10,059 |
| `PROFORMAINV` | 5,175 |
| `DELIVERYCHALLAN` | 2,977 |
| `PURCHASEORDER` | 2,306 |
| `SALESORDER` | 609 |
| `DEBITNOTE` | 91 |
| `PAYMENTRECEIPT` | 90 |

There may be values that did not appear in that week. This is not a closed list.

**Traps:**

- **"Invoices" almost never means the whole collection.** Filter `billType`.
- `isExpenditure` separates money going out from money coming in. A count of
  `INVOICE` without it mixes sales and purchases.
- **Expenses have no `billType` of their own.** An expense is `billType: INVOICE` with
  `isExpenditure: true`. `isExpenditure` is indexed. In the 30 days to 20 Aug 2026 that
  was 22,723 documents from 1,117 businesses. Do not count expenses from
  `businessacquisitions.featureUsage.expenses`. It under-reports (see below).
- `invoiceDate` is what the user typed. `createdAt` is when the record was made. They
  are different questions, and `invoiceDate` can be backdated.
- Roughly 113,500 documents are created in a typical 7-day window (19 Aug 2026). Size
  date ranges with that in mind.

**Not yet checked:** the `status` values, `taxType` values, `invoiceAccepted` values.
Confirm before using any of them.

## `businesses`

933 field paths.

**Indexed:** `_id`, `name`, `alias`, `urlKey`, `country`, `users`, `categories`,
`preferences`, `source`, `description`, `redirect`, `createdAt`, `updatedAt`,
`isPrivate`, `isRemoved`, `isPageIndexed`, `panNumber`, `elasticUpdatedAt`,
`lastSession`, `cname`, `isRankQualified`, `_systemMeta.urlKeyStatus`,
`premium.enabled`, `premium.productId`.

**Traps:**

- `country` holds **two-letter ISO codes**, not names: `IN`, `US`, `PK`, `MY`, `AE`,
  `ZA`, `KE`, `BD`, `SA`, `GB`. Confirmed 19 Aug 2026. It is indexed, so the
  India / not-India split that matters in nearly every Refrens question is cheap.
  Filter `country: "IN"`, never `"India"`.
- **`premium.enabled` is not a paid flag.** It is indexed, so it looks like the cheap
  way to split paid from free. It is not. Of 59,754 businesses created Mar to May 2026,
  48,127 have `premium.enabled: true` with `premium.onTrial: true` and no
  `premium.endDate`. That is an auto-trial that never expires. Confirmed 20 Aug 2026.
  Use the table under **Paid, trial and conversion** below.
- `users` is an array, so `$unwind` multiplies rows. Filter before unwinding.
- `isHardRemoved` exists here too, but it is **not indexed**. Safe to put in a
  `$match` alongside `createdAt` or `isRemoved`, which are.
- There is **no email on a business**. The cheap way to drop internal and test
  accounts is `urlKey`: exclude anything matching `test|demo`, case ignored. That
  removed 33 of 4,045 in the week to 19 Aug 2026, and all 33 were genuinely
  internal. It is a substring match, so check what it dropped before trusting it.
  A stricter cut means joining to `users` on email.
- About **4,000 businesses are created a week** (19 Aug 2026). Small enough that a
  month or a quarter is fine to query directly.
- More country codes seen 19 Aug 2026: `LK`, `NG`, `ZW`, `UG`, `CA`. Still not a
  closed list.
- **Cut days on IST, not UTC.** Roughly 74% of new businesses are Indian, so a UTC
  day boundary splits every Indian evening in two. Group with
  `"timezone": "Asia/Kolkata"`. See
  [../query-library/businesses-created-by-day.md](../query-library/businesses-created-by-day.md).

## `clients` — the customers a business bills

206 field paths.

**Indexed:** `_id`, `business`, `profile`, `entity`, `industry`, `email`, `source`,
`panNumber`, `uniqueKey`, `shareId`, `isArchived`, `avgPayingDate`, `createdAt`,
`updatedAt`.

**Traps:**

- Archiving uses `isArchived` here, **not** `isRemoved`. Different collection,
  different flag. Check the flag name per collection instead of assuming.
- A client is scoped to one business, so the same real company appears many times
  across different businesses.

## `inventorytransactions`

Only 28 field paths, which makes it one of the easy ones.

**Indexed:** `_id`, `business`, `inventory`, `warehouse`, `docId`, `modifiedBy`.

There is no indexed date field. Filter on `business` or `docId` first.

## `leads`

260 field paths. **Indexed:** `_id`, `business`, `pipeline`, `status`, `quotation`,
`labels`, `referrer`, `shareId`, `clientBusiness`, `clientUser`, `isLegacy`,
`CLOSED`, `createdAt`, `updatedAt`.

`CLOSED` as an indexed field name is unusual. **Not yet checked** what it holds.

## Paid, trial and conversion

Confirmed 20 August 2026 on 63,605 businesses created Jan to Mar 2026.

| Question | Use this |
|----------|----------|
| Did this business ever pay? | `businesses.premium.paymentActivated: true` |
| Is it paying today? | `businesses.premium.enabled: true` **and** `premium.onTrial != true` |
| When did it convert? | `subscriptions.recurrences[]`, the `PAYMENT*` element's `createdAt` |
| What did it pay? | the paid invoice, reached by `recurrences[].invoice` |
| Why did it start a trial? | `subscriptions.recurrences[]`, the `TRIAL` element's `reason` |

Recall against "has at least one paid invoice": `paymentActivated` 99.9%,
`activationType` 97.6%, `enabled and not onTrial` 92.7%.

`enabled and not onTrial` misses businesses that paid and then lapsed. That miss grows as
a cohort ages. Do not use it to compare cohorts of different ages.

**Nothing on `businesses` holds the conversion date.** `premium.trialActivatedAt` is
signup. `premium.trialEndedAt` is trial expiry, and it ran before the first payment in
574 of 574 checked cases. `premium.endDate` is when the subscription ends, and it is
overwritten on renewal. There is no `premiumStartDate` field anywhere.

## `subscriptions`

71 field paths. One row per business.

**Indexed:** `_id`, `clientBusiness`, `createdAt`, `endDate`, `enabled`, `parent`.

- `clientBusiness` is the customer's `businesses._id`. `business` is the Refrens id.
- `createdAt` and `startDate` are **signup**, not conversion. They match the business
  `_id` ObjectId timestamp.
- `activationType` is the **current** state, not history. Values seen in 2026: `TRIAL`,
  `PAYMENT`, `PAYMENT_RC`, `PAYMENT_MANUAL`, `INTERIM`, `REFRENS`, `BARTER`, `RESELLER`,
  `INFLUENCER`, `CHANNEL_PARTNER`, `RC`.
- **`recurrences` is the history.** One element per lifecycle event, in order. The field
  index does not flatten it. Confirmed keys:
  - every element: `_id`, `activationType`, `startDate`, `endDate`, `createdAt`, `updatedAt`
  - `TRIAL` element: `reason`, which paywall the user hit. 62 values, including
    `AUTO_TRIAL_INVOICE`, `AUTO_TRIAL_QUOTATION`, `AUTO_TRIAL_EXPENDITURE`, `Sidebar`,
    `Book Keeping`, `Inventory`, `Gst Lookup`, `Managing Roles`, `Invoices API`.
  - `PAYMENT*` element: `lead`, `pricePlan`, `product`, `period`, `invoice`, `proforma`,
    `params.revenueCatSubscription`, `params.partnerOffer`, `params.creditDiscount`
- The `PAYMENT*` element's `createdAt` matches the paid invoice's `createdAt` to within
  8 seconds. Checked on 3 businesses, 20 Aug 2026.
- The array holds 2 to 3 elements, so `$unwind` roughly doubles rows. It is cheap. Filter
  on `createdAt` or `clientBusiness` **first**. For one flag per business, skip `$unwind`
  and use `$filter` inside `$addFields`.

## `businessacquisitions`

233 field paths. **No indexed fields are recorded.** Reach it through a business id list.

- **`createdAt` is not the business creation date.** July 2026 holds 64,459 rows against
  about 17,000 new businesses. Anchor cohorts on `businesses.createdAt`.
- `featureUsage.<feature>` tracks adoption across 34 features. Each carries
  `usedInLifetime`, `firstUsedAt`, `liveStatus`, `updatedAt`, `backfilledByCommand`.
  Features include `invoices`, `client`, `addItem`, `quotations`, `leads`, `expenses`,
  `purchases`, `purchaseOrders`, `paymentReceipts`, `eInvoicing`, `realTimeBooksSync`,
  `realTimeInventorySync`, `approvalWorkflows`, `embeddedForms`.
- **`firstUsedAt` starts on 12 June 2026.** That is the earliest value anywhere. Use
  `usedInLifetime` as a boolean. Only trust `firstUsedAt` for a first use after that date.
- **`featureUsage.expenses` under-reports.** It showed 354 businesses where direct
  document counting showed 1,117. The feature is new and the tracker is behind.
- `acquisition.utm.*` holds source, medium and campaign.

## `businesses.accounting.*`, the per-business document counters

Lifetime counts per document type, held on the business record. No `invoices` scan needed.

`accounting.<TYPE>.TOTAL` exists for `INVOICE`, `QUOTATION`, `PROFORMAINV`,
`PURCHASEORDER`, `SALESORDER`, `DELIVERYCHALLAN`, `CREDITNOTE`, `DEBITNOTE`,
`PAYMENTRECEIPT` and `EXPENDITURE`. Also `accounting.ALL.TOTAL`.

Channel splits exist on some types: `.DASHBOARD`, `.API`, `.BULKUPLOAD`. `accounting.ALL`
also carries `.PREMIUM`, `.TRIAL`, `.WORKFLOWS`, `.WAREHOUSES`, `.LEADFORMS` and
`.CUSTOM_REPORTS`.

**Trap:** these are **lifetime** counts, read today. For a business that converted they
include everything it did **after** paying. Do not use them to claim a behaviour caused a
conversion. Window the behaviour against the conversion date instead.

## `VIEW_premium_paid_invoice`

Every invoice Refrens raised on a customer. 17 fields.

- `clientProfile` is the customer's `businesses._id`.
- `_id` is the underlying `invoices._id`.
- Carries `amount`, `amountInINR`, `currency`, `period`, `isRenewal`, `product`, `leadID`.
- **`invoiceDate` has a fake time.** Times run 00:00:29, 00:00:30, 00:00:31 in
  invoice-number order. The day is right. For real timing, join on `_id` to
  `invoices.createdAt`.
- Coverage: 953 of the 1,041 businesses that ever paid, in the Jan to Mar 2026 cohort.
  The gap is mostly `PAYMENT_RC` (in-app purchase) and comped accounts.

## Collections not yet looked at

113 of the 118. `python scripts/mb.py tables 2` lists them all. Add a section here the
first time you use one, and record what you confirmed.
