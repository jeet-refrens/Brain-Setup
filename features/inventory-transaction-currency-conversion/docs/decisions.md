# inventory-transaction-currency-conversion — Decision Log

Append-only. Record a reversal as a new entry that supersedes the old one; never edit an entry in
place. `F<n>` refs point at [code-findings.md](code-findings.md).

---

### D1 — Inventory values a movement at the document's rate (2026-08-18)

**Context:** Today `manage-inventory-stock.js:586-594` fetches its own live rate from riften keyed on
`transactionDate` and never reads the source document's `conversionRates` (F3). The document's rate
is the one the invoice total and the accounting voucher already used, and it is the one a user can
deliberately override (F2).

**Options:** (a) the document's stored `conversionRates[businessCurrency]`, with a riften lookup only
when the document has no rate; (b) keep today's live riften lookup and simply persist it; (c) the
document's rate strictly, with no fallback at all.

**Decision:** (a).

**Why & trade-off:** One sale should value the same on the invoice, in the ledger, and in stock. Under
(b) a user's deliberate override keeps being honoured by the invoice and the books and thrown away by
inventory — the disagreement Jeet raised, merely written down. (c) is the most auditable but leaves
older foreign-currency documents producing unvalued movements with no path forward. The trade-off
accepted: inventory now depends on a document field it did not previously read, so a document with a
bad rate produces a bad stock valuation. That is the correct coupling — the invoice is the source of
truth for what the sale was worth.

**Refs:** F2, F3; ADR 0001.

---

### D2 — Store the rate, not converted prices (2026-08-18)

**Context:** Accounting's house pattern stores both sides on every ledger leg: `amount`/`currency`
plus `book_amount`/`book_currency` plus `forex_rate`. The question was whether an inventory movement
should mirror that in full.

**Options:** (a) store the rate only; (b) store converted prices only; (c) store both, mirroring
accounting.

**Decision:** (a) — store the rate and the currency it converts into. Do not store converted prices.

**Why & trade-off:** Three reasons to diverge from the accounting shape here.

1. Converted prices do not scale with price fields. `features/inventory-net-price-on-transactions/`
   is adding `netCostPrice`/`netSellingPrice` to the same row. Book variants of every price field
   means eight price fields to keep in sync instead of four. One rate converts all of them, now and
   later.
2. Accounting's reason does not transfer. `book_amount` is an integer in minor units on a **total**,
   so rounding must be fixed once at write time or two reports disagree by paise. Inventory stores
   **unit prices** as floats, which are then multiplied by quantity and averaged. Rounding a
   converted unit price would introduce error rather than remove it.
3. A stored derived value drifts. Any patch that changes `costPrice` without recomputing its book
   twin leaves the row quietly self-contradictory.

Trade-off accepted: every reader must remember to multiply. That is the cost of not duplicating a
derived value, and it is mitigated by fixing the report paths in the same task (D15).

**Refs:** F6, F8; ADR 0002.

---

### D3 — Field names: `conversionRate` and `bookCurrency` (2026-08-18)

**Context:** `docs/glossary.md` already defines **bookAmount / bookCurrency** as "the business-currency
value of a line item, converted from `amount`/`currency` at `forex_rate`". Saturn uses snake_case;
talos uses camelCase.

**Decision:** Add two fields to `inventorytransactions`:

| Field | Type | Meaning |
|---|---|---|
| `conversionRate` | Number | Business-currency units per 1 unit of `currency`. So `business value = costPrice × conversionRate`. |
| `bookCurrency` | String, `fence/currencies` enum | The business currency this rate converts into. |

`currency`, `costPrice` and `sellingPrice` keep their present meaning and are not touched.

**Why & trade-off:** Reuses the established vocabulary instead of inventing a synonym, and matches the
direction the existing `priceFactor` already multiplies by, so no arithmetic changes meaning.
`bookCurrency` earns its place because a business can change its base currency — without it, a
currency switch silently reinterprets every historical row. Both terms must be added to
`docs/glossary.md` before this ships.

