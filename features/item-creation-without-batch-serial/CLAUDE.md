# Working context — Item creation without mandatory batch / serial

Asana task (existing): https://app.asana.com/1/434866962028513/project/1208558476392934/task/1216785341363930
— "Allow item creation with tracking method only", Inventory project, assignee Twinkle, created 2026-07-22.

## Module(s) touched

**Inventory** only. No cross-module ripple — accounting ledger mappings, CRM and
Workflow & Documents are untouched by the creation-time change itself. The one
downstream reader worth naming is document line-item batch selection (`birds`
`check-batch-in-document-required`), which already handles the "no batch" case
via `batchOptionalFlag` and the per-billType `manageInventory` flag.

## Docs read (grounding done 2026-08-17 — do not re-read unless stale)

- `docs/modules/inventory/overview.md`
- `docs/modules/inventory/schema.md`
- `docs/modules/inventory/transactions.md` (batch/serial targeting section)
- `docs/glossary.md` (`trackingMethod`, `batch`, `serial`, `strictControl`, `warehouse`)
- `docs/repo-map.md`

## Canonical terms to reuse (from glossary.md / fence)

- `trackingMethod` — `NONE` · `BATCH` · `SERIAL` · `BATCHWISESERIALS`. Immutable once non-`NONE`.
- `batch` (`batches` model), `serial` (`serials` model, status `AVAILABLE`/`BLOCK`/`UNAVAILABLE`/`ARCHIVED`)
- `isStockManaged`, `strictControl`, `initialStock`, `stock`, `stockInHand`
- `inventoryOptions.manageWarehouses`, `inventoryOptions.strictInventoryControl`,
  `inventoryOptions.batchOptionalFlag` (`block`/`ignore`/`blockignore`, default `blockignore`)
- Do **not** invent terms like "empty item", "unstocked item", "placeholder batch".

## Verified current behaviour (code-grounded 2026-08-17)

The mandatory-batch/serial rule is enforced at **two layers**, not one:

1. **Frontend — `lydia`** `src/schemas/inventory.js`, `stockManagementDetailsFormSchema`,
   the `.test('tracking-method', ...)` block:
   - `!isEdit && trackingMethod === 'BATCH' && !batches?.length` → `inventoryForm.batchTrackingRequired`
   - `!isEdit && trackingMethod === 'SERIAL'` with no serials (root `serials[]`, or
     `warehouses[].serials` when warehouse-managed) → `inventoryForm.serialTrackingRequired`
   - Both guarded by `!isEdit`, so **edit already permits zero batches/serials**.
   - `BATCHWISESERIALS` is not covered by this test — but it is also hard-disabled in the
     dropdown (`StockManagementDetailsForm.jsx`), so it is not a live path.
   - Form step: `src/components/forms/inventory/steps/StockManagementDetailsForm.jsx`
     (`BatchFormList`, `Serials` widgets); strings in `src/i18n/{en,ar}/inventoryForm.ts`.

2. **Backend — `serana`**, reached on every UI create via
   `src/services/inventories/inventories.hooks.js` → `before.create` →
   `beforeManualInventoryCreate()` (`src/hooks/before-manual-inventory-create.js`):
   - `trackingMethod === 'BATCH'` → `src/utils/process-inventory-batch.js`:
     `if (!data.batches || !data.batches.length) throw BadRequest('Batch is required')`
   - `trackingMethod === 'SERIAL'` → `src/utils/process-inventory-serials.js`:
     - warehouse-managed: throws `'Warehouses are required for serial tracking when
       warehouses are managed'`, then `'Each warehouse must have serials for serial tracking'`
     - not warehouse-managed: throws `'Serials are required for serial tracking '`
   - Same processors also enforce: `manageInventory` on, `itemType === 'product'`,
     not a package, and the `batch-wise-tracking` **paywall accessibility** check
     (serial tracking reuses the `batch-wise-tracking` accessibility key).

So a frontend-only fix is **not sufficient** — the serana throw must be relaxed too.

## Other current-behaviour facts that constrain the change

- `trackingMethod` is immutable once non-`NONE` (`initialValue?.trackingMethod !== 'NONE'`
  disables the dropdown on edit). An item created as `BATCH`/`SERIAL` with nothing in it
  cannot be walked back to `NONE`.
- `before-manual-inventory-create.js` forces `data.warehouses = []` when
  `trackingMethod === 'BATCH'` — batch items never carry the warehouse cache array.
- Patch-side batch guard: switching an existing item to `BATCH` when `stockInHand > 0`
  requires `batches[0].initialStock >= stockInHand`. Creation-with-zero-stock sidesteps this.
- `serana` `src/hooks/check-batch-tracking.js` / `inventorySerials/checkSerialTracking.js`
  gate the later add-batch / add-serial routes on `trackingMethod === 'BATCH'` / `'SERIAL'`
  respectively — so the "add them later" path the task asks for already exists and is
  correctly gated.
- Document-time: `birds` `src/helpers/check-batch-in-document-required.ts` requires a batch
  whenever the resolved `manageInventory` flag is `UPDATE`; `BLOCK`/`IGNORE` are optional
  depending on `batchOptionalFlag`. A zero-batch item therefore stays unusable on
  stock-updating documents until a batch exists — which is the correct outcome, but is the
  behaviour to state explicitly and test.

## Secrets

Reference `.env` values (`GITHUB_PAT`, `ASANA_PAT`, `METABASE_API_KEY`, `METABASE_URL`,
`RAILWAY_TOKEN`) **by name only**. Never print, echo, paste or embed their values.
