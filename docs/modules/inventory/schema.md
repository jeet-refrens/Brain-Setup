# Inventory — Schema

## Summary

> Curated from the live `talos`, `birds` and `fence` sources, verified 2026-08-06; the
> `manageInventory` stock-effect config re-verified 2026-08-15. Field-for-field truth is in
> **Source of truth** below — use it whenever exact types/enums matter.

### Entities & key fields

| Entity (model) | Key fields (curated) | Notes |
|----------------|----------------------|-------|
| **`inventories`** (item master) | `sku`, `name`(req), `itemType`(enum, nullable), `hsn`, `category`, `unit`, `trackingMethod`(default `NONE`), `isStockManaged`(default false), `strictControl`(default false), `initialStock`, `stock`, `stockInHand`, `soldQuantity`, `purchaseQuantity`, `stockStatus`, `reorderPoint`, `overstockPoint`, `warehousesStockThresholds[]`, `sellingPrice`, `costPrice`, `avgSellingPrice`, `avgCostPrice`, `landedCost`, `isPriceTaxInclusive`, `inclusivePrices`, `gstRate`, `taxCategory`, `itc`, `warehouses[]`(cache), `salesLedger`, `purchaseLedger`, `inventoryLedger`, `isPackage`, `items[]`, `groups[]`, `business`, `documents[]`, `isArchived`, `isSalesItem`, `source` | One collection for products/services/one-time **and** package/group items (`isPackage`). `warehouses[]` is the materialized per-warehouse stock cache. `*Ledger` fields link to accounting. |
| **`inventorytransactions`** | `inventory`, `business`, `quantity`, `unit`, `type`(BUY/SELL), `transactionType`(IGNORE/BLOCK/BLOCK_IGNORE/UPDATE, default UPDATE), `docType`(source doc type enum), `docId`→`invoices`, `transactionDate`, `costPrice`, `sellingPrice`, `gstRate`, `warehouse`, `batch`→`batches`, `serials[]`, `isReversed`, `reversedTransaction`, `isStockManaged`, `itemType`, `reason`, `createdBy`/`modifiedBy`/`modifiedByApp`, `group` | Immutable movement log. `transactionType` is **derived from business config**, not the document type — see [transactions.md](transactions.md#how-transactiontype-is-decided--its-business-configuration). `UPDATE` moves `stock` + `stockInHand`; `BLOCK` moves `stock` only. Reversal-based edits. `action` enum is **deprecated**. |
| **`warehouses`** | `name`(req), `warehouseId`(req), `business`(req), `address{street,city,state,stateCode,pincode,country,gstState,...}`, `gstin`, `vatNumber`, `contact{name,phone,email}`, `isPrimary`, `isActive`, `isArchived`, `systemGenerated` | Physical location master. |
| **`batches`** | `batchCode`(req), `batchName`(req), `inventory`, `business`, `vendor`→`clients`, `manufacturingDate`, `expiryDate`, `costPrice`, `sellingPrice`, `stock`, `stockInHand`, `avgCostPrice`, `avgSellingPrice`, `soldQuantity`, `purchaseQuantity`, `lowStockAlert`, `warehouses[]`, `isArchived`, `isHardRemoved` | Batch-tracked stock; own counters + warehouse cache. |
| **`serials`** | `serialNumber`(req, validated), `inventory`, `business`, `batch`→`batches`, `status`(AVAILABLE/BLOCK/UNAVAILABLE/ARCHIVED), `warehouse`, `client`, `reason`(enum), `manufacturedDate`, `warrantyDate`/`warrantyPeriod{value,unit}`, `soldDate`, `salesTxn`/`purchaseTxn`/`additionalTxns[]`, `sourceDocument`/`currentDocument`→`invoices`, `lockedBy`/`lockExpiresAt`, `isArchived` | One doc per physical unit. `batch` set when `trackingMethod = BATCHWISESERIALS`. |
| **`businessConfigurations.inventoryOptions`** | `manageWarehouses`, `strictInventoryControl`, `defaultItemType`, `pricingStrategy`, `sameFlowPricingStrategy`, `crossFlowPricingStrategy`, `batchOptionalFlag`(default `blockignore`), `defaultReorderPoint`(10), `defaultOverstockPoint`(100), `autoExpandPackageItems`, `showItemTypeInDocuments` | Item/warehouse-level switches; act as transaction-time gates, non-destructive when toggled off. **`showItemTypeInDocuments` gotcha:** its `default: true` only materialises on hydrate/save — PATCH `$set`, lean reads, aggregations and the Redis config cache return `undefined` for older documents, so **readers must treat `undefined` as `true`**, unlike the sibling booleans which default false. |
| **`businessConfigurations.manageInventory`** | **Boolean**, default `false` | Master on/off for inventory across the business. When falsy every document resolves to `IGNORE`. |
| **`businessConfigurations.<docType>[0].manageInventory`** | **String** enum `IGNORE`·`BLOCK`·`UPDATE`, **no default** | The **per-billType stock effect**. `<docType>` ∈ `invoice`, `proforma`, `quotation`, `deliveryChallan`, `purchaseOrder`, `expenditure`, `creditNote`, `debitNote`, `salesOrder`, `paymentReceipt` — each an **array** of `DocumentConfiguration`, of which only `[0]` is read. Defined in `talos/src/helpers/businessConfiguration.ts` (`DocConfigCommonFields`). |

### Enums (exact, from `fence`)

- **`itemType`** (`fence/inventory/itemType.json`): `product` · `service` · `onetime`.
- **`trackingMethod`** (`.../trackingMethod.json`): `NONE` · `BATCH` · `SERIAL` · `BATCHWISESERIALS`.
- **`stockStatus`** (`.../stockStatus.json`): `critical` · `low` · `well` · `overstock` · `outOfStock`.
- **`inventorytransactions.type`** (inline): `BUY` · `SELL`.
- **`inventorytransactions.transactionType`** (inline): `IGNORE` · `BLOCK` · `BLOCK_IGNORE` · `UPDATE`.
- **`inventorytransactions.docType`** (`.../transactionType.json`): source document type —
  `INVOICE`, `PROFORMAINV`, `QUOTATION`, `SALESORDER`, `PURCHASEORDER`, `EXPENDITURE`,
  `DELIVERYCHALLAN`, `CREDITNOTE`, `DEBITNOTE`, `MANUAL`, `BULKMANUAL`, `TRANSFERSTOCK`, `RECONCILE`.
- **`serials.status`** (inline): `AVAILABLE` · `BLOCK` · `UNAVAILABLE` · `ARCHIVED`.

### Relationships

- `inventories` 1—N `inventorytransactions` (`inventory`).
- `inventorytransactions.docId` → `invoices` (the source document that caused the movement).
- `inventories.warehouses[]` / `batches.warehouses[]` embed per-warehouse balances (cache);
  `warehouses` is the standalone location master (`inventorytransactions.warehouse`, `serials.warehouse`).
- `inventories` 1—N `batches` 1—N `serials` (serial `batch` set only for batch+serial tracking).
- `inventories.{salesLedger,purchaseLedger,inventoryLedger}` link items to accounting ledgers.
- Package items: `inventories.isPackage=true` with `items[]` (children) / `groups[]` (parents).

## Source of truth

Fetch exact definitions via the GitHub REST API (reference `GITHUB_PAT` **by name only**; `gh` is
**not installed** in this environment) — or run `/sync-schema inventory`.

- **`refrens/talos`** — `src/inventories.js`, `src/inventorytransactions.js`, `src/warehouses.js`,
  `src/inventorybatches.js`, `src/inventoryserials.ts`, `src/helpers/warehouseSchema.js`,
  `src/businessConfigurations.ts` (`inventoryOptions` ~line 631),
  **`src/helpers/businessConfiguration.ts`** (`DocConfigCommonFields.manageInventory` ~line 178,
  `LegacyConfig.manageInventory` ~line 258, the `[DocumentConfiguration]` per-billType arrays
  ~lines 272-281).
- **`refrens/fence`** — `inventory/itemType.json`, `trackingMethod.json`, `stockStatus.json`,
  `transactionType.json`, `serialReason.json`, `batchOptionalFlag.json`.
- **`refrens/birds`** — **`src/helpers/get-manage-inventory-flag.ts`** (the authoritative
  stock-effect resolver), `src/helpers/check-batch-in-document-required.ts`.
- **`refrens/serana`** — `src/hooks/manage-document-inventory-flag.js` (stamps
  `advanceOptions.manageInventory`), `manage-document-inventory.js`,
  `manage-inventory-stock.js`, `manage-linked-document-inventory-transaction.js`,
  `src/helpers/onDocumentUpdate.js`; plus **`docs/inventory.md`** and
  `.claude/skills/inventory-knowledge/SKILL.md` — in-repo narrative docs, useful but **verify
  against code** (their `DELIVERYCHALLAN` default disagrees with `birds`).
  **`refrens/lydia`** — item forms.
- **Fetch pattern** (`gh` is **not** installed; PAT by name only):
  ```bash
  curl -s -H "Authorization: Bearer $GITHUB_PAT" -H "Accept: application/vnd.github.raw" \
    "https://api.github.com/repos/refrens/birds/contents/src/helpers/get-manage-inventory-flag.ts"
  ```