**Refs:** F2 (rate direction), F8; `docs/glossary.md`.

---

### D4 — Failed-rate handling is engineering's call (2026-08-18)

**Context:** The two existing paths disagree. The document hook refuses to persist a failed lookup and
raises Sentry, because storing 0 "silently makes the business-currency total zero" (F2). Inventory
turns the same failure into rate 1 and corrupts the average with no trace (F4).

**Decision:** Deferred to engineering judgment. Carried in the PRD and task Open Questions with a
stated working default: write the movement with `conversionRate` unset, raise Sentry, let stock quantity
move normally, and do not feed the average until the rate is filled.

**Why & trade-off:** Jeet's explicit call. The requirement that matters — today's silent rate-1
substitution is a defect (D14) — is settled; only the replacement mechanism is open.

**Refs:** F2, F4.

---

### D5 — Forward-only, with lazy filling of history (2026-08-18)

**Context:** A one-shot backfill was proposed on the grounds that the affected set is small and
precisely identifiable (`currency ≠ bookCurrency and conversionRate unset`) and that the repair input
already exists on each row's document.

**Options:** (a) backfill the rate and recompute affected averages; (b) backfill the rate only;
(c) forward-only, matching the sibling feature's D2; (d) forward-only plus lazy filling.

**Decision:** (d).

**Why & trade-off:** Jeet's call — too many businesses, with too many items, with too many
transactions, for a one-shot replay to be safe at this volume. Lazy filling gets the same end state
without a migration window. Trade-off accepted: history becomes correct gradually rather than at
once, and until a row is filled its report contribution stays as wrong as it is today (D6).

**Refs:** F1, F6; `features/inventory-net-price-on-transactions/docs/decisions.md` D2.

---

### D6 — An unfilled historical row counts as rate 1, and this stays open (2026-08-18)

**Context:** Under D5, a cross-currency row that has not yet been filled has no rate. A report has to
decide what it is worth.

**Options:** (a) treat as rate 1, exactly as today; (b) treat as rate 1 but show the user a coverage
note; (c) exclude unfilled rows from totals.

**Decision:** (a) as the working default, **and the question stays open** for team discussion.

**Why & trade-off:** (a) is the only option with no behaviour regression on day one — an unfilled row
contributes precisely what it contributes today, and reports get quietly more accurate as filling
proceeds. The cost is real and must not be hidden: the number stays wrong until that row is filled,
with nothing on screen saying so. (c) was rejected as worse — it understates totals and reads as data
loss to a user who knows the sale happened.

**Refs:** F6; PRD Open Questions.

---

### D7 — Lazy filling runs on the write path and a background sweep, never on report reads (2026-08-18)

**Context:** "Lazy" could mean filling when a report reads a row. Two facts rule that out: the raw
`$group` report paths cannot resolve or write a rate mid-pipeline (F6), and filling during a read
means one large report triggers thousands of writes and a burst of riften calls.

**Decision:** Fill in two places. (1) Any existing movement that is patched or reversed fills its rate
on the way through, since it is already in the hook. (2) A rate-limited sweep in the existing
integrity cron `serana/src/commands/crons/integrity/inventorystockintegrity.js`, which already walks
transactions.

**Why & trade-off:** Keeps reads read-only and the fill rate controllable. Trade-off: filling is not
on-demand, so a user cannot force their own history to be correct by opening a report.

**Refs:** F6, F11.

---

### D8 — A reversal reuses the rate stored on the original row (2026-08-18)

**Context:** `calculateAveragePrice` subtracts `price × quantity × factor` on reverse using the factor
resolved **at reversal time**, not the one used originally (F5). Same `transactionDate` normally
yields the same rate, so this usually agrees.

**Decision:** A reversal reads `conversionRate` off the row it reverses. It never re-resolves.

