# Inventory Valuation & COGS — Product & Engineering PRD

**This file is the canonical source of truth for the Inventory Valuation feature.** Every finalized decision and every shipped (or shelved) implementation should be reflected here — the "why," not just the "what" — so any future session can pick this up cold without re-deriving context from chat history. Update it as a normal part of finishing a decision or a build, not as a separate approval step.

**Last updated:** 2026-07-21

---

## 0. Why this feature exists

Refrens' Inventory and Accounting modules don't talk to each other today. A business can track stock quantities in Inventory and post ledger/voucher entries in Accounting, but nothing connects the two — so there is no accurate, system-computed Cost of Goods Sold (COGS) or inventory asset valuation on the books. This feature closes that gap: it values stock (WAC/FIFO/LIFO/SI), computes COGS on every sale, and posts the resulting asset/expense movements into the existing accounting ledgers, without disturbing the document-level accounting (invoices, purchase bills, GST) that already works today.

## 1. Two tracks — read this before anything else below

This initiative has always run on two parallel, distinctly-scoped tracks. Every decision and status note further down is tagged with one of these:

| Track | What it is | Where it lives |
|---|---|---|
| **LAB** | A working, deployed local prototype (`valuation-prototype` repo) used to design and validate the valuation engine, posting model, and UX *before* touching real production code. Has its own git history, tests, and a live Railway deployment. | `C:\Users\testr\Refrens\Claude\Inventory Valuation\valuation-prototype` |
| **PROD** | Decisions about how the real Refrens backend (`serana`/`saturn`/`talos`/`fence`) needs to change to ship this feature for real. Made **without direct access to those repos from this environment** — grounded in an earlier session's research (`docs/prod-implementation-map.md`) that *did* have repo access, now secondhand. Nothing in this track has been implemented. | Design-only; no code |

