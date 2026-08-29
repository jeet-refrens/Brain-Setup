# Inventory: currency conversion rate on stock movements — Handoff & Decision Log

**Audience:** the engineer or agent who picks this up without having been in the room.

**Links:** [PRD](PRD-inventory-transaction-currency-conversion.md) ·
[TESTS](TESTS-inventory-transaction-currency-conversion.md) ·
[TASK](TASK-inventory-transaction-currency-conversion.md) ·
[code-findings](code-findings.md) · [decisions](decisions.md) ·
[ADR 0001](adr/0001-inventory-values-a-movement-at-the-documents-rate.md) ·
[ADR 0002](adr/0002-store-the-rate-not-the-converted-price.md)

## TL;DR

Read in this order. **(1)** [code-findings.md](code-findings.md) — short, every claim carries a
`file:line`, and it holds the three things most likely to surprise you. **(2)** The decision journey
below. **(3)** `serana/src/hooks/update-invoice-with-biz-currency.js`, the reference implementation of
every rule we are adopting. Read it before designing anything.

**The premise was half wrong, and the correction matters.** The idea was raised as "the average is
computed correctly, we just don't store the rate." The averaging engine does apply a rate. But it
fetches its own market rate instead of the document's (F3), turns a failed lookup into `1` (F4), and
and reports a stale unconverted average in the item-create response (F7). **F7 was wrong in its
first version** — it claimed the stored average was seeded unconverted. Jeet disproved that in
product. The stored average is correct; only the response is not. Read F7 before repeating the old
claim.

**Storing beats recomputing for one concrete reason.** The party transaction report adds currencies
together inside a database aggregation (F6). It cannot convert, because you cannot multiply by a rate
that is not a field on the row. *(An earlier version of F6 claimed two such reports. The second was
Batch expiry, which aggregates `batches`, not transactions. Corrected — see F15.)*

**We diverged from the accounting pattern on purpose.** Accounting stores both sides of a conversion.
We store only the rate. Read [ADR 0002](adr/0002-store-the-rate-not-the-converted-price.md) before
"fixing" that. It will look like an oversight. It is not.

## Decision matrix

| D# | Decision | Status | Ref |
|---|---|---|---|
| D1 | A movement uses its source document's rate; a lookup is the fallback | decided | [ADR 0001](adr/0001-inventory-values-a-movement-at-the-documents-rate.md) |
| D2 | Store the rate, not converted prices | decided | [ADR 0002](adr/0002-store-the-rate-not-the-converted-price.md) |
| D3 | Field names; both added to the glossary | **superseded by D19** (name) | decisions.md |
| D19 | Field is `conversionRate`, not `forexRate` — never just "rate" | decided | decisions.md |
| D20 | F7 corrected: stored average was always right | decided | decisions.md |
| D21 | Labelling the item's own averages | **OPEN @Jeet** | PRD OQ6 |
| D4 | Failed-rate handling | **OPEN @engineering** — working default stated | PRD OQ1 |
| D5 | Forward-only, with lazy filling of history | decided | decisions.md |
| D6 | An unfilled movement counts as rate 1 | **OPEN @Jeet + team** — default in force | PRD OQ2 |
| D7 | Filling runs on the write path, never on reads | **sweep half superseded by D22** | decisions.md |
| D8 | A reversal reuses the rate stored on the movement it reverses | decided | decisions.md |
| D9 | Editing a document's rate re-triggers the stock path | decided | decisions.md |
| D10 | Document-less movements take a lookup at `transactionDate` | decided | decisions.md |
| D11 | A reservation release unwinds at the original movement's rate | decided | decisions.md |
| D12 | Warehouse and batch averages get the same treatment | decided | decisions.md |
| D13 | A credit note uses its own rate; the return gap is accepted | decided | decisions.md |
| D14 | F4 and F7 are fixed in this task | decided | decisions.md |
| D15 | The inventory report paths are fixed in this task | decided | decisions.md |
| D16 | Sequencing against the net-price task | **OPEN @Jeet** | PRD OQ3 |
| D17 | Builder disagreement when a document has no currency | **OPEN @engineering** | PRD OQ4 |
| D18 | What a report does across a business-currency change | **resolved by D23** | decisions.md |
| D22 | Filling on the write path only; no background sweep | decided — supersedes the sweep half of D7 | decisions.md |
| D23 | A report never drops a row; it falls back instead | decided | decisions.md |
| D24 | Read the rate from the document — parked option for history | parked | decisions.md |
| D25 | Warehouse transfers are out of scope | decided | decisions.md |
| D26 | The stock-integrity cron is in scope, as a must-fix | decided | decisions.md |
| D27 | The rate goes on every transaction, `IGNORE` included | decided | decisions.md |

## Decision journey — read this first