**Why & trade-off:** Re-resolving is how an average fails to unwind exactly. If the two lookups ever
differ — most obviously when one of them failed (F4) — the item keeps a permanent error that nothing
detects. Reusing the stored rate makes reversal exact by construction.

**Refs:** F4, F5.

---

### D9 — Editing a document's conversion rate re-triggers inventory (2026-08-18)

**Context:** `conversionRates` appears in neither `TXN_RELEVANT_DOC_FIELDS` nor
`TXN_RELEVANT_ITEM_FIELDS` (F10). So correcting a rate on an invoice restates the invoice total and
the ledger, and inventory does not notice.

**Options:** (a) add `conversionRates` to the watched fields so the movements restamp and the averages
unwind at the old rate and re-apply at the new one; (b) treat the rate stamped at creation as final
history.

**Decision:** (a).

**Why & trade-off:** D1 only holds if it keeps holding after an edit — otherwise the first rate
correction reintroduces exactly the disagreement this feature exists to remove. Trade-off: rate edits
now cause average churn, and a business that edits rates often will see averages move.

**Refs:** F10; D1.

---

### D10 — Document-less movements take a riften lookup at `transactionDate` (2026-08-18)

**Context:** `MANUAL`, `BULKMANUAL`, `TRANSFERSTOCK` and `RECONCILE` movements have no source document
and therefore no document rate.

**Decision:** `conversionRate` is 1 when the movement's `currency` already equals `bookCurrency`; otherwise
a riften lookup at `transactionDate`, stored on the row like any other.

**Why & trade-off:** The D1 fallback branch, applied to the case where the fallback is the only option.

**Refs:** F1, D1.

---

### D11 — A proforma release reverses at the original row's rate (2026-08-18)

**Context:** When a `BLOCK`ed document converts into one resolving to `UPDATE`, the original
transaction is patched to `BLOCK_IGNORE` so the reservation is released without double-counting. The
invoice may carry a different rate than the proforma did.

**Decision:** The release reverses at the rate stored on the original `BLOCK` row. The invoice then
applies its own rate on its own movement.

**Why & trade-off:** Direct consequence of D8. The reservation unwinds exactly, and the rate
difference lands on the invoice, where it belongs.

**Refs:** D8; `docs/modules/inventory/transactions.md`.

---

### D12 — Per-warehouse and per-batch averages get the same treatment (2026-08-18)

**Context:** `updateWarehouseData` maintains per-warehouse `avgCostPrice`/`avgSellingPrice`, and
`batches` carries its own pair. All run through the same averaging engine.

**Decision:** In scope, same rules throughout.

**Why & trade-off:** Same engine, same defect. Leaving batches out would make batch valuation disagree
with item valuation for the same stock.

**Refs:** F3; `docs/modules/inventory/schema.md`.

---

### D13 — A credit note stamps its own rate (2026-08-18)

**Context:** A credit note is raised later than the sale it reverses, often at a different rate.

**Decision:** It stamps the rate of its own document. No attempt is made to match the rate of the
original sale.

**Why & trade-off:** It is a separate document at a separate date, which is how accounting already
treats it. **Consequence that must be stated in the PRD, not hidden:** a full return at a different
rate will not restore the average to its pre-sale value. That residue is a genuine foreign-exchange
effect, not an error, and is an accepted edge case.

**Refs:** D1; `docs/cross-module-links.md` (credit note row).

---

### D14 — F4 and F7 are fixed in this task (2026-08-18)

**Context:** Two live corruption paths exist independently of the missing field. F4: a failed lookup
becomes rate 1. F7: `avgCostPrice` is seeded straight from the item's own currency on item creation
with initial stock, so the average is mixed-currency before any document exists.

**Options:** (a) both in this task; (b) both split into a separate bug; (c) F4 here, F7 separately.

**Decision:** (a).

