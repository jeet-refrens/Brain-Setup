# Join map

MongoDB has no foreign keys, so nothing here can be read off the schema. Every link
below was confirmed by hand. **Do not add a link you have not checked.**

Last updated: **20 August 2026**.

Mark each link with how sure we are:

- **confirmed** — checked against the field index and a query that returned sensible rows
- **likely** — the field index says the shape is right, but no query has proved it
- **unknown** — do not use without checking first

## The spine: `business`

Almost everything hangs off the business.

`businesses._id` (ObjectId) is the anchor. At least 40 collections in db 2 carry a
top-level `business` field pointing at it. On the ones that matter it is indexed:
`invoices`, `clients`, `leads`, `inventories`, `inventorytransactions`,
`businessconfigurations`, `bankaccounts`, `integrations`, `activities`, `calls`,
`forms`, `feedbackresponses`, `businessdashboards`, `invoiceaudits`, `badges`,
`greetings`. **confirmed** (field index, 19 Aug 2026)

Practical effect: filtering by `business` is almost always cheap, and is usually the
right first filter.

## Across services: Mongo to Saturn

| From | To | How | Status |
|------|----|-----|--------|
| `refrens.businesses._id` (ObjectId) | `Saturn.*.business` (varchar) | The same id, stored in Postgres as its 24-character hex string | **confirmed** 19 Aug 2026 |

**The trap:** the type differs. Mongo holds an `ObjectId`, Saturn holds a `varchar`.
Going Mongo to Saturn, use the string form. Coming back, wrap it in `ObjectId("...")`.
There is no cross-database join in Metabase — run one query per database and match the
ids yourself.

Every business-scoped Saturn table carries `business`: `vouchers`, `voucher_entries`,
`ledgers`, `lineitems`, `accountgroups`, `financial_years`, `bank_books`,
`bank_statements`, `bank_transactions`, `reconciliations`,
`reconciliation_bank_books`, `reconciliation_lineitems`, `fy_wise_ledgers_data`,
`fy_wise_vouchers_data`. **confirmed** (field index)

Posting to the books is **opt-in per business per document type**. So a document in
Mongo does not mean a voucher exists in Saturn. See
[../modules/accounting/overview.md](../modules/accounting/overview.md).

## Within db 2 (MongoDB)

All of the following are indexed on the left-hand side.

| From | Field | To | Status |
|------|-------|----|--------|
| `invoices` | `business` | `businesses._id` | **confirmed** |
| `invoices` | `client` | `clients._id` | **likely** — indexed ObjectId, name matches, not yet proved by query |
| `invoices` | `clientProfile` | `businesses._id` (the client's own business, when they have one) | **confirmed** 20 Aug 2026 — proved on Refrens' own paid invoices |
| `invoices` | `vendor` | `clients._id` or `businesses._id` | **unknown** — matters for expense documents |
| `invoices` | `owner`, `creator` | a user | **likely** |
| `invoices` | `bankAccount` | `bankaccounts._id` | **likely** |
| `clients` | `business` | `businesses._id` (the business that owns this client record) | **confirmed** |
| `clients` | `profile` | a linked profile / business | **unknown** |
| `clients` | `entity`, `industry` | `entities._id`, `industries._id` | **likely** |
| `businesses` | `users` (array) | users | **likely** |
| `inventorytransactions` | `business` | `businesses._id` | **confirmed** |
| `inventorytransactions` | `inventory` | `inventories._id` | **likely** |
| `inventorytransactions` | `warehouse` | a warehouse | **likely** |
| `inventorytransactions` | `docId` | `invoices._id` (the document that moved the stock) | **likely** — see [../modules/inventory/transactions.md](../modules/inventory/transactions.md) |
| `leads` | `business` | `businesses._id` | **confirmed** |
| `leads` | `quotation` | `invoices._id` | **likely** |
| `leads` | `clientBusiness`, `clientUser` | `businesses._id`, a user | **likely** |
| `subscriptions` | `clientBusiness` | `businesses._id` (the customer) | **confirmed** 20 Aug 2026 — indexed |
| `subscriptions` | `business` | `businesses._id` (Refrens' own account) | **confirmed** 20 Aug 2026 |
| `subscriptions` | `recurrences[].invoice` | `invoices._id` (the paid invoice) | **confirmed** 20 Aug 2026 — dates agree to 8 seconds |
| `subscriptions` | `recurrences[].proforma` | `invoices._id` (the proforma) | **likely** |
| `subscriptions` | `activeLead` | `leads._id`, and equals `VIEW_premium_paid_invoice.leadID` | **confirmed** 20 Aug 2026 |
| `businessacquisitions` | `business` | `businesses._id` | **confirmed** 20 Aug 2026 — but see the `createdAt` trap |

## The Refrens house account

Refrens bills its own customers from one business:
`businesses._id = ObjectId("6041f964023c430011d81409")`. Confirmed 20 Aug 2026.

So every subscription payment appears twice:

- as a document in `invoices` where `business` is that id, `billType: INVOICE`,
  `status: PAID`, and `clientProfile` is the paying customer
- as an element in `subscriptions.recurrences[]` where `activationType` starts with
  `PAYMENT`

`business` is indexed on `invoices`, so filtering to the house account is cheap. About
1,150 paid invoices a month (July 2026).

**Which to use.** Use `recurrences` for timing and history. It is one collection and both
filter fields are indexed. Use the invoice for amount and currency. Reach it by
`recurrences[].invoice`.

## How to join in practice

Metabase cannot join two databases, and a `$lookup` without a sub-pipeline reads the
whole joined collection. So the house pattern, the one the existing saved questions
use, is **two steps**:

1. Query one, filtered and indexed, returning the ids you need.
2. Query two, with those ids in a `$match: { field: { $in: [...] } }`.

Keep the id list to a few thousand. If it is bigger than that, the question probably
wants a `$group` instead of a join.

Sometimes a `$lookup` really is the right tool. Then it must use `let` plus a
`pipeline`, with a `$match` on an indexed field of the joined collection. The script
enforces this.

## Promoting a link

A **likely** link becomes **confirmed** when a query using it returns sensible rows.
Change the status, add the date, and put the query in
[query-library/](query-library/).