**T1 — The premise was corrected before anything was designed.** The idea assumed the averages were
right. The live code says otherwise on F3 and F4. Everything downstream was designed against the
corrected picture. If you catch yourself thinking "this is just adding a field", re-read this turn.
**One correction to this turn:** F7 originally claimed a third fault — an unconverted opening
average — and that was wrong. See F7 and D20.

**T2 — Which rate is authoritative (D1).** Options: the document's stored rate, or a live market
lookup at the movement's date. Chose the document's rate, with a lookup as fallback. The deciding
argument: the submitted rate on a document is *deliberately trusted*, and the document hook only ever
fills a **missing** rate (F2). An independent lookup throws away a choice the user made on purpose.
*Rejected: keeping the live lookup and merely persisting it — that writes the disagreement down
rather than fixing it.*

**T3 — What to store (D2).** Accounting stores the original amount, the converted amount and the
rate. Chose the rate and the business currency only. Reasons in
[ADR 0002](adr/0002-store-the-rate-not-the-converted-price.md). The one most easily forgotten: the
net-price task is about to add two more price fields to this record, so converted twins do not scale.
*Rejected: mirroring accounting in full; storing converted prices alone.*

**T4 — Failed lookups (D4).** Put to Jeet, who returned it to engineering. Settled: today's silent
`1` is a defect. Open: what replaces it. A working default is stated so the requirement stays
testable.

**T5 — Backfill (D5). Pushed hard; the answer was better than either option offered.** The case for a
one-shot backfill: the affected set is small, precisely identifiable, and its repair input already
exists on each movement's document. Jeet rejected it on volume, and proposed a third path —
forward-only **plus lazy filling**. Same end state, no migration window. *Rejected: one-shot backfill
with average recomputation; rate-only backfill; pure forward-only with no filling.*

**T6 — What an unfilled movement is worth (D6).** Chose rate `1`, as today, because it is the only
option with no day-one regression. Jeet kept the question open for the team. The cost is written into
the PRD, not buried: the number stays wrong until filled, with nothing on screen saying so.
*Rejected: excluding unfilled movements — it understates totals and reads as data loss.*

**T7 — Where filling happens (D7).** The write path plus a rate-limited sweep. Two facts ruled out
filling on report reads: the raw aggregation paths cannot resolve or write a rate mid-pipeline (F6),
and filling on read turns one large report into thousands of writes.

**T8 — Reversal correctness (D8).** A reversal reuses the stored rate and never re-resolves. Today's
code re-resolves (F5). It usually agrees, since the lookup is keyed on the same date. "Usually" is not
enough for an append-only log where the average is correct only if every entry unwinds exactly. The
failure that settles it: a lookup that succeeds going in and fails coming out leaves a permanent
error nothing detects.

**T9 — Editing a document's rate (D9).** Chose to re-trigger the stock path. `conversionRates` is in
neither watched-field list today (F10), so a correction restates the invoice and the ledger and
inventory never hears about it. Without this, D1 holds only until someone corrects a rate. *Rejected:
treating the rate stamped at creation as final history.*

**T10 — Smaller rules, decided by the author and accepted (D10, D11, D12, D13).** Document-less
movements take a lookup at their date. A reservation release unwinds at the original movement's rate,
so the difference lands on the invoice. Warehouse and batch averages get identical treatment, since
otherwise batch valuation disagrees with item valuation for the same stock. A credit note uses its own
rate — with the consequence stated rather than hidden: a full return at a different rate will not
restore the average exactly.

**T19 — Package items were traced, and turned up a silent trap (F17).** Jeet flagged that a package
on a document creates a transaction for the parent *and* one per child, and asked for the rule to
cover them. Tracing it showed the children are created by an after-hook that copies an **explicit
allow-list of fields** from the parent transaction. The currency is on that list, so the same rate
applies throughout and there is nothing extra to resolve. But `conversionRate` and `bookCurrency`
must be **added to that list** — miss it and every package child ships without a rate, silently,
and only for businesses that use packages. Called out in the task's flow list rather than left to
implementation.

**T18 — `IGNORE` rows were confirmed in scope (D27, F16).** Jeet noticed the Scope named only the
billTypes configurable to `UPDATE` or `BLOCK` and asked whether `IGNORE` transactions should carry a
rate. They should. Price and currency are already stored on every row regardless of stock effect; the
All transaction report lists `IGNORE` rows and could not otherwise convert them; and a row's
`transactionType` changes over its life, so a conditional rate would be missing exactly when a
reversal needs it. The tests already had this right — TC-C5 asserts all four types carry a rate.
Only the Scope prose was wrong.

**T17 — The reports were mapped, got it wrong, and were corrected (F15).** Jeet listed the six
reports he can see in the product. The first mapping inferred each report's data source from the
field names in its pipeline, and was wrong about two of them. Jeet asked whether Batch expiry and
Stock value use the *item's* price — they do. Batch expiry aggregates `batches`; Stock value reads
`inventories` and already converts from the item's currency. Neither reads a transaction.