**Why & trade-off:** Same defect family, same files, and the new field cannot be trusted while they
persist. F7 in particular means shipping the rate alone would still leave averages wrong. Trade-off:
a bigger task and a wider regression surface than the field change alone.

**Refs:** F4, F7.

---

### D15 — The inventory report paths are fixed in this task (2026-08-18)

**Context:** The sibling feature's D6 sequenced report changes as a separate task. Here the broken
report paths are the reason the field is worth storing at all (F6).

**Decision:** In scope. The two raw `$group` paths gain a multiplication by `conversionRate`; the JS paths
that currently make a live riften call per row switch to the stored rate.

**Why & trade-off:** Without it this task ships a field nothing reads, and the wrong numbers stay on
screen. Side benefit: the converting paths lose a network call per row (F11). Trade-off: departs from
the sibling feature's precedent, so the two tasks now differ in shape as well as content.

**Refs:** F6, F11; `features/inventory-net-price-on-transactions/docs/decisions.md` D6.

---

### D16 — Sequencing against the net-price task is open (2026-08-18)

**Context:** `features/inventory-net-price-on-transactions/` adds fields to the same row, edits the
same two builders (`onDocumentUpdate.js:483-505` and
`manage-linked-document-inventory-transaction.js:18-42`), and changes what the same averaging engine
is fed. Merging them was proposed.

**Decision:** Not merged. The net-price task is already with an engineer for estimate; priority
between the two is Jeet's call after that discussion. The collision is documented in both tasks so
whoever picks up either one sees it.

**Why & trade-off:** Merging would mean one schema change and one regression pass instead of two, but
it would also disturb an estimate that is already in progress. Trade-off accepted: two passes through
the same functions, and a rebase for whichever ships second.

**Refs:** F9; sibling feature `spec.md`, `docs/decisions.md`.

---

### D17 — The two movement-creation paths must agree on a missing document currency (2026-08-18)

**Context:** Surfaced during drafting, not during the team-talk. The converted/linked path falls back
to the item's own currency when the document carries none
(`manage-linked-document-inventory-transaction.js:27`); the primary path has no such fallback
(`onDocumentUpdate.js:483-505`). So the same document can produce differently-valued movements
depending on which path created it.

**Options:** (a) both fall back to the item's currency; (b) both fall back to the business currency;
(c) leave them different.

**Decision:** Open, owned by engineering. Working default: (a) — make both fall back to the item's
currency, matching the path that already does. (c) is ruled out: two paths disagreeing on the same
input is the defect, whichever value wins.

**Why & trade-off:** Recorded as a numbered decision rather than a loose note so the handoff matrix
has no unnumbered row, and so it cannot be lost between the two tasks that touch these paths.

**Refs:** F9; PRD EC8 and OQ4.

---

### D18 — What a report does across a business-currency change (2026-08-18)

**Context:** Raised by the adversarial review, after the team-talk had ended. EC1 keeps each movement's
original `bookCurrency` and does not restate history when a business changes its own currency. FL7
tells every report to state its totals in `bookCurrency`, as though there were only one. A report
period that spans the change contains movements valued into two different currencies. Summing them
recreates this feature's own defect one level up.

**Options:** (a) total only movements whose `bookCurrency` matches the business's current currency,
and say how many were excluded; (b) group the report by `bookCurrency` and show one total per
currency; (c) convert old movements into the new currency at some rate; (d) sum them anyway.

**Decision:** Open, owned by Jeet and the team. Working default: (a). (d) is ruled out without
discussion — it is the exact defect this feature exists to remove.

**Why & trade-off:** (a) never shows a wrong number, at the cost of showing an incomplete one. (b) is
more honest but changes every affected report's shape. (c) needs a rate for a conversion that never
happened, and would restate history, which D5 and EC1 both refuse.

**Refs:** PRD EC13 and OQ5; TC-G6; F2.

---

