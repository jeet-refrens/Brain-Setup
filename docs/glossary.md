# Glossary

Canonical terms, field names, and statuses used across Refrens. **Check here before
introducing any new field/status/term name** — reuse an existing one if it fits, and add new
terms here rather than inventing synonyms.

> Terms for **Inventory** and **Workflow & Documents** are grounded in the live `talos`/`fence`
> sources (verified 2026-08-06). **Accounting** and **CRM** rows are grounded in live
> `saturn`/`talos`/`fence` sources (verified 2026-08-15).

| Term | Module | Definition | Notes |
|------|--------|------------|-------|
| itemType | Inventory | Kind of catalogue item: `product` · `service` · `onetime` (One Time). | Field on `inventories`; currently nullable. aka "item category" (avoid — `category` is a separate field). |
| isStockManaged | Inventory | Whether stock is actively tracked for an item. | Boolean, default false. Non-managed items only get `IGNORE` transactions. |
| strictControl | Inventory | Blocks negative stock (strict enforcement) for an item. | Boolean; gated by business-level `strictInventoryControl`. |
| trackingMethod | Inventory | Granularity of stock tracking: `NONE` · `BATCH` · `SERIAL` · `BATCHWISESERIALS`. | Immutable once non-`NONE` (existing behaviour). |
| stockStatus | Inventory | Health of on-hand stock: `outOfStock` · `critical` · `low` · `well` · `overstock`. | Derived from quantity vs reorder/overstock points. |
| transactionType (stock effect) | Inventory | How a movement affects stock: `UPDATE` (moves `stock` + `stockInHand`) · `BLOCK` (moves `stock` only — reserved) · `BLOCK_IGNORE` (releases a prior block) · `IGNORE` (none). | Inline enum on `inventorytransactions`. **Name collision:** distinct from `docType` below. Derived from `manageInventory`, not set directly. |
| manageInventory (per billType) | Inventory ↔ Workflow & Documents | **String enum** `IGNORE` · `BLOCK` · `UPDATE` on `businessConfigurations.<docType>[0]` — the business's choice of what each document type does to stock. | Configurable for `invoice`, `proforma`, `quotation`, `deliveryChallan`, `purchaseOrder`, `expenditure`, `creditNote`, `debitNote`, `salesOrder`, `paymentReceipt`. No schema default; falls back per billType. **Collides by name with the Boolean below.** |
| manageInventory (business switch) | Inventory | **Boolean**, default `false`, on `businessConfigurations` — the master on/off for inventory. When falsy, every document resolves to `IGNORE`. | Same field name as the per-billType enum above, different type and level. Always say which one you mean. |
| advanceOptions.manageInventory | Workflow & Documents | The **resolved** stock effect snapshotted onto a saved document. | Set by `manage-document-inventory-flag`; what `transactionType` is actually derived from. Config changes do **not** retroactively update it on existing documents. |
| docType | Inventory | Source document type that generated a movement (`INVOICE`, `SALESORDER`, `MANUAL`, `TRANSFERSTOCK`, …). | On `inventorytransactions`; uses `fence/inventory/transactionType.json` (confusingly-named file). |
| currency (on a movement) | Inventory | The currency a stock movement happened in — i.e. the currency its `costPrice`/`sellingPrice` are expressed in. Comes from the source document. | Live field on `inventorytransactions`. **Not** the business currency; the movement carries no business-currency value today. |
| conversionRate | Inventory | **Proposed, not yet built.** Business-currency units per 1 unit of a movement's `currency`, so `book value = price × conversionRate`. | Planned on `inventorytransactions` by [features/inventory-transaction-currency-conversion/](../features/inventory-transaction-currency-conversion/). Singular of the document's `conversionRates` map, which is where the value comes from — same direction, same meaning, one currency instead of a map. Equivalent to Accounting's `forex_rate`. Do not coin a synonym (`forexRate`, `exchangeRate`, `rate`); `priceFactor` is the in-memory variable this replaces. **Never call it just "rate"** — a document line already has a `rate` field, which is its unit price. |
| bookCurrency (on a movement) | Inventory ↔ Accounting | **Proposed, not yet built.** The business currency a movement's `conversionRate` converts into. | Same meaning as Accounting's `book_currency`, applied to `inventorytransactions`. Recorded per row because a business can change its base currency. |
| conversionRates | Workflow & Documents | A document's stored exchange rates: a map keyed by **business currency code** → rate. A USD invoice in an INR business holds `conversionRates.INR`. | On `invoices` (and separately on each payment, credit claim and wallet transaction, at that event's own date). The submitted rate is **trusted** — a failed lookup is never persisted as `0`. |
| warehouse | Inventory | Physical stock location (`warehouses` collection). | Per-item/-batch balances cached in `warehouses[]`; the location master is `warehouses`. |
| batch | Inventory | Batch-tracked stock lot (`batches` model) with mfg/expiry and own counters. | For `trackingMethod = BATCH` / `BATCHWISESERIALS`. |
| serial | Inventory | Individual serial-numbered unit (`serials` model). | Status: `AVAILABLE` · `BLOCK` · `UNAVAILABLE` · `ARCHIVED`. |
| ledger mapping | Inventory ↔ Accounting | `salesLedger` / `purchaseLedger` / `inventoryLedger` on an item, linking it to accounting ledgers. | `{ ledgerId, ledgerName }` each. |
| document (type) | Workflow & Documents | A business document in the shared `invoices` collection: `INVOICE`, `QUOTATION`, `PROFORMAINV`, `SALESORDER`, `PURCHASEORDER`, `EXPENDITURE`, `DELIVERYCHALLAN`, `CREDITNOTE`, `DEBITNOTE`, `PAYMENTRECEIPT`. | `fence/invoices/documentTypes.json`. |
| invoiceStatus | Workflow & Documents | Document lifecycle status: `DRAFT` · `UNPAID` · `PARTIAL` · `PAID` · `OVERDUE` · `CANCELED`. | Field `status`, default `UNPAID`. |
| billType / types | Workflow & Documents | `types`: `INVOICE` (Tax Invoice) · `BOS` (Bill of Supply). `billType` default `INVOICE`. | GST document classification. |
| conversion (convertedFrom) | Workflow & Documents | Creating a document from another (e.g. quotation → invoice); may be partial. | `convertedFrom`, `partialConvert`, `isSourceConverted`, `linkedDocuments[]`. |
| invoiceaudit | Workflow & Documents | A versioned snapshot of a document edit (`versionNumber`, `action`, `oldValues`). | `invoiceaudits` collection; pinned by signature requests. |
| documentSignatureRequest | Workflow & Documents | An e-signature request (via Digio) against a document, with per-signer state. | Status `NONE`/`PENDING`/`SIGNED`/`EXPIRED`/`CANCELLED`; signer roles `BUSINESS`/`CLIENT`/`INTERNAL`. |
| accountGroup | Accounting | A chart-of-accounts group (`accountgroups` in `saturn`), e.g. Sundry Debtors, Duties and Taxes. | 45 values in `fence/accounting/accountGroupType.json`. Parent of `ledger`. |
| accountType | Accounting | The fundamental class of an account group/ledger: `asset` · `liability` · `income` · `expense` · `capital`. | On both `accountgroups` and `ledgers`. |
| ledger (accounting) | Accounting | An individual account inside an account group (`saturn.ledgers`). | **Disambiguate:** "ledger" alone is ambiguous — see `wallet transaction`. Links to Mongo via `document_refers_to` + `document_reference_id`. |
| voucher | Accounting | A voucher **book** (Sales, Purchase, Payment, Receipt, Journal, Contra…), not an individual entry. | `saturn.vouchers`; 19 `voucherType` values. |
| voucherEntry | Accounting | One posted accounting entry (`saturn.voucher_entries`), with `debits`/`credits`, `voucher_date`, `version`. | Corrections bump `version`; reversal sets `reversed`/`reversal_entry`. Never deleted. |
| lineItem (accounting) | Accounting | One Dr/Cr leg of a voucher entry against one ledger (`saturn.lineitems`). | **Name collision:** distinct from a document's line item (`invoiceItems` on `invoices`). Say "voucher line item" when ambiguous. |
| crdr | Accounting | Direction of a voucher line item: `cr` · `dr`. | `fence/accounting/creditDebitType.json`. |
| financialYear | Accounting | A per-business FY window (`saturn.financial_years`, `label`/`start_date`/`end_date`). | FY start varies by country — `fence/accounting/fyByCountry.json`. |
| bookAmount / bookCurrency | Accounting | The business-currency value of a line item, converted from `amount`/`currency` at `forex_rate`. | Amounts are stored as **integers** (minor units), not floats. |
| syncAccounting | Accounting | Per-business, per-document-type gate controlling whether documents post to the books. | `businessConfigurations.syncAccounting`; status `NONE`/`REQUESTED`/`SCHEDULED`/`DONE`/`FAILED`. |
| syncBreak | Accounting | A flag that halts accounting sync for one document until repaired. | Reasons in `fence/accounting/syncBreakReasons.json`. |
| default_key | Accounting | Stable identifier for a system-created ledger/group/voucher (`REF_DEFAULT_*`, `REF_Legacy_*`). | `fence/accounting/ledgerDefaultKeys.json` (~75 ledgers). |
| wallet transaction | Accounting | Money movement between `wallets` (`transactions.debit`/`credit`) — **not** double-entry bookkeeping. | Mongo-side; links into the books via `paymentLedgerId`/`paymentVoucherEntryRefrence`. |
| paymentAccount | Accounting | The user-facing "paid into / paid from" account; carries `ledgerId` mapping it to a Saturn ledger. | `paymentAccounts` collection. Supersedes the legacy per-payment-mode ledgers. |
| reconciliationStatus | Accounting | Bank-reconciliation outcome per row: `MATCHED` · `MISSING_IN_LEDGER` · `MISSING_IN_BANK_BOOK` · `DISCARDED` · `MARKED_FOR_LATER` · `RECONCILED`. | `bank_transactions` (bank side) vs `bank_books` (books side). |
| client | CRM | An **organisation** a business bills or buys from (`clients`). | Role is a flag combination (`isClient`/`isVendor`/`isBilledClient`/`isSelf`), not a type. Carries `ledgerId`. |
| contact | CRM | An **individual person** (`contacts`), business-scoped and mergeable. | Distinct from `clients`. Linked via `contactRelations`. |
| contactRelation | CRM | The contact↔client link carrying `department`, `role`, `isPrimary`, `isActive`. | One primary contact per client. |
| lead | CRM | An enquiry/opportunity (`leads`) worked through a pipeline until it converts or is lost. | `status`: `NEW`·`OPEN`·`CLOSED`·`DROPPED`·`REJECTED` — **labels differ from keys** ("Deal Done", "Lost", "Not Serviceable"). |
| pipeline | CRM | An ordered set of lead stages, stored as **business configuration** (`businessConfigurations.lms.pipelines[]`), not its own collection. | One may be `isPrimary`. |
| leadStage | CRM | A stage within a pipeline: `name`, `state`, `closure`, `decayThreshold`. | `_id` is a **nanoid string**. `closure` = sales probability %. `decayThreshold` is always in **hours**. |
| decayStatus | CRM | How stalled a lead is: `On Track` · `Needs Attention` · `Stalled`. | On `leadPipelineHistory`; derived from stage `decayThreshold`. |
| workflow (approval) | CRM | A named, typed approval chain for **documents** (`workflows` + `workflowitems`). | **Name collision:** unrelated to the Workflow & Documents module's document lifecycle. Types: `INVOICE`, `QUOTATION`, `SALESORDER`, `PURCHASEORDER`, `PROFORMAINV`, `EXPENDITURE`, `VENDOR_LEADS`. |
| workflowItem | CRM | One live instance of a workflow against a `sourceDocument`; status `OPEN`·`COMPLETED`·`CLOSED`. | Status **display labels are business-configurable** — don't hard-code "Approved"/"Rejected". |
| integrationType | CRM | Third-party connector on a business (`integrations`): `INDIAMART`, `FB-META`, `TRADE-INDIA`, `AISENSY`, `COMPLYANCE`, `CASHFREE-MERCHANT`, `GOOGLE-CALENDAR` (+ IndiaMART webhook/backfill variants). | Shopify is **not** here — it's a separate app. |

