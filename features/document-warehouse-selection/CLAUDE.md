# Working context — Document-level warehouse selection

## Idea (raw)

Today, a business managing multiple warehouses must pick the warehouse on every line item of a
document, one by one — there's no document-level default. Some businesses also ship an order from
one warehouse but draw stock for different line items from different warehouses, so the "ship
from" location and the "stock source" per line item aren't always the same thing.

## Modules touched

- **Workflow & Documents** (primary) — the `invoices` document model, line items, and (today)
  no document-level warehouse/ship-from field.
- **Inventory** (primary) — `warehouses`, per-item `warehouse` selection, and the stock
  movements (`inventorytransactions`) that get generated from it.

## Docs read

- `docs/modules/workflow-documents/overview.md`
- `docs/modules/inventory/overview.md`
- `docs/modules/inventory/schema.md`
- `docs/glossary.md`
- `docs/cross-module-links.md`

## Canonical terms to reuse

- **`warehouse`** (Inventory) — physical stock location, `warehouses` collection. See
  [glossary.md](../../docs/glossary.md).
- **`inventorytransactions.warehouse`** — the warehouse a stock movement actually happened at.
- **`docId` / `docType`** — how a transaction links back to its source document.

## Code-grounded findings (talos, verified 2026-08-27)

Read `refrens/talos` `src/helpers/invoiceItems.js` directly (not documented in
`docs/modules/workflow-documents/schema.md` — that file doesn't mention `warehouse` at all, so
this was verified in source rather than guessed):

- **Per-line-item warehouse already exists**: `invoiceItems.warehouse` — `ObjectId ref: 'warehouses'`.
  This is the field the business picks manually today, once per line item. Confirms the idea's
  premise.
- **No document-level warehouse field exists** on `invoices` (confirmed: zero matches for
  `warehouse` in `talos/src/invoices.js`). A document-level default/ship-from warehouse would be
  new.
- **`invoiceItems.allocations[]` already carries its own `warehouse`** (`AllocationSchema.warehouse`,
  a String warehouse id) alongside `batch`, `quantity`, `serials[]`. This sub-schema already
  supports splitting a *single line item's* quantity across more than one
  batch/warehouse/serial-set — worth checking with engineering whether this is the existing
  mechanism for "one line item, stock from multiple warehouses," or dead/legacy weight, before
  designing a new one.

## Cross-module impact (from cross-module-links.md)

- `invoiceItems.warehouse` is what `inventorytransactions.warehouse` is ultimately set from when
  a document resolves to `UPDATE`/`BLOCK` (see
  [transactions.md](../../docs/modules/inventory/transactions.md)). Any change to how warehouse
  is chosen/defaulted at the document or line-item level has a direct, immediate effect on which
  warehouse's stock actually moves — this is not a UI-only change.
- The per-billType stock effect (`IGNORE`/`BLOCK`/`UPDATE`) is business configuration, not
  document-type-fixed — a document-level warehouse default needs to make sense regardless of
  which of the three effects ends up applying.

## Open questions for grilling (not yet resolved)

- Is "ship from" (address-level, one per document) the same concept as a document-level
  *default* warehouse for line items, or two separate fields that happen to often agree?
- When a line item's warehouse differs from the document's ship-from warehouse, does anything
  change downstream (e.g. delivery challan, e-way bill, GST place-of-supply)?
- Does `allocations[].warehouse` already solve "stock from multiple warehouses per line item," or
  is it unused for that today?

## Secrets

Reference `.env` values (`GITHUB_PAT`, etc.) **by name only** — never print or paste their values.