### D19 — Field renamed to `conversionRate`; supersedes the name half of D3 (2026-08-18)

**Context:** D3 named the new field `forexRate`, after Accounting's `forex_rate`. Jeet flagged that
any name ending in "rate" reads badly next to a document line's own `rate` field, which is its
**unit price** and has nothing to do with currency. The docs had already needed a written caution
about that collision, which is itself the signal that the name was wrong.

**Options:** (a) `conversionRate`; (b) `exchangeRate`; (c) keep `forexRate`.

**Decision:** (a) `conversionRate`. `bookCurrency` is unchanged.

**Why & trade-off:** The value is read straight off the document's `conversionRates` map, so the
singular name makes the lineage obvious: a document holds a map of rates keyed by business currency,
a transaction holds the one that applied to it. (b) is a fine word but has no matching term anywhere
else in the product. (c) borrowed a name from a different service, in a different language
(`saturn` is PostgreSQL and snake_case), and bought no clarity here.

Trade-off accepted: the name no longer visibly matches Accounting's `forex_rate`. The glossary entry
records that they mean the same thing and convert in the same direction, so the link is not lost.

**Supersedes:** the field-name half of D3. The rest of D3 (`bookCurrency`, and the requirement to add
both to `docs/glossary.md`) still stands.

**Refs:** D3; `docs/glossary.md`; ADR 0002.

---

### D20 — F7 corrected: the stored average was always right (2026-08-18)

**Context:** F7 originally claimed that creating an item with opening stock seeds `avgCostPrice`
unconverted, making the average mixed-currency before any document exists. That claim was used to
justify D14 (fixing it inside this task) and appeared in the PRD problem statement, the task's
Verified Current Behaviour, and TC-C6.

**What actually happens:** Jeet tested it — INR business, item priced in USD with opening stock —
and `avgCostPrice` came out converted, in INR. Re-read of the code confirms it. The `MANUAL`
transaction is created first, its hook writes the converted average to Mongo, and only afterwards does
`result.avgCostPrice = costPrice` run inside an `alterItems` after-hook that never re-saves. It
changes the create **response**, not the record.

**Decision:** F7 is corrected. The defect is a stale unconverted `avgCostPrice` in the item-create
response, not corrupted data. It stays in scope — it is small and sits in the same code — but it
no longer carries any weight in D14's reasoning.

**Why & trade-off:** D14 was argued partly on "shipping the rate alone would still leave averages
wrong, because F7 corrupts them before any document exists." That sentence was false. **D14 still
stands, on F4 alone** — the `|| 1` fallback is a genuine corruption path and was verified
separately.

**Supersedes:** the F7 half of D14's reasoning. D14's decision is unchanged.

**Refs:** F7 (rewritten), F4, D14; `inventories.hooks.js:191-195`.

---

### D21 — Labelling the item's own averages is not in this task (2026-08-18)

**Context:** Jeet asked which currency the item's average is held in, given three currencies are in
play: business, item and transaction. The answer is always the business currency — but nothing on
the item record says so. `inventories.currency` labels `costPrice`/`sellingPrice`, while
`avgCostPrice`/`avgSellingPrice` carry no label at all. An item priced in USD in an INR business ends
up holding a USD price and an INR average side by side (F12, EC14).

**Options:** (a) leave it, and rely on the transaction's new `bookCurrency` to make each contribution
checkable; (b) add a currency label to the item's averages; (c) restate item prices into the business
currency.

**Decision:** (a) for this task. Raised as **OQ6**, owned by Jeet.

**Why & trade-off:** This gap is not caused by the missing conversion rate and storing one does not
fix it. It is a separate question about how an item presents its own prices. (c) would change what a
user sees on the item they priced, which is well outside a stock-valuation correction. Trade-off
accepted: after this ships the averages are trustworthy and auditable per transaction, but the item
record still shows two currencies with no label.

