Companions: TESTS-item-creation-without-batch-serial.md

# [Enhancement] Allow item creation with tracking method only

## Summary

A business that tracks stock by batch or serial cannot build its catalogue before stock arrives. Picking **Batchwise** or **Serial No.** forces a batch or serial there and then. So they invent placeholder data, or give up tracking.

**After this ships, a user can create a Batchwise or Serial No. item with nothing in it, and fill it later.**

## User Stories

- As a business owner, I want to create batch-tracked items before stock arrives, so I stop inventing fake batch numbers.
- As an integrator, I want to create tracked items over the API, so my catalogue sync stops skipping them.

## Scope

**In**

- Batchwise item with no batches
- Serial No. item with no serials, warehouse management on or off
- Same on the API, with `initialStock` and warehouse `quantity` rejected

**Out**

- ~~Editing Tracking Method after creation~~
- ~~Document behaviour for empty tracked items~~ — already correct
- ~~Bulk item upload~~ — no tracking-method column, creates **None** only
- ~~A serials API~~ — none exists
- ~~Batch + Serial No.~~
- ~~Backfill~~

## Verified Current Behavior

Checked against the running code on 17 Aug 2026.

- **Batchwise** needs one batch. **Serial No.** needs one serial. With warehouse management on, every warehouse row needs serials.
- The block runs twice: in the form, then on the server.
- Editing already allows zero batches and serials. Both rules are creation-only.
- The form hides opening stock for tracked items. An empty item is always `stock = 0`, `stockInHand = 0`.
- Adding batches and serials later already works in the app.
- The API accepts `trackingMethod` but rejects `batches` and `serials` as unknown fields. So it cannot create a tracked item today.

## The Change

Drop both rules, in the form and on the server.

- A **Batchwise** item may have no batches.
- A **Serial No.** item may have no serials. A warehouse row with no serials is valid.

**On the API**

- `trackingMethod` of `BATCH` or `SERIAL` is allowed on create.
- Reject `initialStock`.
- Reject warehouse `quantity`. Warehouse `reorderPoint` and `overstockPoint` stay allowed.
- `batches` and `serials` stay outside the contract. Add batches later through the batches API.

Stock only ever arrives as a batch or serial count.

Every other creation guard still fires — see Group D.

The new item has `trackingMethod = BATCH` or `SERIAL`, `stock = 0`, `stockInHand = 0`.

## Risk

**Low in the app.** It already reaches this state, through editing and through normal sell-down.

Watch during review:

- This opens tracked-item creation on the API for the first time — a new capability, not a wider one.
- A batch item made over the API can be filled through the batches API. A serial item can only be filled in the app.
- Serial tracking uses the same plan entitlement as batch tracking. Do not disturb that check.

No migration. No flag. Reverting restores both checks.

## Handling and Tests

**@Twinkle** — no backfill needed. Please confirm no report or export assumes a tracked item always has one.

42 cases in the attached companion.