**Corrected blast radius: three reports, and only one visibly changes.** Party transaction is the
only currency-mixing aggregation over transactions. Product wise P&L already converts and shifts only
where a rate was overridden. All transaction is a listing that changes no number. Stock value, Batch
expiry and Stock status are untouched.

This also corrected F6, which had claimed **two** non-converting aggregations. There is one. The
argument for storing rather than recomputing survives on that one, but the count was wrong in four
documents. **Lesson for anyone extending this work: check which collection a pipeline queries, not
which field names appear in it.**

**T16 — Enumerating the affected reports turned up the biggest risk in the feature (D26, F14).** Jeet
asked which existing reports change. Five consumers read prices off transactions and all need work.
The sixth is not a report at all: the stock-integrity cron recomputes the same averages with its own
copy of the conversion logic, its own live lookup, its own `\|\| 1` fallback, and writes them back.
Fixing the live path alone would mean the cron overwrites the correction on its next run and the
feature silently undoes itself. Brought into scope as a must-fix. The underlying smell — two
implementations of one averaging rule — is pre-existing and worth its own cleanup later.

**T15 — Warehouse transfers were checked and ruled out (D25).** Jeet asked whether transfers store a
price. They do not: both transfer transactions are built with zero cost and selling price, no
currency, and a flag that excludes them from every average (F13). So there is nothing to convert.
Recorded as an explicit **Out** with the reason, because the natural instinct on reading the task is
to "finish the job" by stamping a rate on them. A real gap did surface and was left alone: a transfer
carries no cost basis, so a destination warehouse's average does not reflect stock arriving. That
predates this work.

**T14 — History was scoped down, and reports were made complete instead (D22, D23, D24).** Jeet cut
the background sweep: filling now happens only when a transaction is patched or reversed for some
other reason. He also rejected the plan to exclude non-matching rows from reports — an incomplete
report is worse than an imprecise one. So no report drops a row; an unusable rate falls back to what
that report does today. The refinement that matters: falling back to a flat `1` **everywhere** would
have been a regression, because the per-row report paths convert history correctly today. Asked for a
better option for existing data, the answer was D24 — resolve the rate from the source document at
report time, which needs no data change at all. Parked, not rejected.

**T11 — Scope of the existing faults (D14, corrected by D20).** F4 is fixed here — a real
corruption path. F7 is also fixed here, but it turned out to be a stale **response** value, not
corrupted data, so it no longer carries the weight it did when D14 was taken. D14 still stands on F4
alone.

**T12 — Scope of the reports (D15).** Fixed here, departing from the net-price task's precedent of
deferring report work. Otherwise this ships a field nothing reads and the reported symptom stays on
screen.

**T13 — Sequencing (D16).** Merging with the net-price task was proposed: one schema change, one
regression pass, no second rebase. Jeet declined to decide now — that task is already with an engineer
for estimate. **The collision is real and unresolved.** Whoever picks up either task reads the other's
spec first.

> D3, D17 and D18 have no journey turn. D3 followed from D2 with no debate. D17 and D18 were both
> found after the team-talk had ended — D17 during drafting, D18 during the adversarial review.

## Code map and what already works

Read from live source on 2026-08-17. Re-check line numbers before relying on them.