**Refs:** F12; PRD EC14 and OQ6.

---

### D22 — Filling happens on the write path only; no background sweep (2026-08-18)

**Context:** D7 put filling in two places: on any patch or reversal of an existing transaction, and
in a rate-limited background sweep. Jeet has since scoped history down.

**Options:** (a) keep both; (b) write-path touch only; (c) no filling at all.

**Decision:** (b). A transaction that is patched or reversed for any reason fills its
`conversionRate` and `bookCurrency` on the way through. Nothing else touches history. No sweep, no
migration, no fill-on-read.

**Why & trade-off:** The write-path fill is free — the hook is already running and already has the
document. A sweep is a separate job with its own rate-limit, failure and monitoring surface, for
history that D23 now handles safely on read anyway. Trade-off accepted: a transaction that is never
touched again is never filled, so it relies on the D23 fallback for ever. That is acceptable because
the fallback is defined and matches today's behaviour exactly.

**Supersedes:** the background-sweep half of D7. The write-path half of D7, and its rule that filling
never happens during a report read, both still stand.

**Refs:** D7; PRD FL8.

---

### D23 — A report never drops a row; it falls back instead (2026-08-18)

**Context:** D18/OQ5 asked what a report does when its period spans a change of business currency,
and the working default was to exclude non-matching rows. Jeet rejected that: an excluded row makes
the report **incomplete**, which is worse than a slightly wrong one. He proposed falling back to the
transaction's own price, treating the conversion rate as `1`, and noted the same fallback covers a
transaction that simply has no `conversionRate` yet.

**Decision:** No report ever excludes a transaction. A row's stored rate is **usable** when it has a
`conversionRate` **and** its `bookCurrency` equals the business's current currency. When usable, the
report multiplies by it. When not usable, the report falls back to **what that report does today**.

That last clause is a refinement on the raw "treat as 1" rule, and it exists to prevent a regression:

| Report path | Today | Fallback for an unusable row |
|---|---|---|
| The party transaction aggregation | No conversion at all — already effectively rate `1` | Rate `1`. No change from today. |
| The paths that loop per row | A live rate lookup per row, which converts history correctly today | Keep the live lookup. Dropping these to `1` would make working reports worse. |

> **Corrected 2026-08-18 (citation only; the decision is unchanged).** This entry originally said
> "the two database aggregations". There is one over `inventorytransactions` — Party transaction.
> The second report cited at the time, Batch expiry, aggregates `batches` and never reads a
> transaction. See F6 and F15.

**Why & trade-off:** Completeness beats precision here — a missing row reads as data loss to a user
who knows the sale happened, while a slightly wrong row reads as today's number. The refinement costs
nothing and protects the reports that are already right. Trade-off accepted: a row that falls back to
`1` in an aggregation report is still wrong, silently. That is unchanged from today, and OQ2 still
asks whether to say so on screen.

**Resolves:** D18 / OQ5.

**Refs:** F6; D6; D22.

---

### D24 — Reading the rate from the document is the parked option for history (2026-08-18)

**Context:** Jeet asked whether any better alternative exists for existing data before parking it.

**Decision:** Nothing is done to existing data now, beyond D22's write-path fill. One alternative is
recorded as the first thing to evaluate if history accuracy later becomes a complaint: **resolve the
rate from the source document at report time** rather than storing it, via a `$lookup` from
`inventorytransactions.docId` into `invoices` and reading `conversionRates[businessCurrency]`.

**Why & trade-off:** It needs **no data change at all** — no migration, no sweep, no writes — and
it makes every document-backed historical row convert correctly on the spot. It also survives a
business-currency change for free, because the document keeps one rate key per business currency.
Costs: a join on a high-volume collection inside report aggregations, and it does nothing for
document-less rows (`MANUAL`, `BULKMANUAL`, `TRANSFERSTOCK`, `RECONCILE`). `docId` is already
indexed. Rejected for now on complexity, not on merit — prefer it over a migration if this is
revisited.

