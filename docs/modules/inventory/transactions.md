# Inventory — Transactions

> Grounded in `talos/src/inventorytransactions.js` + `fence/inventory/transactionType.json`,
> verified 2026-08-06; the `manageInventory` resolution chain (`birds` +
> `serana/src/hooks/manage-document-inventory-flag.js`) verified 2026-08-15.
> Movement-generation logic lives in `serana`.

Every stock change is a row in **`inventorytransactions`**. The log is **append-only**: an item's
current `stock` / `stockInHand` / averages are derived by replaying its transactions, so edits and
deletes are done by writing reversals — never by mutating an existing row.

## The two axes: `type` and `transactionType`

- **`type`** — the direction of the movement: `BUY` (inbound) or `SELL` (outbound).
- **`transactionType`** — whether/how it affects stock:

| `transactionType` | Effect on stock | When |
|-------------------|-----------------|------|
| `UPDATE` | **Moves stock.** Decrements/increments both `stock` and `stockInHand`. The only type that changes on-hand quantity. | Document configured to `UPDATE` **and** a stock-managed item. |
| `BLOCK` | Reserves stock: decrements **`stock` only**, leaves `stockInHand` untouched. | Document configured to `BLOCK` (soft hold — proforma by default). |
| `BLOCK_IGNORE` | No effect — cancels a prior `BLOCK` without double-counting. | **Derived, never configured**: set when a `BLOCK`ed document is fully converted into one resolving to `UPDATE`. |
| `IGNORE` | No effect on stock; recorded for traceability only. | Document configured to `IGNORE`, **or** the line item is not stock-managed, **or** the transaction was soft-removed. |

> `stock` moves on `BLOCK` **or** `UPDATE`; `stockInHand` moves on `UPDATE` only (and never for
> `isPackage` items). This is the practical difference between "reserved" and "gone".

## How `transactionType` is decided — it's business configuration

**The stock effect is not fixed per document type.** A business configures, per billType, whether
that document updates, blocks, or ignores stock. This is the single most important thing to know
before reasoning about when stock moves.

The resolved value is stamped onto the document as **`advanceOptions.manageInventory`** by
`serana/src/hooks/manage-document-inventory-flag.js`, which delegates to
`getManageInventoryFlag()` in `birds`. Resolution order:

1. **Explicit payload override** — if `data.advanceOptions.manageInventory` is already set, it wins
   and the hook returns immediately.
2. **Business master switch** — `businessConfigurations.manageInventory`, a **Boolean** defaulting
   to `false`. If falsy, **every document resolves to `IGNORE`**; inventory is off for the business.
3. **Per-billType config** — `businessConfigurations.<docType>[0].manageInventory`, a **String**
   enum `IGNORE` · `BLOCK` · `UPDATE` with **no schema default**. Configurable doc types:
   `invoice`, `proforma`, `quotation`, `deliveryChallan`, `purchaseOrder`, `expenditure`,
   `creditNote`, `debitNote`, `salesOrder`, `paymentReceipt`. The config is an **array**; only
   element `[0]` is read.
4. **Fallback** when that config is unset:

   | billType | Fallback |
   |---|---|
   | `INVOICE`, expenditure (`isExpenditure`) | `UPDATE` |
   | `PROFORMAINV` | `BLOCK` |
   | `QUOTATION`, `PURCHASEORDER`, `SALESORDER`, `DELIVERYCHALLAN` | `IGNORE` |
   | anything else (`CREDITNOTE`, `DEBITNOTE`, `PAYMENTRECEIPT`, …) | `IGNORE` |

5. **Per-item final gate** — for each line item:
   `transactionType = inventory.isStockManaged ? inventoryFlag : 'IGNORE'`.
   A non-stock-managed item always produces `IGNORE`, regardless of document configuration.

### Gotchas

- **⚠️ Naming collision.** `businessConfigurations.manageInventory` (business level) is a
  **Boolean**; `businessConfigurations.<docType>[0].manageInventory` (per document type) is a
  **String enum**. Same name, different types, different levels.
- **⚠️ Source discrepancy on `DELIVERYCHALLAN`.** `serana/docs/inventory.md` documents the fallback
  as `UPDATE`; the live `birds` resolver returns `IGNORE`
  (`deliveryChallan.manageInventory || 'IGNORE'`). **The code is authoritative.** Re-verify before
  depending on delivery-challan stock behaviour.
- **Quotations, sales orders and POs do not reserve stock by default** — all fall back to `IGNORE`.
  Only proforma defaults to `BLOCK`. "Sales order reserves stock" is a common but wrong assumption.
- **The flag is snapshotted on the document.** Changing business config later does not retroactively
  alter existing documents. Conversely, a change to `advanceOptions.manageInventory` on an existing
  document is itself a recognised change trigger (`result.advanceOptions.manageInventory !==
  stashedData.advanceOptions?.manageInventory`) that re-runs the inventory effect — reversing the
  old flag's effect before applying the new one.
- **`BLOCK_IGNORE` is derived, not configured.** The config enum has only three values; the
  transaction enum has four.

## Source document type (`docType`)

`docType` records which kind of document generated the movement (enum
`fence/inventory/transactionType.json`): `INVOICE`, `PROFORMAINV`, `QUOTATION`, `SALESORDER`,
`PURCHASEORDER`, `EXPENDITURE`, `DELIVERYCHALLAN`, `CREDITNOTE`, `DEBITNOTE`, `MANUAL`,
`BULKMANUAL`, `TRANSFERSTOCK`, `RECONCILE`. The originating document is referenced via
`docId` → `invoices`.

## Immutability / reversal model

- Edit or delete of a movement ⇒ a reversal row is written (`isReversed`,
  `reversedTransaction`), plus (for edits) a new row with the corrected values.
- Effective stock = the **net-of-reversals** set of `UPDATE` rows, replayed in order
  (`transactionDate`, then `createdAt`, then `_id`).
- Reversal pairs never re-enter as new movements.

## Batch / serial / warehouse targeting

- `warehouse` — which location the movement touched (recorded even for `IGNORE` rows).
- `batch` → `batches`, `serials[]` — set when the item is batch/serial tracked.
- `group` → `inventories` — links child-item movements for package/group items.
- `createdBy` / `modifiedBy` / `modifiedByApp` — actor (user, or app for API-sourced changes).

## Valuation impact

Movements carry `costPrice` / `sellingPrice`, which drive the item's `avgCostPrice` /
`avgSellingPrice`. **Full inventory valuation** (FIFO/LIFO layers, valuation runs, and posting
valuation vouchers to accounting) is a **prototype**, not in the live schema — see
[../../../features/inventory-valuation/](../../../features/inventory-valuation/).

## Cross-module dependencies

Documents in **Workflow & Documents** generate these transactions; the item's `*Ledger` mappings
tie movements to **Accounting**. See [../../cross-module-links.md](../../cross-module-links.md).

> `action` (CREATED/UPDATED/DELETED/LINKED*) is a **deprecated** field — do not build on it.
