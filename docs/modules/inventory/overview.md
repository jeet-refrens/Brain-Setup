# Inventory — Overview

> Grounded in the live `talos` schemas (`inventories.js`, `inventorytransactions.js`,
> `warehouses.js`, `inventorybatches.js`, `inventoryserials.ts`) and `fence` enums, verified
> 2026-08-06. Business logic lives in `serana`; forms in `lydia`. See [schema.md](schema.md) for
> field-level detail and the Source-of-truth pointers.

## Purpose

Track what a business buys and sells as stock: item master data (products, services, one-time
items), on-hand quantities, per-warehouse balances, batch/serial-level tracking, and the running
cost/selling averages that feed documents (invoices, POs) and the accounting ledgers. Stock is
only actively maintained for items flagged **stock-managed**; others exist as catalogue items.

## Core Entities

- **`inventories`** — the item master (also holds package/group items). Carries identity, pricing,
  tax, stock counters, warehouse cache, and ledger mappings.
- **`inventorytransactions`** — the immutable movement log; every stock change is a row, created
  from documents or manual adjustments. Edits/deletes are done by reversal, never in place.
- **`warehouses`** — physical stock locations (address, GSTIN, primary flag).
- **`batches`** (model `batches`) — batch-tracked stock with mfg/expiry, per-batch counters.
- **`serials`** (model `serials`) — serial-number-tracked units with their own status lifecycle.
- **`businessConfigurations.inventoryOptions`** — business-level item/warehouse switches
  (`manageWarehouses`, `strictInventoryControl`, `defaultItemType`, `pricingStrategy`,
  `batchOptionalFlag`, `defaultReorderPoint`, `defaultOverstockPoint`, `autoExpandPackageItems`,
  `showItemTypeInDocuments`).
- **`businessConfigurations.manageInventory` (Boolean) + `businessConfigurations.<docType>[0].manageInventory`
  (String enum)** — the **per-billType stock-effect configuration**: whether each document type
  updates, blocks, or ignores stock. See [transactions.md](transactions.md#how-transactiontype-is-decided--its-business-configuration).

## Key User Flows

1. **Create/edit an item** — set `itemType` (Product / Service / One Time), toggle `isStockManaged`,
   pick a `trackingMethod` (None / Batch / Serial / Batch+Serial), set pricing and (optionally)
   ledger mappings, reorder/overstock points, and initial stock.
2. **Stock movement from documents** — creating/confirming an invoice, purchase, delivery challan,
   etc. generates `inventorytransactions` that adjust stock (see [transactions.md](transactions.md)).
3. **Manual stock adjustment** — direct add/reduce with a `reason`, recorded as a `MANUAL` /
   `BULKMANUAL` transaction.
4. **Warehouse transfer** — move stock between warehouses (`TRANSFERSTOCK`).
5. **Batch / serial handling** — allocate, block, sell, return, or archive individual batches/serials.

## Status Lifecycles

- **Item stock status** (`inventories.stockStatus`, derived from quantity vs thresholds):
  `outOfStock` · `critical` · `low` · `well` (healthy) · `overstock`.
- **Serial status** (`serials.status`): `AVAILABLE` → `BLOCK` (reserved) → `UNAVAILABLE` (sold/consumed)
  → `ARCHIVED`.
- **Item archival**: `isArchived` (soft) — items are archived, not hard-deleted, in normal flows.

## Known Edge Cases

- **The stock effect is business configuration, not a property of the document type.** Per billType,
  a business chooses `UPDATE` / `BLOCK` / `IGNORE`. Defaults: invoice + expenditure → `UPDATE`,
  proforma → `BLOCK`, **quotation / sales order / purchase order / delivery challan → `IGNORE`**.
  So quotations and sales orders do **not** reserve stock unless explicitly configured to. Full
  resolution chain in [transactions.md](transactions.md#how-transactiontype-is-decided--its-business-configuration).
- **Only `transactionType: UPDATE` moves on-hand stock.** `BLOCK` decrements `stock` but not
  `stockInHand` (reserved, not gone); `IGNORE` = no effect (non-stock-managed item, ignored
  document type, or soft-removed row); `BLOCK_IGNORE` = a previously-blocked row released on
  conversion.
- **Immutable transactions.** To edit/delete a movement, the system writes a reversal
  (`isReversed` / `reversedTransaction`) and, for edits, a fresh row — the log is append-only.
- **`trackingMethod` immutability** (existing behaviour): once an item is `BATCH`/`SERIAL`, it can't
  be switched back to `NONE` on edit.
- **itemType ↔ stock coupling initiative is in-flight, not confirmed in prod.** A planned change
  hard-links Service → `isStockManaged=false`, `strictControl`→requires stock-managed, etc. It is
  documented in `_archive/docs/decisions.md` (dated 2026-07-31) — treat as **proposed**, not live,
  until verified in `serana`. Today `itemType` is still nullable and the flags are independent.
- **Inventory valuation (FIFO/LIFO, valuation runs/vouchers) is a prototype**, not in the live
  schema (no `valuationMethod` field in `inventories.js`). See
  [../../../features/inventory-valuation/](../../../features/inventory-valuation/).