## Conventions

- One row per canonical term. If two teams use different words for the same thing, pick one
  canonical term and list the others under **Notes** as "aka".
- Prefix module-specific statuses with context if the same word means different things in two
  modules (note the collision here).

**Known collisions — always disambiguate:**

| Word | Meaning A | Meaning B |
|---|---|---|
| `transactionType` | Inline stock-effect enum on `inventorytransactions` (`UPDATE`/`BLOCK`/`BLOCK_IGNORE`/`IGNORE`) | The `fence/inventory/transactionType.json` file, which actually backs **`docType`** (document types). Use **docType** for the document-type meaning. |
| `manageInventory` | `businessConfigurations.manageInventory` — a **Boolean** master switch (default `false`) | `businessConfigurations.<docType>[0].manageInventory` — a **String enum** (`IGNORE`/`BLOCK`/`UPDATE`) per document type. Say **"business inventory switch"** vs **"per-billType stock effect"**. A third, resolved value lives on documents at `advanceOptions.manageInventory`. |
| **ledger** | An accounting account in `saturn.ledgers` | The Mongo `transactions`/`wallets` money-movement layer. Say **"books ledger"** vs **"wallet transaction"**. |
| **line item** | A Dr/Cr leg of a voucher entry (`saturn.lineitems`) | A product/service row on a document (`invoiceItems` on `invoices`). Say **"voucher line item"** vs **"document line item"**. |
| **workflow** | The CRM approval engine (`workflows`/`workflowitems`) | The document lifecycle in Workflow & Documents (`invoices.status`, conversions). Say **"approval workflow"** vs **"document workflow"**. |
| **transactions** | `talos.transactions` — wallet money movement | `talos.inventorytransactions` — stock movements. Always use the full collection name. |
| **client** | `clients` — an organisation (CRM/billing) | "client" as in API caller. Prefer **client record** for the CRM sense. |
