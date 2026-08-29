# inventory-net-price-on-transactions — working context

## Modules touched

- **Primary: Inventory** — `inventorytransactions` schema, the avg-price computation
  (`avgCostPrice`/`avgSellingPrice` at item, per-warehouse, and per-batch level), and every
  report built on those averages.
- **Upstream trigger: Workflow & Documents** — the line item's `discount`/`amount` fields (the
  source of truth for "price actually transacted at") live on the document, not on Inventory.
  This feature reads that value but does not change document schema or behaviour.
- Not touched: Accounting, CRM.

## Docs read for this kickoff

- [docs/modules/inventory/overview.md](../../docs/modules/inventory/overview.md) — core entities,
  key flows, known edge cases (valuation is prototype-only, transactions are append-only/reversal-based).
- [docs/modules/inventory/schema.md](../../docs/modules/inventory/schema.md) — `inventorytransactions`
  and `inventories` field lists; confirms `avgCostPrice`/`avgSellingPrice` live on `inventories`
  (and mirrored on `batches`).
- [docs/modules/inventory/transactions.md](../../docs/modules/inventory/transactions.md) — the
  `type`/`transactionType` axes, immutability/reversal model, and the existing note that
  "movements carry `costPrice`/`sellingPrice`, which drive the item's `avgCostPrice`/`avgSellingPrice`."
  This feature is a direct follow-on to that note.
- [docs/modules/workflow-documents/schema.md](../../docs/modules/workflow-documents/schema.md) —
  confirms line items carry `discount{discountType,amount}` and net `amount` separately from
  `invoiceTransactions`; the two are currently disconnected.
- [docs/cross-module-links.md](../../docs/cross-module-links.md) — "Sales invoice finalised" and
  "Purchase / expenditure recorded" rows: both generate Inventory `UPDATE` movements and "avg cost
  updated" — this feature corrects what that update is based on. No accounting-posting change.
- [docs/glossary.md](../../docs/glossary.md) — no existing term for a discount-adjusted/net unit
  price; this feature introduces one (see spec Open Questions on naming).

## Session research (grounded in live code, not docs)

`gh`/PAT-based reads against `refrens/talos` and `refrens/serana` this session (2026-08-08)
established the exact mechanism — see `spec.md` for the full trace. Key files, for whoever
picks up implementation:

- `talos/src/inventorytransactions.js` — schema to extend.
- `talos/src/helpers/invoiceItems.js` — line item shape (`rate`, `discount`, `amount`, `subTotal`).
- `serana/src/helpers/getInvoiceItem.js` — proves `amount = subTotal − discount.amount` (net,
  pre-tax); `rate` stays gross.
- `serana/src/hooks/manage-linked-document-inventory-transaction.js:25-26` — where
  `costPrice`/`sellingPrice` are currently set from `sourceItem.rate` (gross). The **primary**
  (non-linked) document → transaction builder that does the equivalent for the main invoice/PO
  flow was not pinned down by code search this session — first implementation task is locating it.
- `serana/src/hooks/manage-inventory-stock.js` — `calculateAveragePrice()` (weighted moving
  average) and its callers `adjustInventoryStock` / `updateWarehouseData`, which consume
  `costPrice`/`sellingPrice` off the transaction.

## Reminders

- Reference `.env` secrets (`GITHUB_PAT`, etc.) **by name only** — never print/paste values.
- Inventory valuation (FIFO/LIFO, valuation runs) is a **prototype**, not live — see
  `features/inventory-valuation/`. This feature is independent of it but the two will eventually
  need to agree on what "actual transacted price" means; flag conflicts to that feature's owner
  if valuation work resumes before this ships.