**Refs:** F2, F6; D5, D22.

---

### D25 — Warehouse transfers are explicitly out of scope (2026-08-18)

**Context:** Jeet asked whether a transfer stores `costPrice`/`sellingPrice` on its transactions, and
if not, whether this task needs to handle it. Checked in code (F13): it does not. Both transfer
transactions are built with a cost and selling price of zero, no `currency`, and a
`params.transferStock` flag that excludes them from every average at item, warehouse and batch level.

**Options:** (a) leave transfers alone and say so; (b) stamp a conversion rate on them anyway for
consistency; (c) give transfers a real price so their value carries between warehouses.

**Decision:** (a). Transfers are named in the task's **Out** list, with the reason, so the exclusion
is deliberate rather than an oversight.

**Why & trade-off:** (b) would store a rate against a zero price — no meaning, and a maintenance
trap. (c) is a genuine improvement to per-warehouse valuation, and genuinely a different feature: it
would give transfers a cost basis and start moving warehouse averages that are stable today. Neither
belongs in a task about recording the rate that was actually used.

**Stated out loud in the task so nobody "fixes" it later:** do not add a rate or a price to a
transfer as part of this work.

**Refs:** F13.

---

### D26 — The stock-integrity cron is in scope, as a must-fix (2026-08-18)

**Context:** Jeet asked which existing reports are affected. Enumerating them (F14) turned up
something that is not a report: `inventorystockintegrity.js` recomputes `avgCostPrice` and
`avgSellingPrice` at item, warehouse, batch and batch-warehouse level with its **own** copy of the
averaging maths, its **own** live rate lookup, and its **own** `exchangeRate || 1` fallback — then
patches the result back onto the item.

**Options:** (a) fix it in this task; (b) leave it and raise a separate bug; (c) disable it until it
is fixed.

**Decision:** (a).

**Why & trade-off:** This is not an enhancement to the cron, it is a precondition for the feature
holding at all. Fix the live path alone and the cron overwrites the corrected averages on its next
run — the feature silently undoes itself. (b) leaves a window where that happens in production.
(c) removes the drift protection the cron exists to provide. Trade-off accepted: the task now spans
two implementations of the same maths, which is a wider regression surface. That duplication is
pre-existing and worth flagging separately — two copies of an averaging rule is how they drift.

**Refs:** F14, F4.

---

### D27 — The rate is stored on every transaction, whatever its stock effect (2026-08-18)

**Context:** Jeet noticed the task's Scope named only the billTypes a business can set to `UPDATE` or
`BLOCK`, and asked whether `IGNORE` transactions should carry the rate too.

**Options:** (a) store on every transaction regardless of `transactionType`; (b) store only on rows
that move or reserve stock (`UPDATE`, `BLOCK`).

**Decision:** (a).

**Why & trade-off:** Three reasons, in rising order of force (F16).

1. `costPrice`, `sellingPrice` and `currency` are **already** written on every row regardless of
   stock effect. Storing the rate on a subset recreates this feature's own defect for that subset.
2. The **All transaction report does not filter by `transactionType`** — it lists `IGNORE` rows
   with their price and currency. Without a rate they cannot be converted.
3. **`transactionType` is not fixed for the life of a row.** A `BLOCK` becomes `BLOCK_IGNORE` on
   conversion; a soft-removed row is patched to `IGNORE`; a change to the document's stock-effect
   flag re-runs the effect in either direction. A conditionally-stored rate would vanish exactly when
   a reversal needs it, breaking D8.

**Not a change of intent, a correction of wording.** The test suite already asserted this — TC-C5
reads "All four carry a `conversionRate`". Only the Scope prose was wrong, because it described which
billTypes are *configurable* for stock rather than which documents create a transaction.

**Refs:** F16; D8; `manage-inventory-stock.js:702`.