A superseded older prototype iteration also exists at `C:\Users\testr\Refrens\Claude\Inventory Valuation\prototype\` (pre-fork, largely historical — `valuation-prototype` is the actively developed fork all current work targets). Two standalone HTML artifacts also live at the `Inventory Valuation` root: `inventory-valuation-flow-explorer.html` (an interactive flow-explainer built early on) and `valuation-ux-mockup.html` (a "Post to Books" UX mockup, §5.6).

## 2. Core concepts (glossary)

Full glossary lives in `valuation-prototype/CONTEXT.md` — summarizing the load-bearing terms here:

- **WAC / FIFO / LIFO / SI** — the four costing methods. WAC and FIFO/LIFO operate on a flat or layered cost pool per item; SI (Specific Identification) keys pools by `(item, batch/serial)` and is mandatory (never optional) for batch/serial-tracked items. LIFO is books-postable only outside jurisdictions where it's disallowed (India: Ind AS 2) — always previewable as a lens everywhere.
- **UPDATE / BLOCK / IGNORE** — the fixed, per-billType stock-effect enum every sales/purchase document type carries. `UPDATE` moves on-hand quantity (and feeds valuation); `BLOCK` reserves Committed Stock only; `IGNORE` touches nothing.
- **Opening Boundary** — the date at which an item's (or a late-joining item's) manually-asserted opening qty×cost becomes its first valuation layer. Never a historical replay (ADR-0003) — always a current, human/payload-asserted snapshot.
- **Valuation Scope** — the forced-decision principle that every stock-managed item is visibly either tracked or excluded, never silently missing.
- **Push / Confirm** — the manual, bulk action that turns staged valuation math (COGS, asset movements) into real posted voucher/ledger entries. Nothing hits real books before a push.
- **Strict Mode (`strictControl`)** — the pre-existing (valuation-unrelated) per-item negative-stock-prevention flag. Now the sole trigger for valuation tracking (§5.12).

## 3. Architecture Decision Records (ADRs)

All **LAB**, all Accepted, all in `valuation-prototype/docs/adr/`:

| ADR | Decision |
|---|---|
| [0001](valuation-prototype/docs/adr/0001-prod-shaped-contracts-in-sqlite.md) | Prod-shaped Serana/Saturn contracts modeled inside local SQLite, not a from-scratch schema |
| [0002](valuation-prototype/docs/adr/0002-saturn-carries-value-never-quantity.md) | Saturn (real ledger system) only ever receives value — quantities never cross into the books |
| [0003](valuation-prototype/docs/adr/0003-no-historical-replay-migration-in-production.md) | Production never reconstructs opening values by replaying history — always a manually asserted current snapshot |
| [0004](valuation-prototype/docs/adr/0004-periodic-summary-vouchers-not-per-document.md) | Perpetual compute in Serana, monthly summary vouchers in Saturn (not per-document posting) |
| [0005](valuation-prototype/docs/adr/0005-valuation-requires-strict-mode.md) | Valuation requires Strict Mode on, and locks it on permanently once valued |
| [0006](valuation-prototype/docs/adr/0006-lifo-is-a-lens-never-a-books-method.md) | LIFO is a lens, never a directly-postable books method *(refined by §5.7 — jurisdiction-gated, not universally blocked)* |
| [0007](valuation-prototype/docs/adr/0007-month-bucketed-valuation-vouchers.md) | One confirm posts month-bucketed vouchers, never one cumulative journal |

`docs/prod-implementation-map.md` (dated 2026-07-03, **PROD**, secondhand) is the grounding research doc for every PROD-track decision below — real schema/file citations, verified against actual repo clones at the time it was written, not re-verifiable from this environment today.

---

## 4. Decisions log

Organized by topic. Each entry: **Decision**, **Why**, **Status**. Superseded decisions are marked explicitly rather than deleted, so the reasoning trail stays intact.

### 4.1 Valuation method policy — **LAB, implemented**
- Valuation method is a **per-item property with a business-level default** (Tally precedent), not business-wide-only. Batch/Serial items default to SI (non-optional); everything else defaults to the business default (itself WAC).
- Method is **frozen once set** — changeable only prospectively from a future FY boundary, at most once per FY.
- **Why:** matches how real accounting software (Tally/Zoho/QuickBooks) already handles per-item costing, and prevents retroactive method-switching from silently rewriting historical COGS.

### 4.2 FY boundaries and period locks — **LAB, implemented**
- **No period locks in V1** (deliberate scope cut) — the only replay floor is the Opening Boundary. Past-FY documents are read-only for editing; their chain stays readable.
- **FY-close forces a final push** of all pending transactions dated in that FY before lock takes effect, so nothing is ever stranded un-pushed in a closed period.

### 4.3 Paywall / plan-gating model — **PROD, decided, not implemented**
- Voucher/ledger/report viewing is **always Accounting-plan-gated**, no exceptions.
- **New businesses**: per-item valuation-method field exposed **ungated** — the system silently stages the valuation chain from the first transaction (zero migration risk, no prior history to reconcile). Dashboard/push/vouchers stay Accounting-plan-gated regardless of business age.
- **Existing businesses**: the "Enable Inventory Valuation" activation flow is only reachable once already on an Accounting plan with sync enabled — no dead-end wizard on Inventory-only plans.
- The Valuation Dashboard (staging view + push action) is gated identically to vouchers/reports — it's a pre-voucher view of the same accounting data (COGS, asset value), so exposing it on Inventory-only plans would undercut the same upsell the voucher/report gate protects.
- **Why:** keeps the existing Accounting-plan upsell intact; new businesses get the feature "for free" (in compute terms) precisely because there's zero migration risk for them, not because the paywall was relaxed.
- **Note (§4.12):** this gate is orthogonal to when tracking *starts* (now driven purely by item-level `strictControl`, §4.12) — don't conflate the two.

### 4.4 Staging + push architecture — **LAB, implemented** (core mechanics); **PROD, decided**
- A staging collection holds every UPDATE-triggering document's calculated transaction (layer/WAC math, cascade-on-edit) **without touching real vouchers**.
- A **manual, bulk "push to vouchers" action** (not scheduled, not selective) materializes everything pending into real voucher/ledger entries.
- Editing a document **before** push updates the staged transaction directly (cheap). Editing **after** push triggers reverse/remove/re-add of the posted entries, reusing the existing `reverse-entries` service.
- Flagged/missing-cost items are **pushed anyway with a placeholder value** ("allow with warning") — never auto-excluded, never blocking.
- The Dashboard replaces an earlier "reconciliation wizard" idea — since nothing hits real vouchers until push, the business can compare calculated opening value against actual Stock-in-Hand right on the Dashboard before committing.
- **Why:** matches how real bulk-accounting workflows already behave (draft → review → commit), and avoids forcing a reconciliation ceremony before any real risk exists.

### 4.5 Ledger Push Spec (posting granularity) — **PROD, decided (revised) — ✅ now matches what's built**
- Two layers, never conflated: **Layer 1** (document accounting — invoice/purchase-bill vouchers, existing, unchanged, posts on save) vs. **Layer 2** (valuation accounting — inventory-asset + COGS lines, new, posted only on push/confirm, month-bucketed `IVAL-<business>-<YYYYMM>`, no GST, no quantities per ADR-0002).
- **Decided granularity**: LEDGER-ROLE-PRESERVING (one voucher/month, distinct roles) — generic `STOCK_IN_HAND`/`COGS`/`INVENTORY_ADJUSTMENT` legs only, **never party ledgers**.
- DBN rate-vs-cost variance → posts to the existing Suspense A/c group, flagged for accountant reconciliation.
- Pushes nothing for: warehouse transfers, BLOCK/IGNORE/BLOCK_IGNORE docs, the FY rollover bridge, the package wrapper itself, excluded items, any non-UPDATE document.
- **✅ Resolved (was previously flagged as diverging)**: the original decision wanted vendor/client-tagged manual adjustments to post their own `Cr Vendor A/c`/`Dr Client A/c` line through the push ("PARTY LEDGERS PRESERVED") — the LAB engine (`confirmValuation.ts`) never implemented this, and per §4.14/Part R below, it now never should. Manual adjustments never touch party ledgers, regardless of whether a party is tagged on them for reference — real party-ledger movements only ever come from real documents (Purchase Bill/Sales Invoice/Credit Note/Debit Note), via the existing, unchanged document-accounting hook. What's already built (generic legs only) is now the confirmed-correct design, not an unbuilt shortcut.

### 4.6 Push & re-post model — **LAB, implemented** (supersedes an earlier ADR-0007-style month-voucher re-versioning idea)
- Two paths, keyed on whether a movement's effect was already pushed:
  1. **NEW/unpushed** → on push, ADD new entries only. Prior push vouchers untouched. A business can push many times within a month; each push appends.
  2. **A document that changes after its effect was already pushed** → REVERSE the whole push-batch voucher that contained it, then RE-POST that batch corrected. Grain = **per-push-batch** (chosen over per-document or whole-month-replace).
- Rejected alternatives: whole-month re-versioning ("replace the month"); "post only the adjusting delta."
- **UI implication**: one merged screen (not separate Post-to-Books + Shockwave) — month-wise rows, "In books" (immutable) vs. "To push" (pending), single "Review & post" action; a backdated edit to an already-posted batch shows as an inline change badge, not a separate surface. Mockup: `valuation-ux-mockup.html` at the repo root.

### 4.7 Auto-post vs. manual-push split + LIFO jurisdiction gating — **LAB, implemented, merged to `main`** (PR #24)
- **Auto-posts immediately at document save** (stock-managed items only): Purchase bill → `Dr Stock in Hand / Cr Vendor` (replaces the old `Dr Purchases / Cr Vendor`); DBN linked to a specific original purchase → `Dr Vendor / Cr Stock in Hand`. Non-stock-managed items keep the old `Dr Purchases / Cr Vendor` shape.
- **Stays in the manual push**: COGS on sales, CDN reversal, all manual adjustments, opening stock (credits Inventory Adjustment, not Purchases).
- **Consequence**: the `PURCHASES` ledger role retired from the push engine entirely — narrowed from 3 leg-pair-types to 2 (COGS, Adjustment).
- **Two Stock-in-Hand writers now exist on purpose** — deliberately accepted, breaking a prior single-writer invariant. `/books` nets Stock-in-Hand across both writers correctly.
- **LIFO**: WAC/FIFO/LIFO user-selectable; SI stays automatic for BATCH/SERIAL items. LIFO postability is **jurisdiction-gated** (new `ScenarioParams.country`, defaults `'IN'`) — blocked as view-only lens for India (Ind AS 2 / ADR-0006), postable elsewhere by default. Three independent pre-existing "LIFO never allowed" guards all had to become country-aware (`confirmValuation.ts`, `activation.ts`, `routes.ts`'s `parseItemValuationMethod` — the last one was silently stripping LIFO back to WAC on save, the real reason LIFO never stuck).
- **Why:** removes needless friction for real purchases/DBN (deterministic cost, no reason to wait for a push) while keeping the harder valuation-method-dependent postings (COGS) in the ceremony where staleness/re-versioning matters.

### 4.8 Opening entry design — production version — **PROD, decided, not implemented**
- Debit side always Stock-in-Hand. **Credit side split by where the on-hand quantity originally came from**: portion traceable to a Purchase Bill this FY → credit the **dedicated COGS ledger** at its real recorded rate; portion with no traceable origin → credit **Inventory Adjustment A/c** at the item's reviewed cost.
- Reconstruction bounded to the current FY only (`FY-start qty = current on-hand − net FY-to-date movement`, oldest-first consumption assumption within that window). Fallback on inconsistency: credit the whole opening value to Inventory Adjustment A/c, flagged for review.
- `BATCH`-tracked items skip reconstruction — each existing batch becomes one opening FIFO layer directly.
- One combined "Opening Stock" voucher entry per activation (one debit line per item, split credit lines), not one entry per item.
- **Note:** this production-track credit-split design is a heavier reconstruction than the simpler LAB opening entry used today (§4.12 Decision 6: fixed `Dr Stock in Hand / Cr Inventory Adjustment A/c` for every opening entry in the lab and in the current PROD activation-flow decision, §4.12). Flagging the discrepancy rather than silently picking one — §4.12's simpler fixed-pair design is the one actually finalized for activation; this section's source-split design predates that and would need reconciling if ever built.

### 4.9 Special-case flows — **PROD, decided, not implemented**
- **Package/composite items**: no independent ledger/valuation identity — a sale/purchase line explodes into one consumption event per child item; the resulting voucher has multiple line pairs, not one.
- **Warehouse transfers**: no ledger/voucher entry in Phase 1 (Stock-in-Hand is one global account per item, not per-warehouse). Chain-only tracking node needed so per-warehouse reporting stays possible later.
- **Stock reconciliation**: same ledger mechanics as Manual Adjustment IN/OUT — direction derived from counted-vs-expected qty (not user-chosen), always no-party, gain defaults to current average cost. Narration says "Stock Reconciliation" for auditability even though mechanics are identical.

### 4.10 Document migration, activation & paywall — **PROD, decided, not implemented**
(Originally Part E.) Covers the same ground as §4.3/§4.4/§4.8 from an earlier pass, plus:
- **Existing-business activation UX**: Settings → Inventory → Enable Valuation (no proactive banner); single screen, one primary decision (default method, WAC pre-selected); live-computed summary (item/value totals, items missing cost price — informational, never blocking); ledger backfill on the same screen; CSV round-trip for cost review at scale; lands on the Dashboard with "you're set, push whenever ready."
- **Note**: this activation-screen UX is superseded in its *scoping* by §4.12 Decision/§D below (the screen now only walks items already `strictControl: true`, not "every stock-managed item, default them on") — the low-friction *intent* here survives, the "no per-item review" *mechanism* doesn't.
- **Schema-grounded corrections** (from real-repo research, now unverifiable from this environment): dedicated `costOfGoodsSold` account group already exists (use it, don't double up Purchase Ledger); `stockJournal` voucher type already exists (use it, don't invent a new type); `inventorytransactions.transactionType` enum confirmed exactly `['IGNORE','BLOCK','BLOCK_IGNORE','UPDATE']`; `inventories.{salesLedger,purchaseLedger,inventoryLedger,costPrice,avgCostPrice}` confirmed to already exist as assumed.

### 4.11 COGS tracks the UPDATE-flagged transaction, regardless of billType — **PROD, decided (revised), implementation deferred**
- **The baseline mechanism (unchanged, confirmed)**: valuation computes COGS from *any* `inventorytransactions` row with `transactionType: UPDATE`, regardless of which document (or manual adjustment) produced it. Today's billType config (Invoice, Proforma, DC, PO, Purchase, etc., each independently set to `UPDATE`/`BLOCK`/`IGNORE`) has no restriction — a business can set multiple sales-side billTypes to `UPDATE` simultaneously.
- **Considered and rejected**: (A) COGS always follows Invoice, DC just moves quantity — breaks the moment Invoice precedes its fulfilling DC (Balance Sheet misstatement, not a timing nuance). (B) COGS follows whichever doc is `UPDATE`, with new DC↔Invoice linkage + post-fulfillment edit-lock — wins on every scenario in a 13-scenario comparison, but was originally set aside for requiring new engineering.
- **Revised decision — no restriction required.** The original "Approach C" gate (valuation only enabled if Invoice is the sole sales-side `UPDATE` document) is **superseded**. Confirmed instead: COGS/valuation simply tracks whichever transaction is `UPDATE`-flagged, with zero precondition on billType configuration, for three reasons — (1) an Invoice-only restriction excludes real bill-then-ship businesses, not just an edge case; (2) revenue recognition (Invoice's own voucher, already independent of its stock-effect setting) and stock/COGS impact (driven by whichever transaction is `UPDATE`) are legitimately independent concerns, never required to ride the same document; (3) if a business misconfigures multiple billTypes to `UPDATE` simultaneously (double-counting stock), that's the business's own configuration problem, not the valuation engine's to detect or prevent.
- **What this means Approach B's rejected cost turns out not to require**: per-sale margin doesn't need DC↔Invoice linkage once COGS just follows whichever document is `UPDATE` (that document already carries its own line items); edit/cancellation correctness doesn't need a new lock since the existing reverse+recreate machinery already operates on the transaction row itself, regardless of which document created it.
- **What this eliminates as a concern**: no Invoice-only activation precondition, no "can't flip DC to `UPDATE` while valuation is enabled" enforcement, no V1 exclusion for ship-before-bill businesses — they can enable valuation immediately, same as bill-then-ship businesses.
- **What's explicitly accepted as out of scope**: double/multi-`UPDATE` misconfiguration double-counts stock and valuation output — accepted as-is, not validated against, not the engine's problem. `MANUAL_ADJUSTMENT` remains the route for genuinely unbilled dispatches, no longer for gate-safety reasons (there's no gate) but as ordinary good practice (see §4.14's manual-adjustment standardization).
- **Open items**: exact production billType enum/classification (needed for labeling, not gating); re-verify the baseline claims directly once repo access exists (`sync-document-with-voucher-entries.js` fires independent of stock-effect; `manage-linked-document-inventory-transaction.js`'s reverse+recreate operates on any UPDATE-linked row, not just Invoice-originated ones) — everything here is currently a secondhand paraphrase.
- **Purchase side is NOT symmetric with this — a real gate still applies, decided as a direct follow-up.** Two purchase-side billTypes can carry an item (Purchase, Purchase Order); today PO creates no journal entry at all even when its stock-effect is `UPDATE`, while Purchase auto-posts `Dr Stock in Hand / Cr Vendor` at save time (Part J). Considered: a Goods Received Not Invoiced (GRNI) clearing account letting PO auto-post `Dr Stock in Hand / Cr GRNI` when it's the `UPDATE` trigger, with the later Purchase Bill posting `Dr GRNI / Cr Vendor` instead of touching Stock-in-Hand again — **rejected as unnecessary complexity** (users may or may not link a Bill to a specific PO, may change UPDATE/BLOCK/IGNORE anytime, so the needed linkage is ongoing engineering, not a one-time decision). **Decided instead: Purchase's stock-effect must always be `UPDATE`; PO's can never be `UPDATE`** (only `BLOCK`/`IGNORE`), for any valuation-enabled business — because unlike Invoice, Purchase Bill's auto-post directly touches Stock-in-Hand, so a second `UPDATE`-flagged purchase-side document risks real double-posting, not just a business-owned misconfiguration. Real-world gap acknowledged (goods-receipt-before-billing businesses will see understated on-hand stock during that lag) but judged narrow/low-severity — the failure direction is conservative (can't oversell), and a cheap workaround exists (create the Purchase Bill provisionally at receipt time, edit once the real invoice lands). **Migration**: existing businesses must set Purchase to `UPDATE` (and PO off it) before activation, surfaced clearly, no auto-fix; new businesses get Purchase auto-set to `UPDATE` and locked, with PO's `UPDATE` option structurally never offered. This supersedes the original Approach C's purchase-side clause ("at most one purchase-side billType `UPDATE`, not required to specifically be Purchase") — full detail and revision history in the plan-mode file's Part K.

### 4.12 Strict Mode hard-linking & the finalized activation/tracking flow — **PROD, decided (revised), implementation deferred**
The most recently finalized decision set — supersedes an earlier draft of this same topic. Full text (context, all decisions, the complete A–G flow, open items, verification, and a revision-history note) lives in the plan-mode file: `C:\Users\testr\.claude\plans\can-you-create-a-iterative-shamir.md`, Part Q. Summarized:

1. **Source of truth for tracking = item-level `strictControl: true`, alone.** Valuation never reads the business-level `inventoryOptions.strictInventoryControl` flag directly — that flag stays exactly what it already is (Strict Mode's own pre-existing, valuation-unrelated gate on whether `strictControl` can be set at all).
2. **Hard link**: `strictControl` can only be `true` when `isStockManaged` is `true`.
3. **Cascade rule** (two states, no matrix): not-yet-tracked item → turning `isStockManaged` off auto-clears `strictControl` silently (never auto-restores); already-tracked item → turning either off is blocked outright.
4. New items never default `strictControl` on, even in a brand-new business — deliberate opt-in always required.
5. **Two new nullable timestamp fields**, replacing any reliance on a lab-only `VALUED`/`EXCLUDED` scope concept (no such field is planned for the real item schema):
   - **Business-level `inventoryOptions.valuationActivatedAt`** — null until the business completes its one-time bootstrap sweep (existing businesses only; new businesses treat this as always-set from day one).
   - **Item-level `valuationActivatedAt`** — null until that item's own `OPENING_STOCK` event posts; set atomically with it. Locks `strictControl`/`isStockManaged` permanently and marks "not a first-time activation" for any later flip.
6. **Opening entry ledgers, fixed everywhere**: `Dr Stock in Hand / Cr Inventory Adjustment A/c`, system default, **not user-editable (for now)** — applies uniformly to fresh item creation, the existing-business bulk sweep, and later late-joins alike. *(This is the simpler, currently-authoritative opening-entry design — see the reconciliation note under §4.8.)*
7. **Opening value is trusted directly from whatever payload accompanies the `strictControl: true` transition** — uniformly across dashboard manual entry, bulk CSV upload, and API. No pending/review queue anywhere. This is a deliberate, explicitly-flagged loosening of a literal reading of ADR-0003's "manually asserted" language (satisfied by any creation channel's explicit fields, not strictly an interactive confirm-click).
8. **Existing-business activation flow** re-scoped: the "Enable Valuation" screen only walks items *already* at `strictControl: true` (not "every stock-managed item, default them on"). **Late-join is not a separate mechanism** — any later `strictControl` flip, on any single item, at any time, runs the identical trigger.
9. Open items: whether the business-level field should be set even over zero qualifying items on first run; exact per-creation-path payload mechanics (dashboard/CSV/API) still need engineering-level confirmation. (§4.11's *sales-side* Invoice-gating was superseded, but its *purchase-side* gate — Purchase always `UPDATE`, PO never `UPDATE` — is a live precondition again, alongside this Part's Strict Mode gating; both are independent preconditions for "can this business/item be valued," worth a combined checklist when implementation starts.)

### 4.13 Scalable valuation architecture — dimensional model, incremental replay — **LAB, partially built, not merged**
(Originally Part O, produced via `/tactics-board`.) A `ValuationKey = { itemId, batchId?, serialId?, warehouseId? }` abstraction generalizes item/batch/serial/warehouse pooling (SI already proved the pattern; this generalizes it to WAC/FIFO/LIFO too), plus per-`(key, month)` checkpointing so an edit only recomputes the items actually affected instead of a full-history replay. Category accounting is a stamped, point-in-time tag on postings (cost-center style), never a new GL account or a live join. Posting/rollup grouping is designed as a pluggable parameter so future warehouse-wise posting is a config change, not a re-architecture.
- **Status**: T1–T5 (the `ValuationKey` abstraction, keyed pools, generalized FIFO/WAC/LIFO, per-item checkpointing, scoped edit-invalidation) are **built** — commit `954972c` on branch `feat/scalable-valuation-engine-and-enable-redesign`, not yet merged to `main`.
- **Not started**: T6 (category tagging), T7 (warehouse dimension + pluggable posting-grouping), T8 (DB indexes), T9 (pagination/streaming), T10 (`BATCHWISESERIALS` — shipping decision intentionally left open), T11 (benchmark harness).
- **Why deferred sequencing (T1-T5 before T6+)**: T1-T5 alone already fix the two structural risks that matter most today (full-scenario replay cost, and edits to one item leaking into another's numbers); T6+ are additive dimensions layered on the same abstraction, not blockers to shipping T1-T5.

### 4.14 UX build-outs — **LAB, implemented, not all merged**
- **Adjust Stock drawer** (Part M) — replaced the generic "Post transaction" modal with a Refrens-style right-slide drawer (Incoming/Outgoing, Adjusted Quantity, Rate, Vendor, Reason-to-adjust), mapped onto existing `SourceEvent` fields with no server/schema changes. **Merged to `main`** (PR #25, commit `8a87ba6`).
  - **Standardization decided, not yet built** (Part R): the party field's type must follow the specific reason, not just direction (today's "Returned" wrongly shows Vendor instead of Client); a new "Returned to Vendor" outgoing reason closes the matrix symmetry gap; every reason gets a locked "Adjustment Ledger" field defaulting to the item's `adjustmentLedger`; and — the key rule — a selected party is informational only, never a ledger posting, with an explicit disclaimer shown so users don't mistake it for a real vendor/client transaction. "Sold" is retagged `docType: 'MANUAL'` (drops its misleading, never-acted-on `'INVOICE'` tag). Full detail and rationale in the plan-mode file's Part R.
- **VoucherEntryCard redesign** (Part N) — replaced two ad-hoc, misaligned Dr/Cr tables in the confirm modal with one shared, fixed-column-width component (Financial Year/Date/Reference info row, Debit/Credit sections, balance indicator). **Merged to `main`** (same PR #25, same commit).
- **Enable Valuation flow rebuild** (Part P) — replaced the static placeholder `EnableValuationPage` with the full Claude Design–sourced flow (3-step drawer: Defaults → Item data → Confirm; `LedgerSelect` component; simulated CSV upload; post-enable dashboard landing). **Built, not merged** — commit `954972c` on `feat/scalable-valuation-engine-and-enable-redesign`.
  - **2026-07-21 follow-up (uncommitted on the same branch)**: the confirm step's two ledger fields ("Inventory asset" / "Offset account") are now **read-only, locked displays** instead of editable dropdowns — matches §4.12 Decision 6 (opening-entry ledgers are a fixed system default, not user-editable for now). `LedgerSelect` gained a `readOnly` prop; the now-unreachable "advanced note" (only fired when the offset account was changed from default) was replaced with a plain fixed-default note.
- **Refrens header swap (in progress, uncommitted, undocumented anywhere else)**: `AppTopbar` (search+avatar) is being replaced by a new `RefrensHeader` component — a decorative, non-functional top nav ported from the same Claude Design mockup's real-app chrome, purely so the prototype visually reads as sitting inside the real product. `AppLayout.tsx`/`styles.css` updated to wire it in. **Not finished/verified as a deliberate task — flagged as mid-flight work inherited from an earlier session, not yet reconciled with any Part.**

---

## 5. Lab prototype — current implementation status

**Repo:** `C:\Users\testr\Refrens\Claude\Inventory Valuation\valuation-prototype` (fork of `vaidik2412/inventory-valuation-lab`, deployed to Railway).

**`main` HEAD:** `350ec9a` (merge of PR #25 — Adjust Stock drawer + VoucherEntryCard, §4.14).

**Current working branch:** `feat/scalable-valuation-engine-and-enable-redesign`, one commit ahead of `main` (`954972c` — §4.13's T1-T5 + §4.14's Enable Valuation rebuild), **not yet opened as a PR / not merged**, plus uncommitted changes on top (the read-only-ledger fix and the in-progress header swap, both under §4.14).

**⚠️ Live-Atlas footgun**: this repo's `.env` `MONGODB_URI` points to a real, shared MongoDB Atlas cluster (`vaidik-test.x3pzzrc.mongodb.net`) — the same one an earlier session accidentally wrote test data into (see `plans/lessons.md`). `npm run dev` / `npm run serve` connect to it directly and run write-on-boot backfills. **Never run those directly for ad-hoc verification** — use an isolated in-memory Mongo + in-memory SQLite scratch server instead (`createInitializedDatabase(':memory:', { useMemoryServer: true })`), exactly as done for the §4.14 follow-up verification.

Merged-to-`main` feature timeline (oldest → newest; see `plans/todo.md` for full narrative detail through 2026-07-07, and `git log` for everything after):
`main` history through month-close/activation → routed pages → product-shaped workspace → prod-faithful confirm ceremony → Books page/confirm-preview/freshness banners/deploy hardening → Scenario Library → testability polish → trust-hardening guards → committed-stock display → **valuation mockup pages (PR #23)** → **auto-post/LIFO-jurisdiction (PR #24, §4.7)** → **Adjust Stock drawer + VoucherEntryCard (PR #25, §4.14)**.

Not yet started in the lab: wiring the 3 mockup pages (Dashboard/Post to Books/Enable Valuation) to real data — explicitly deferred pending §4.13's engine work landing and stabilizing first.

## 6. Production — implementation status

**Nothing in the PROD track has been implemented.** §4.3, §4.8, §4.9, §4.10, §4.11, §4.12 are all design-only, awaiting real repo access before any code changes begin. Treat every file/function citation in these sections and in `docs/prod-implementation-map.md` as secondhand and unverified until confirmed against actual `serana`/`saturn`/`talos`/`fence` source.

## 7. Master open-items list

Consolidated from every section above — cross-referenced, not duplicated:

1. ~~§4.5 — LAB engine doesn't implement party-ledger-preserving push granularity~~ — **resolved** (Part R): manual adjustments never touch party ledgers, by design; the LAB engine's generic legs were correct all along.
2. §4.8 vs §4.12 — two different opening-entry designs exist in this document (source-split reconstruction vs. a fixed Stock-in-Hand/Inventory-Adjustment pair); §4.12's is the current, finalized one — §4.8 needs a formal supersession pass whenever PROD activation work actually begins.
3. §4.11 — exact production billType enum/classification and every real-repo citation (`sync-document-with-voucher-entries.js`, `manage-linked-document-inventory-transaction.js`) need re-verification once repo access exists. (The *sales-side* Invoice-gating restriction this item used to reference is superseded, no restriction there anymore — but a *purchase-side* gate now exists instead: Purchase always `UPDATE`, PO never `UPDATE`, with its own activation-time migration check for existing businesses.)
4. §4.12 — whether the business-level `valuationActivatedAt` should be set even over zero qualifying items on an existing business's first activation run; exact per-creation-path opening-payload mechanics (dashboard/CSV/API field shapes) still need engineering-level confirmation.
5. §4.13 — `BATCHWISESERIALS` shipping decision intentionally left open; T6-T11 not started.
6. §4.14 — the in-progress `RefrensHeader` swap is unfinished, uncommitted, and not tied to any tracked Part — needs a decision on whether to finish, formalize as its own Part, or discard.
7. General — §4.11's sales-side Invoice-gating was superseded (no precondition there), but its purchase-side gate (Purchase always `UPDATE`, PO never `UPDATE`) and §4.12's Strict Mode gating are now two independent preconditions for "can this business/item be valued" — worth a combined precondition checklist once PROD implementation actually starts.
8. §4.14 (Part R) — decided, not yet implemented in the lab: the reason→party-type fix, the new "Returned to Vendor" reason, and the locked Adjustment Ledger field all still need building in `AdjustStockDrawer.tsx`. Revisit-if-asked items intentionally left open: routing party-bearing reasons to real document creation (the fuller design considered and deferred), and per-reason (not just per-item) adjustment-ledger routing.

## 8. Related documents

- `valuation-prototype/CONTEXT.md` — full persona/terminology glossary for the lab.
- `valuation-prototype/docs/prod-implementation-map.md` — the grounding PROD research doc (secondhand, unverifiable from this environment).
- `valuation-prototype/docs/adr/000{1-7}-*.md` — the 7 accepted ADRs (§3).
- `valuation-prototype/PROTOTYPE.md`, `README.md`, `plans/todo.md`, `plans/lessons.md` — lab-specific build narrative, day-to-day task tracking, and incident/footgun notes (not decision rationale — that's this file's job).
- `prototype/docs/inventory-valuation-feature-plan.md` — an earlier (2026-07-13) consolidated doc covering roughly the same ground as §4 up through §4.7/§4.11. **Superseded by this file** — kept for historical reference only, not maintained further.
- `C:\Users\testr\.claude\plans\can-you-create-a-iterative-shamir.md` — the working plan-mode file this project has been iterating in session-to-session (Parts A–R, chronological). This PRD is the durable, topic-organized distillation of it; the plan-mode file remains useful for the full blow-by-blow context/rationale behind any given Part, especially Part Q's complete flow write-up (§4.12) and Part R's manual-adjustment standardization (§4.14).

## 9. Changelog

- **2026-07-21**: Initial version of this file created, consolidating the plan-mode file (Parts A–Q), the prior `prototype/docs` living doc (2026-07-13), and current `valuation-prototype` git/branch state into one topic-organized source of truth. Folds in the just-finalized Strict Mode activation/tracking revision (§4.12) and the same-day read-only-ledger UI fix (§4.14).
- **2026-07-24**: §4.11 revised — the original Invoice-gating decision (Approach C) is superseded. COGS/valuation now tracks whichever inventory transaction is `UPDATE`-flagged, regardless of billType, with no restriction on configuration required or enforced; misconfiguration is explicitly the business's responsibility, not the engine's. Cross-references in §4.12 and §7 updated to drop the now-obsolete "orthogonal precondition" framing against Part K.
- **2026-07-24 (same day, follow-up)**: §4.11 extended with a purchase-side decision that is deliberately *not* symmetric with the sales-side revision above — Purchase's stock-effect must always be `UPDATE` and Purchase Order's can never be `UPDATE`, for any valuation-enabled business, because Purchase Bill's auto-post directly touches Stock-in-Hand (unlike Invoice) and a rejected GRNI-linkage alternative was judged unnecessary complexity. Existing businesses must satisfy this at activation; new businesses get it auto-set and locked. §4.12 and §7 cross-references updated again to reflect that a real precondition (now purchase-side, not sales-side) sits alongside Strict Mode gating.
- **2026-07-24 (same day, second follow-up)**: Manual Adjustment standardization decided (Part R) — reason-linked party fields (Vendor/Client shown per specific reason, not just direction; fixes "Returned" wrongly showing Vendor; adds a new "Returned to Vendor" reason) are purely informational and never post to a party ledger, with an explicit in-drawer disclaimer; a locked "Adjustment Ledger" field is added to every reason, defaulting to the item's existing `adjustmentLedger`; "Sold" is retagged `docType: 'MANUAL'` (drops a misleading, never-acted-on `'INVOICE'` tag). This formally resolves §4.5's long-flagged party-ledger-preserving-push gap — the LAB engine's generic legs were correct all along, not an unbuilt shortcut. Not yet implemented in the lab.