| Repo / file | State | What you need from it |
|---|---|---|
| `talos/src/inventorytransactions.js` | to change | The record to extend. Already has `currency` (`:20-23`), `params` (`:82`), `lineItem` (`:81`). `strict: 'throw'` (`:135`) — a new field must be declared. |
| `talos/src/helpers/documentCommonFields.js:787-808` | do not change | Where a document's `currency` and `conversionRates` live. Input, not a target. |
| `serana/src/hooks/update-invoice-with-biz-currency.js` | do not change | **Read before designing anything.** The reference implementation of every rule we adopt: trust the submitted rate, fill only what is missing, never persist a failed lookup, force same-currency to 1, strip a cloned foreign rate. |
| `serana/src/hooks/update-conversion-rates.js:17-46` | works | Re-resolves the rate when a document's currency changes, then refreshes totals. |
| `serana/src/helpers/onDocumentUpdate.js:483-505` | to change | **The primary movement builder.** Stamp the rate here. |
| `serana/src/helpers/onDocumentUpdate.js:10-30` | to change | The watched-field lists. Add `conversionRates` for D9. |
| `serana/src/hooks/manage-linked-document-inventory-transaction.js:18-42` | to change | The converted/linked builder. Falls back to the item's currency (`:27`) where the primary builder does not — that is D17. |
| `serana/src/hooks/manage-inventory-stock.js:586-594` | to change | Where the rate is fetched live, and where `priceFactor = exchangeRate \|\| 1` lives. F3 and F4 both sit here. |
| `serana/src/hooks/manage-inventory-stock.js:30-64` | to change | `calculateAveragePrice`. D8 changes where the reverse factor comes from. |
| `serana/src/hooks/manage-inventory-stock.js:702` | **do not change** | The gate that decides `UPDATE` and `BLOCK` feed the averages. Only the rate applied changes. |
| `serana/src/hooks/create-manual-inventory-transaction.js:95, 187, 226` | to change | Sets `result.avgCostPrice` on the **response** after the real converted write has already happened. This is F7 — a stale response, not bad data. |
| `serana/src/services/inventories/inventories.hooks.js:191-195` | reference | Proves the line above runs in an `alterItems` after-hook that never re-saves. This is what makes F7 cosmetic. |
| `serana/src/helpers/getCurrencyExchange.js` | change carefully | Returns 0 on failure, rounds to six decimals. Many callers, not all inventory. Check the blast radius. |
| `serana/src/services/inventory-reports/class.js:846-856` | to change | The **Party transaction** aggregation — the one place that sums transaction prices with no conversion. This is F6. `:530-537` is **not** a sibling: it belongs to Batch expiry, which aggregates `batches`. |
| `serana/src/services/inventory-reports/class.js:110-163`, `:962-968` | to change | The paths that convert with a remote call per row. Switch to the stored rate. |
| `serana/src/commands/crons/integrity/inventorystockintegrity.js` | **must change** | A second, independent implementation of the averaging maths (F14). Own rate lookup (`:60`), own `\|\| 1` bug (`:66`), and it patches averages back (`:381`, `:426`). Fix the live path without this and the cron reverts it. |
| `serana/src/services/conversion-rate/conversion-rate.service.js:14` | works | Proxies rate lookups to `riften`. Every lookup is a network call. |
| `serana/src/commands/fixinventorycurrencyrates.js` | reference only | An existing repair command for a different currency defect. Useful as a shape for a sweep. |

**Verified preconditions** — checked in code, not assumed.

- The movement record already stores `currency`. This adds to a partial implementation (F1).
- A document's rate map is keyed by business currency code, and multiplies document amounts *up* into
  business currency (F2). The existing `priceFactor` multiplies in the same direction.
- Both movement builders are located, including the primary one — an open question in the net-price
  task (F9).
- Item records already carry per-currency price maps, while the averages carry no currency label at
  all (F8).

## Pitfalls — do not undo

- **Do not "simplify" by looking the rate up instead of reading the document.** That is the original
  bug. [ADR 0001](adr/0001-inventory-values-a-movement-at-the-documents-rate.md).
- **Do not add converted price fields for convenience.**
  [ADR 0002](adr/0002-store-the-rate-not-the-converted-price.md). The next price field would need one
  too, and it will drift.
- **Do not let a reversal resolve its own rate.** It reads the rate off the movement it reverses (D8).
- **Do not restore `|| 1` on a failed lookup.** It looks harmless. It values a dollar as a rupee (F4).
- **Do not change which movements feed the averages.** The `UPDATE`/`BLOCK` gate stays exactly as it
  is.
- **Do not fill rates during a report read** (D7).
- **Do not read a `0` rate as "same currency".** `0` means "we do not know" everywhere else.
- **Do not trust `serana/docs/inventory.md` on delivery-challan behaviour.** It disagrees with the
  live resolver, and the code wins.
- **Do not skip the single-currency regression pass.** The averaging engine is shared by every
  business in the product, most of which have none of this problem.

## Open questions

Live copy. The PRD mirrors these.

| # | Question | Owner | Working default |
|---|---|---|---|
| OQ1 (D4) | What happens when no rate can be resolved? | Engineering | No rate stored, Sentry alert raised, stock quantity still moves, kept out of the average. Filling later does not add it retroactively. Substituting `1` is ruled out. |
| OQ2 (D6) | Should reports flag movements that are not yet converted? | Jeet + team | No — count at rate `1`, matching today exactly. |
| OQ3 (D16) | Does this ship before or after the net-price task? | Jeet | Undecided. Both edit the same builders and the same averaging engine. |
| OQ4 (D17) | When a document has no currency, do both builders fall back to the item's currency? | Engineering | Yes — make them agree. |

## Changelog

- **2026-08-17** — Code research against live `talos` and `serana`. Findings F1–F11 recorded. Located
  the primary movement builder, closing an open question in the net-price task.
- **2026-08-18** — Team-talk. D1–D16 recorded, ADR 0001 and ADR 0002 raised. Problem confirmed by
  Jeet. PRD, TESTS, TASK and this handoff drafted. D17 added during drafting. Editorial, plain-English
  and adversarial review passes run; D18 and EC13 came out of the last one.
